from fastapi import APIRouter, Query
from app.services.stock_info import stock_info_service
from app.services.kis_data import kis_data
import asyncio

router = APIRouter(prefix="/stocks", tags=["Stocks"])

@router.get("/rank/{rank_type}")
async def get_stock_ranking(rank_type: str):
    """
    순위 데이터 조회 (volume, amount, cap, rise, fall)
    """
    # 1. API로 순위 데이터(코드, 현재가, 거래대금 등) 가져오기
    raw_data = await kis_data.get_ranking_data(rank_type)
    
    # 2. 종목명 매핑 (서비스에서 이름 추가)
    final_results = []
    for item in raw_data:
        item['name'] = stock_info_service.get_name(item['code'])
        final_results.append(item)
        
    return final_results

@router.get("/search")
async def search_stocks(keyword: str = Query(..., min_length=1)):
    # 1. 검색 서비스 호출 (market 정보 포함됨)
    results = stock_info_service.search_stocks(keyword, limit=10)
    if not results:
        return []

    # 2. 비동기로 가격 조회 (국내/해외 분기 처리)
    tasks = []
    for item in results:
        code = item['code']
        market = item.get('market', 'KR') # 기본값 KR
        
        if market == 'KR':
            tasks.append(kis_data.get_current_price(code))
        else:
            # 해외 주식인 경우 해외 전용 메서드 호출 (예: NAS)
            tasks.append(kis_data.get_overseas_current_price(code, market_code=market))

    price_infos = await asyncio.gather(*tasks)

    # 3. 결과 합치기
    final_results = []
    for item, price_info in zip(results, price_infos):
        if price_info:
            item['price'] = price_info['price']
            item['change_rate'] = price_info['change_rate']
            # 필요 시 volume, amount 등도 추가 가능
        else:
            item['price'] = "-"
            item['change_rate'] = "0.00"
        final_results.append(item)

    return final_results