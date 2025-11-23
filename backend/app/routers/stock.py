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
    - market_type: DOMESTIC(기본), OVERSEAS, ALL(전체)
    """
    # [공통 로직] 'cap'으로 요청이 오더라도 해외 주식 로직에는 'market_cap'으로 전달되도록 변환
    overseas_rank_type = "market_cap" if rank_type == "cap" else rank_type

    if market_type == "ALL":
        # 전체 보기: 국내/해외 병렬 조회 후 병합
        d_task = kis_data.get_ranking_data(rank_type) # 국내는 'cap' 그대로 사용
        o_task = kis_data.get_overseas_ranking_data(overseas_rank_type, market_code="NAS") # 해외는 변환된 값 사용
        
        d_data, o_data = await asyncio.gather(d_task, o_task)

        # 국내 주식 이름 매핑
        for item in d_data:
            name = stock_info_service.get_name(item['code'])
            if name:
                item['name'] = name
        
        # 데이터 병합
        combined_data = d_data + o_data

        # 정렬 로직 (수치 변환 후 비교)
        def get_value(item, key):
            try:
                val = item.get(key, '0')
                return float(val.replace(',', ''))
            except (ValueError, AttributeError):
                return 0.0

        if rank_type == "rise":
            combined_data.sort(key=lambda x: get_value(x, 'change_rate'), reverse=True)
        elif rank_type == "fall":
            combined_data.sort(key=lambda x: get_value(x, 'change_rate'), reverse=False)
        elif rank_type in ["volume", "amount"]:
            combined_data.sort(key=lambda x: get_value(x, rank_type), reverse=True)
        # cap(시가총액) 등 기타의 경우 기본적으로 큰 순서대로 정렬되어 있다고 가정하거나 
        # 필요 시 market_cap 기준으로 정렬 추가 가능
        if rank_type == "cap":
             combined_data.sort(key=lambda x: get_value(x, 'market_cap') if 'market_cap' in x else get_value(x, 'amount'), reverse=True) # amount가 아닌 시총값 필요하지만 API 특성상 주의
        
        return combined_data[:30] # [수정] 30개로 제한

    elif market_type == "OVERSEAS":
        # [수정] 해외 주식 단독 조회 시에도 'cap' -> 'market_cap' 자동 변환 적용
        raw_data = await kis_data.get_overseas_ranking_data(overseas_rank_type, market_code="NAS")
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
    candidates = stock_info_service.search_stocks(keyword, limit=10)
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