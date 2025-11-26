import logging
import json
import asyncio
import websockets
from collections import defaultdict
from app.services.kis_auth import kis_auth
from app.services.kis_data import kis_data
from app.services.stock_info import stock_info_service 
from app.core.config import settings
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

class KISWebSocketManager:
    def __init__(self):
        self.subscriptions = defaultdict(set) 
        self.kis_websocket = None 
        self.approval_key = None
        self._stream_task = None

    async def get_approval_key(self):
        if not self.approval_key:
            self.approval_key = await kis_auth.get_approval_key()
        return self.approval_key

    async def connect_client(self, websocket, code: str):
        await websocket.accept()
        self.subscriptions[code].add(websocket)
        logger.info(f"✅ [{code}] 클라이언트 입장. 현재 구독자: {len(self.subscriptions[code])}명")

        # 1. 접속 즉시 스냅샷 (REST API)
        asyncio.create_task(self.send_snapshot(websocket, code))

        # 2. KIS 웹소켓 연결 확인
        if self.kis_websocket is None:
            if not self._stream_task or self._stream_task.done():
                self._stream_task = asyncio.create_task(self.start_kis_stream())
        
        # 3. 구독 요청
        if self.kis_websocket:
            await self.send_kis_subscription(code, "1")

    async def disconnect_client(self, websocket, code: str):
        if code in self.subscriptions:
            self.subscriptions[code].discard(websocket)
            if not self.subscriptions[code]:
                del self.subscriptions[code]

    async def send_kis_subscription(self, code, tr_type="1"):
        """국내/해외 구분하여 구독 요청"""
        if self.kis_websocket is None: return

        try:
            key = await self.get_approval_key()
            
            # [핵심] 국내/해외 TR ID 구분 로직
            # 국내 주식: 6자리 숫자 (예: 005930) -> H0STCNT0
            # 해외 주식: 영문 (예: TSLA, AAPL) -> H0GSCNT0
            if code.isdigit() and len(code) == 6:
                tr_id = "H0STCNT0" # 국내
            else:
                tr_id = "H0GSCNT0" # 해외 (미국)

            req = {
                "header": {
                    "approval_key": key,
                    "custtype": "P",
                    "tr_type": tr_type,
                    "content-type": "utf-8"
                },
                "body": {
                    "input": {
                        "tr_id": tr_id, 
                        "tr_key": code # 해외의 경우 DNASAAPL 형식이 필요할 수 있으나, 보통 심볼만 보내도 됨 (혹은 D+NAS+심볼)
                    }
                }
            }
            await self.kis_websocket.send(json.dumps(req))
            action = "구독" if tr_type == "1" else "해제"
            logger.info(f"📡 KIS에 [{code}] {tr_id} {action} 요청 전송")
            
        except Exception as e:
            logger.warning(f"⚠️ 구독 요청 실패: {e}")

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
        
        # KST 시간대 정의
        KST = timezone(timedelta(hours=9))
        
        while True:
            try:
                async with websockets.connect(f"{ws_url}/tryitout/H0STCNT0", ping_interval=60) as ws:
                    self.kis_websocket = ws
                    logger.info("🚀 KIS WebSocket 연결 성공")

                    for code in list(self.subscriptions.keys()):
                        await self.send_kis_subscription(code, "1")
                        await asyncio.sleep(0.1)

                    while True:
                        msg = await ws.recv()
                        
                        if msg[0] in ['0', '1']:
                            parts = msg.split('|')
                            if len(parts) > 3:
                                tr_id = parts[1]
                                raw_data = parts[3]
                                fields = raw_data.split('^')
                                
                                # 1. [국내 주식] H0STCNT0 (기존 동일)
                                if tr_id == "H0STCNT0" and len(fields) > 13:
                                    code = fields[0]
                                    if code in self.subscriptions:
                                        data = {
                                            "type": "trade", 
                                            "code": code,
                                            "time": fields[1], # 국내는 한국 시간이니 그대로 사용
                                            "price": fields[2],
                                            "change": fields[4],
                                            "rate": fields[5],
                                            "volume": fields[12],
                                            "acml_vol": fields[13], 
                                            "power": fields[16] if len(fields) > 16 else "0.00"
                                        }
                                        await self.broadcast(code, data)

                                # 2. [해외 주식] H0GSCNT0 (시간 수정)
                                elif tr_id == "H0GSCNT0" and len(fields) > 12:
                                    code = fields[0]
                                    if code in self.subscriptions:
                                        rate = 1460.0 
                                        
                                        try:
                                            price_usd = float(fields[2])
                                            price_krw = int(price_usd * rate)
                                            
                                            change_usd = float(fields[4])
                                            change_krw = int(change_usd * rate)
                                            
                                            # [핵심 수정] 미국 현지 시간을 버리고, 현재 한국 시간으로 대체
                                            # fields[1] (미국시간) -> datetime.now(KST)
                                            current_kst_time = datetime.now(KST).strftime("%H%M%S")

                                            data = {
                                                "type": "trade", 
                                                "code": code,
                                                "time": current_kst_time, # ★ 여기를 수정했습니다!
                                                "price": str(price_krw),
                                                "change": str(change_krw),
                                                "rate": fields[5],
                                                "volume": fields[12],
                                                "acml_vol": fields[11], 
                                                "power": "0.00"
                                            }
                                            await self.broadcast(code, data)
                                        except:
                                            pass

            except Exception as e:
                logger.error(f"KIS WS Disconnected: {e}")
                self.kis_websocket = None
                await asyncio.sleep(3) 

    async def broadcast(self, code, data):
        """해당 종목 구독자에게 데이터 전송"""
        if code in self.subscriptions:
            json_data = json.dumps(data)
            targets = self.subscriptions[code].copy()
            for client in targets:
                try:
                    await client.send_text(json_data)
                except:
                    self.subscriptions[code].discard(client)

kis_ws_manager = KISWebSocketManager()