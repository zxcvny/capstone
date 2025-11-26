from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.kis_data import kis_data
from app.services.stock_info import stock_info_service
from app.services.kis_ws import kis_ws_manager
import asyncio
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/realtime", tags=["WebSocket"])

# ---------------------------------------------------------------------
# [1] 종목별 실시간 체결가 (기존 코드 유지)
# ---------------------------------------------------------------------
@router.websocket("/stocks/{code}")
async def stock_ws(websocket: WebSocket, code: str):
    await kis_ws_manager.connect_client(websocket, code)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await kis_ws_manager.disconnect_client(websocket, code)
    except Exception as e:
        logger.error(f"⛔ 소켓 에러 [{code}]: {e}")
        await kis_ws_manager.disconnect_client(websocket, code)

# ---------------------------------------------------------------------
# [2] 실시간 랭킹 웹소켓 (신규 추가)
# ---------------------------------------------------------------------
@router.websocket("/rankings")
async def ranking_ws(websocket: WebSocket, rank_type: str = "volume", market_type: str = "ALL"):
    """
    실시간 랭킹 데이터 스트림
    - rank_type: volume(거래량), amount(거래대금), cap(시가총액), rise(급상승), fall(급하락)
    - market_type: ALL, DOMESTIC, OVERSEAS
    """
    await websocket.accept()
    logger.info(f"📊 랭킹 소켓 연결: {rank_type} / {market_type}")
    
    try:
        while True:
            # 1. 데이터 조회 및 병합 로직
            overseas_rank_type = "market_cap" if rank_type == "cap" else rank_type
            final_data = []

            if market_type == "ALL":
                # 국내/해외 병렬 조회
                d_task = kis_data.get_ranking_data(rank_type)
                o_task = kis_data.get_overseas_ranking_data(overseas_rank_type, market_code="NAS")
                d_data, o_data = await asyncio.gather(d_task, o_task)

                # 국내 데이터 보정 (마켓명, 한글명)
                for item in d_data:
                    item['market'] = "KR"
                    name = stock_info_service.get_name(item['code'])
                    if name: item['name'] = name
                
                # 해외 데이터 보정
                for item in o_data:
                    if 'market' not in item: item['market'] = "NAS"

                combined = d_data + o_data
                
                # 정렬을 위한 헬퍼 함수 (문자열 -> 숫자 변환)
                def get_val(x, key):
                    try: return float(str(x.get(key, '0')).replace(',', ''))
                    except: return 0.0

                # 타입별 정렬 로직
                if rank_type == "rise":
                    combined.sort(key=lambda x: get_val(x, 'change_rate'), reverse=True)
                elif rank_type == "fall":
                    combined.sort(key=lambda x: get_val(x, 'change_rate'), reverse=False)
                elif rank_type == "cap":
                    combined.sort(key=lambda x: get_val(x, 'market_cap') if 'market_cap' in x else get_val(x, 'amount'), reverse=True)
                else: # volume, amount
                    combined.sort(key=lambda x: get_val(x, rank_type), reverse=True)
                
                final_data = combined[:30]

            elif market_type == "OVERSEAS":
                # 해외 단독
                final_data = await kis_data.get_overseas_ranking_data(overseas_rank_type, market_code="NAS")

            else: # DOMESTIC
                # 국내 단독
                raw_data = await kis_data.get_ranking_data(rank_type)
                for item in raw_data:
                    item['market'] = "KR"
                    name = stock_info_service.get_name(item['code'])
                    if name: item['name'] = name
                final_data = raw_data

            # 2. 클라이언트로 전송
            await websocket.send_json(final_data)

            # 3. 2초 대기 (API 호출 제한 고려)
            await asyncio.sleep(2) 

    except WebSocketDisconnect:
        logger.info("👋 랭킹 소켓 연결 해제")
    except Exception as e:
        logger.error(f"⛔ 랭킹 소켓 에러: {e}")
        try: await websocket.close()
        except: pass