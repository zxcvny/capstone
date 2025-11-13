import logging
import json
import websockets
import asyncio

from app.services.kis_auth import kis_auth
from app.services.kis_data import kis_data
from app.core.config import settings

logger = logging.getLogger(__name__)

class KISWebSocketManager:
    clients = set()
    _stream_task = None # 스트림 태스크 관리

    async def connect_client(self, websocket):
        await websocket.accept()
        self.clients.add(websocket)
        # 첫 클라이언트가 연결되면 스트림 시작
        if not self._stream_task or self._stream_task.done():
            logger.info("✅ 첫 클라이언트 연결됨. KIS Top Volume 스트림을 시작합니다.")
            self._stream_task = asyncio.create_task(self.start_top_volume_stream())

    def disconnect_client(self, websocket):
        self.clients.discard(websocket)
        logger.info(f"✅ 클라이언트 연결 해제. 현재 클라이언트 수: {len(self.clients)}")
        # 클라이언트가 0명이면 스트림 중지
        if not self.clients and self._stream_task:
            logger.info("✅ 모든 클라이언트가 연결 해제됨. KIS 스트림을 중지합니다.")
            self._stream_task.cancel()
            self._stream_task = None

    async def broadcast(self, data):
        if not self.clients:
            return
        
        # 모든 클라이언트에 대해 비동기 전송 작업을 모음
        tasks = [client.send_json(data) for client in self.clients]
        # asyncio.gather를 사용하여 동시 전송 (예외 발생 시에도 계속 진행)
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for i, result in enumerate(results):
             if isinstance(result, Exception):
                logger.warning(f"⚠️ 클라이언트 {i}에게 브로드캐스트 중 오류: {result}")

    async def start_top_volume_stream(self):
        try:
            symbols = await kis_data.get_top_volume()
            approval_key = await kis_auth.get_approval_key()
            ws_url = f"{settings.KIS_WS_URL}"
            logger.info(f"✅ KIS WebSocket 연결 시도: {ws_url}")

            async with websockets.connect(ws_url, ping_interval=None) as ws:
                logger.info("✅ KIS WebSocket 연결 성공.")
                for symbol in symbols:
                    subscribe_msg = {
                        "header": {
                            "approval_key": approval_key,
                            "custtype": "P",
                            "tr_type": "1",
                            "content-type": "utf-8"
                        },
                        "body": {
                            "input": {
                                "tr_id": "H0STCNT0",  # 실시간 체결 정보
                                "tr_key": symbol
                            }
                        }
                    }
                    await ws.send(json.dumps(subscribe_msg))
                logger.info(f"✅ 총 {len(symbols)}개 종목 구독 완료.")

                while True:
                    msg = await ws.recv()
                    # 클라이언트가 있을 때만 브로드캐스트
                    if self.clients:
                        await self.broadcast(json.loads(msg))

        except websockets.exceptions.ConnectionClosed as e:
            logger.error(f"⛔ KIS WebSocket 연결 종료: {e}")
        except Exception as e:
            logger.error(f"⛔ KIS WebSocket 스트림 오류 발생: {e}", exc_info=True)
        finally:
            logger.info("✅ KIS 스트림 태스크 종료.")
            self._stream_task = None
            await self.broadcast({"type": "error", "message": "Real-time stream disconnected. Retrying soon."})

kis_ws_manager = KISWebSocketManager()
