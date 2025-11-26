from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.kis_ws import kis_ws_manager
import asyncio
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/realtime", tags=["WebSocket"])

# router 코드는 님이 작성하신 것과 거의 동일하게 사용 가능합니다.
# 다만 클라이언트가 연결 끊었을 때 disconnect_client가 확실히 호출되도록
# finally 블록을 활용하는 것이 안전합니다.
@router.websocket("/top-volume")
async def top_volume_ws(websocket: WebSocket):
    await kis_ws_manager.connect_client(websocket)
    try:
        while True:
            # 클라이언트로부터 메시지를 받을 일이 없다면
            # 연결 유지용으로만 대기합니다.
            await websocket.receive_text()
    except WebSocketDisconnect:
        logger.info("✅ 클라이언트 연결 해제")
    except Exception as e:
        logger.error(f"⛔ 소켓 에러: {e}")
    finally:
        # 어떤 이유로든 루프가 끝나면 연결 해제 처리
        kis_ws_manager.disconnect_client(websocket)

@router.websocket("/stocks/{code}")
async def stock_ws(websocket: WebSocket, code: str):
    # 1. 매니저를 통해 연결 및 구독 등록
    await kis_ws_manager.connect_client(websocket, code)
    
    try:
        while True:
            # 클라이언트 메시지 대기 (연결 유지용)
            await websocket.receive_text()
            
    except WebSocketDisconnect:
        logger.info(f"✅ [{code}] 클라이언트 연결 해제")
        # 2. 연결 끊김 처리 (구독 해제 등)
        await kis_ws_manager.disconnect_client(websocket, code)
        
    except Exception as e:
        logger.error(f"⛔ 소켓 에러 [{code}]: {e}")
        await kis_ws_manager.disconnect_client(websocket, code)

