from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.kis_ws import kis_ws_manager
import asyncio
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/realtime", tags=["WebSocket"])

@router.websocket("/top-volume")
async def top_volume_ws(websocket: WebSocket):
    await kis_ws_manager.connect_client(websocket)
    try:
        while True:
            await websocket.receive_text()  # ping, 클라이언트 연결 상태 감지
    except WebSocketDisconnect:
        logger.info("✅ 클라이언트가 WebSocket 연결을 해제했습니다.")
        kis_ws_manager.disconnect_client(websocket)
    except Exception as e:
        logger.error(f"⛔ WebSocket 처리 중 예기치 않은 오류 발생: {e}", exc_info=True)
        kis_ws_manager.disconnect_client(websocket)
