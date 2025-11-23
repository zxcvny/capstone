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
        # 해외 주식 (기본적으로 나스닥 'NAS' 조회)
        raw_data = await kis_data.get_overseas_ranking_data(rank_type, market_code="NAS")
        return raw_data

    else:
        # 국내 주식
        raw_data = await kis_data.get_ranking_data(rank_type)
        
        final_results = []
        for item in raw_data:
            name = stock_info_service.get_name(item['code'])
            if name:
                item['name'] = name
            final_results.append(item)
            
        return final_results

@router.get("/search")
async def search_stocks(keyword: str = Query(..., min_length=1)):
    """
    통합 종목 검색
    - 우선순위 1: 검색어 적합도 (정확도 > 시작 > 포함)
    - 우선순위 2: 시가총액 (높은 순)
    """
    # 1. 텍스트 유사도로 후보군 조회 (넉넉하게 30개 정도 가져옴)
    candidates = stock_info_service.search_stocks(keyword, limit=30)
    if not candidates:
        return []

    # 2. 비동기로 현재가 및 시가총액 정보 조회
    tasks = []
    for item in candidates:
        code = item['code']
        market = item.get('market', 'KR')
        
        if market == 'KR':
            tasks.append(kis_data.get_current_price(code))
        else:
            tasks.append(kis_data.get_overseas_current_price(code, market_code=market))

    price_infos = await asyncio.gather(*tasks)

    # 3. 결과 병합 및 시가총액 추출
    final_results = []
    for item, price_info in zip(candidates, price_infos):
        market_cap = 0.0
        
        if price_info:
            item['price'] = price_info.get('price', '-')
            item['change_rate'] = price_info.get('change_rate', '0.00')
            
            # 시가총액 파싱 (API 응답 구조에 따라 키값이 다를 수 있음)
            # 국내: hts_avls (단위: 억), 해외: valx (단위: 보통 백만 또는 원화환산액)
            try:
                if item['market'] == 'KR':
                    cap_str = price_info.get('hts_avls', '0')
                    market_cap = float(cap_str.replace(',', '')) if cap_str else 0
                else:
                    # 해외주식 시가총액 필드 (valx 등 API 문서 확인 필요)
                    cap_str = price_info.get('valx', '0') # 예시 키값
                    market_cap = float(cap_str.replace(',', '')) if cap_str else 0
            except (ValueError, AttributeError):
                market_cap = 0
        else:
            item['price'] = "-"
            item['change_rate'] = "0.00"
        
        item['market_cap'] = market_cap
        final_results.append(item)

    # 4. 최종 정렬
    # 1순위: score (오름차순 - 낮은게 정확도 높음)
    # 2순위: market_cap (내림차순 - 시총 큰게 위로)
    final_results.sort(key=lambda x: (x['score'], -x['market_cap']))

    # 5. 상위 10개 반환
    return final_results[:10]