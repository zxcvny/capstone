import logging
import json
import websockets
import asyncio
from app.services.kis_auth import kis_auth
from app.services.kis_data import kis_data
# 👇 [핵심] 종목 정보 서비스 가져오기 (이게 있어야 이름을 알 수 있어요!)
from app.services.stock_info import stock_info_service 
from app.core.config import settings

logger = logging.getLogger(__name__)

class KISWebSocketManager:
    clients = set()
    _stream_task = None

    async def connect_client(self, websocket):
        """클라이언트 연결 처리"""
        await websocket.accept()
        self.clients.add(websocket)
        logger.info(f"✅ 클라이언트 연결됨. 현재 수: {len(self.clients)}")
        
        # 🚀 접속하자마자 '최근 시세(스냅샷)' 전송
        asyncio.create_task(self.send_snapshot(websocket))

        # 스트림 시작
        if not self._stream_task or self._stream_task.done():
            logger.info("🚀 첫 클라이언트 입장. KIS Real-time 스트림을 시작합니다.")
            self._stream_task = asyncio.create_task(self.start_top_volume_stream())

    def disconnect_client(self, websocket):
        """클라이언트 연결 해제 처리"""
        self.clients.discard(websocket)
        logger.info(f"👋 클라이언트 퇴장. 남은 수: {len(self.clients)}")
        
        if not self.clients and self._stream_task:
            logger.info("💤 모든 클라이언트 퇴장. KIS 스트림을 중지합니다.")
            self._stream_task.cancel()
            self._stream_task = None

    async def send_snapshot(self, websocket):
        """
        [REST API] 신규 접속자에게 현재가(장중) 또는 종가(장마감/주말) 1회 전송
        """
        try:
            symbols = await kis_data.get_top_volume()
            logger.info(f"SNAPSHOT 시작: {len(symbols)}개 종목 요청")

            for code in symbols:
                if websocket.client_state.name != "CONNECTED": 
                    break

                result = await kis_data.get_current_price(code)
                
                if isinstance(result, dict) and "price" in result:
                    # 👇 [핵심] 코드를 한글 이름으로 변환
                    name = stock_info_service.get_name(result['code'])
                    
                    msg = {
                        "type": "ticker",
                        "code": result['code'],
                        "name": name,  # ✨ 이름 필드 추가됨!
                        "timestamp": "SNAPSHOT",
                        "price": result['price'],
                        "change_rate": result['change_rate'],
                        "volume": result['volume'],
                        "power": ""
                    }
                    await websocket.send_text(json.dumps(msg))
                
                # API 호출 사이 딜레이 (초당 제한 준수)
                await asyncio.sleep(0.1)
            
            logger.info("✅ 초기 스냅샷 데이터 전송 완료")

        except Exception as e:
            logger.error(f"⚠️ 초기 스냅샷 전송 중 오류: {e}")

    async def broadcast(self, data: dict):
        """연결된 모든 클라이언트에게 JSON 데이터 전송"""
        if not self.clients:
            return
        json_data = json.dumps(data)
        tasks = [client.send_text(json_data) for client in self.clients]
        await asyncio.gather(*tasks, return_exceptions=True)

    def _parse_kis_data(self, msg: str):
        """
        한투 웹소켓 데이터 파싱 (이름 추가)
        """
        try:
            first_char = msg[0]
            if first_char == '{':
                return json.loads(msg)
            
            parts = msg.split('|')
            if len(parts) < 4:
                return None

            tr_id = parts[1]
            symbol = parts[2]
            raw_data = parts[3]

            if tr_id == "H0STCNT0":
                val = raw_data.split('^')
                # 👇 [핵심] 여기서도 이름 변환
                name = stock_info_service.get_name(symbol)
                
                parsed_data = {
                    "type": "ticker",
                    "code": symbol,
                    "name": name, # ✨ 이름 필드 추가됨!
                    "timestamp": val[0],
                    "price": val[2],
                    "change_rate": val[4],
                    "volume": val[12],
                    "power": val[20]
                }
                return parsed_data
            
            return {"type": "unknown", "raw": msg}

        except Exception as e:
            logger.error(f"⚠️ 데이터 파싱 에러: {e}")
            return None

    async def start_top_volume_stream(self):
        """KIS 웹소켓 연결 및 데이터 수신 루프"""
        try:
            symbols = await kis_data.get_top_volume()
            approval_key = await kis_auth.get_approval_key()
            ws_url = f"{settings.KIS_WS_URL}"
            
            logger.info(f"🔌 KIS WebSocket 연결 시도: {ws_url}")

            async with websockets.connect(ws_url, ping_interval=60) as ws:
                logger.info("✅ KIS WebSocket 연결 성공.")

                for idx, symbol in enumerate(symbols):
                    subscribe_msg = {
                        "header": {
                            "approval_key": approval_key,
                            "custtype": "P",
                            "tr_type": "1",
                            "content-type": "utf-8"
                        },
                        "body": {
                            "input": {
                                "tr_id": "H0STCNT0", 
                                "tr_key": symbol
                            }
                        }
                    }
                    await ws.send(json.dumps(subscribe_msg))
                    
                    # 구독 요청 딜레이 (서버 부하 방지)
                    if idx % 5 == 0:
                        await asyncio.sleep(0.1) 
                    else:
                        await asyncio.sleep(0.02)
                
                logger.info(f"✅ 총 {len(symbols)}개 종목 구독 요청 완료.")

                while True:
                    msg = await ws.recv()
                    parsed_data = self._parse_kis_data(msg)
                    
                    if parsed_data and self.clients:
                        if "header" in parsed_data: 
                            continue 
                        await self.broadcast(parsed_data)

        except asyncio.CancelledError:
            logger.info("🛑 스트림 태스크 취소됨 (클라이언트 0명).")
        except Exception as e:
            logger.error(f"⛔ KIS WebSocket 스트림 오류: {e}", exc_info=True)
            await self.broadcast({"type": "error", "message": "KIS Stream Error"})
        finally:
            self._stream_task = None
            logger.info("✅ KIS 스트림 태스크 종료.")

kis_ws_manager = KISWebSocketManager()