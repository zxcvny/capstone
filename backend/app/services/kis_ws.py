import logging
import json
import asyncio
import websockets
from collections import defaultdict
from app.services.kis_auth import kis_auth
from app.services.kis_data import kis_data
from app.services.stock_info import stock_info_service 
from app.core.config import settings

logger = logging.getLogger(__name__)

class KISWebSocketManager:
    def __init__(self):
        # { "005930": {ws1, ws2}, "000660": {ws3} } 형태로 관리
        self.subscriptions = defaultdict(set) 
        self.kis_websocket = None 
        self.approval_key = None
        self._stream_task = None

    async def get_approval_key(self):
        """웹소켓 키 발급/조회"""
        if not self.approval_key:
            self.approval_key = await kis_auth.get_approval_key()
        return self.approval_key

    async def connect_client(self, websocket, code: str):
        """프론트엔드 클라이언트 연결"""
        await websocket.accept()
        
        self.subscriptions[code].add(websocket)
        logger.info(f"✅ [{code}] 클라이언트 입장. 현재 구독자: {len(self.subscriptions[code])}명")

        # 1. 접속 즉시 스냅샷(REST API) 전송
        asyncio.create_task(self.send_snapshot(websocket, code))

        # 2. KIS 웹소켓 연결 확인 및 시작
        # [수정] .closed 체크 제거 (None 여부만 확인)
        if self.kis_websocket is None:
            if not self._stream_task or self._stream_task.done():
                self._stream_task = asyncio.create_task(self.start_kis_stream())
        
        # 3. 구독 요청 (이미 연결된 상태라면 즉시, 아니면 연결 후 루프에서 처리됨)
        if self.kis_websocket:
            await self.send_kis_subscription(code, "1")

    async def disconnect_client(self, websocket, code: str):
        """클라이언트 연결 해제"""
        if code in self.subscriptions:
            self.subscriptions[code].discard(websocket)
            logger.info(f"👋 [{code}] 클라이언트 퇴장. 남은 구독자: {len(self.subscriptions[code])}명")
            
            if not self.subscriptions[code]:
                del self.subscriptions[code]
                # 선택사항: 구독 해제 요청을 보내도 되지만, KIS는 연결 유지시 그냥 둬도 무방함

    async def send_kis_subscription(self, code, tr_type="1"):
        """KIS 서버에 종목 구독 요청"""
        # [수정] .closed 체크 제거 -> try-except로 처리
        if self.kis_websocket is None:
            return

        try:
            key = await self.get_approval_key()
            req = {
                "header": {
                    "approval_key": key,
                    "custtype": "P",
                    "tr_type": tr_type,
                    "content-type": "utf-8"
                },
                "body": {
                    "input": {
                        "tr_id": "H0STCNT0", 
                        "tr_key": code
                    }
                }
            }
            await self.kis_websocket.send(json.dumps(req))
            action = "구독" if tr_type == "1" else "해제"
            logger.info(f"📡 KIS에 [{code}] {action} 요청 전송")
            
        except Exception as e:
            logger.warning(f"⚠️ 구독 요청 실패 (연결 불안정): {e}")
            # 여기서 self.kis_websocket = None 처리는 start_kis_stream의 루프에서 담당

    async def send_snapshot(self, websocket, code):
        """초기 진입 시 REST API로 현재가 1회 전송"""
        try:
            result = await kis_data.get_current_price(code)
            if result:
                name = stock_info_service.get_name(code)
                msg = {
                    "type": "trade",
                    "code": code,
                    "name": name,
                    "time": datetime.now().strftime("%H%M%S"),
                    "price": result['price'],
                    "change": result['diff'],
                    "rate": result['change_rate'],
                    "volume": result['volume'],
                    "acml_vol": result['volume'],
                    "power": "0.00"
                }
                await websocket.send_text(json.dumps(msg))
        except Exception as e:
            logger.error(f"Snapshot Error: {e}")

    async def start_kis_stream(self):
        """KIS 웹소켓 연결 유지 및 데이터 분배 (Main Loop)"""
        ws_url = settings.KIS_WS_URL
        
        while True:
            try:
                async with websockets.connect(f"{ws_url}/tryitout/H0STCNT0", ping_interval=60) as ws:
                    self.kis_websocket = ws # 연결 객체 저장
                    logger.info("🚀 KIS WebSocket 연결 성공")

                    # [중요] 재접속 시, 현재 보고 있는 종목들 다시 구독 요청
                    # 딕셔너리 키(종목코드)들을 순회하며 구독
                    for code in list(self.subscriptions.keys()):
                        await self.send_kis_subscription(code, "1")
                        await asyncio.sleep(0.1) # 딜레이

                    while True:
                        msg = await ws.recv()
                        
                        if msg[0] in ['0', '1']:
                            parts = msg.split('|')
                            if len(parts) > 3:
                                tr_id = parts[1]
                                raw_data = parts[3]
                                fields = raw_data.split('^')
                                
                                if tr_id == "H0STCNT0" and len(fields) > 13:
                                    code = fields[0]
                                    if code in self.subscriptions:
                                        data = {
                                            "type": "trade",
                                            "code": code,
                                            "time": fields[1],
                                            "price": fields[2],
                                            "change": fields[4],
                                            "rate": fields[5],
                                            "volume": fields[12],
                                            "acml_vol": fields[13], 
                                            "power": fields[16] if len(fields) > 16 else "0.00"
                                        }
                                        
                                        json_data = json.dumps(data)
                                        targets = self.subscriptions[code].copy()
                                        for client in targets:
                                            try:
                                                await client.send_text(json_data)
                                            except:
                                                self.subscriptions[code].discard(client)

            except Exception as e:
                logger.error(f"KIS WS Disconnected: {e}")
                self.kis_websocket = None # 연결 끊김 표시
                await asyncio.sleep(3) 

from datetime import datetime
kis_ws_manager = KISWebSocketManager()