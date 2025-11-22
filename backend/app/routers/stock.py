from fastapi import APIRouter, Query
from app.services.stock_info import stock_info_service
from app.services.kis_data import kis_data
import asyncio

router = APIRouter(prefix="/stocks", tags=["Stocks"])

@router.get("/search")
async def search_stocks(keyword: str = Query(..., min_length=1)):
    """
    종목 검색 (시세 포함)
    - 검색어와 일치하는 종목 최대 10개를 찾고,
    - 각 종목의 현재가 정보를 병렬로 조회하여 반환합니다.
    """
    # 1. 종목명/코드로 검색 (최대 10개로 변경)
    results = stock_info_service.search_stocks(keyword, limit=10)
    
    if not results:
        return []

    # 2. 검색된 종목들의 현재가 병렬 조회
    tasks = [kis_data.get_current_price(item['code']) for item in results]
    price_infos = await asyncio.gather(*tasks)

    # 3. 검색 결과에 시세 정보 합치기
    final_results = []
    for item, price_info in zip(results, price_infos):
        if price_info:
            item['price'] = price_info['price']
            item['change_rate'] = price_info['change_rate']
        else:
            item['price'] = "-"
            item['change_rate'] = "0.00"
        final_results.append(item)

    return final_results