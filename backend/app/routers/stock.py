from fastapi import APIRouter, Query
from app.services.stock_info import stock_info_service
from app.services.kis_data import kis_data
import asyncio

router = APIRouter(prefix="/stocks", tags=["Stocks"])

@router.get("/rank/{rank_type}")
async def get_stock_ranking(rank_type: str, market_type: str = "DOMESTIC"):
    """
    순위 데이터 조회
    - rank_type: volume, amount, cap, rise, fall
    - market_type: DOMESTIC(기본), OVERSEAS
    """
    if market_type == "OVERSEAS":
        # 해외 주식 (기본적으로 나스닥 'NAS' 조회, 필요시 파라미터 확장 가능)
        raw_data = await kis_data.get_overseas_ranking_data(rank_type, market_code="NAS")
        
        # 해외 주식은 API 응답 자체에 이미 name이 포함되어 있으므로 별도 매핑 불필요하거나,
        # 필요한 경우 여기서 추가 가공
        return raw_data

    else:
        # 국내 주식
        raw_data = await kis_data.get_ranking_data(rank_type)
        
        # 국내 종목명 매핑
        final_results = []
        for item in raw_data:
            # stock_info_service를 통해 한글 종목명 보완
            name = stock_info_service.get_name(item['code'])
            if name:
                item['name'] = name
            final_results.append(item)
            
        return final_results

@router.get("/search")
async def search_stocks(keyword: str = Query(..., min_length=1)):
    # ... (기존 코드 유지)
    results = stock_info_service.search_stocks(keyword, limit=10)
    if not results:
        return []

    tasks = []
    for item in results:
        code = item['code']
        market = item.get('market', 'KR')
        
        if market == 'KR':
            tasks.append(kis_data.get_current_price(code))
        else:
            tasks.append(kis_data.get_overseas_current_price(code, market_code=market))

    price_infos = await asyncio.gather(*tasks)

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