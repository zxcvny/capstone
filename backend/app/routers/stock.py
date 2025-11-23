from fastapi import APIRouter, Query
from app.services.stock_info import stock_info_service
from app.services.kis_data import kis_data
import asyncio
from datetime import datetime, timedelta

router = APIRouter(prefix="/stocks", tags=["Stocks"])

# --- [날짜 계산 유틸리티 함수] ---
def get_trading_dates():
    """
    오늘 날짜와 직전 영업일(전날) 날짜를 계산하여 반환 (MM.DD 포맷)
    """
    now = datetime.now()
    today_str = now.strftime("%Y.%m.%d")
    

    # 전날 계산 (월요일이면 금요일이 전날)
    if now.weekday() == 0: # 월요일
        prev_day = now - timedelta(days=3)
    elif now.weekday() == 6: # 일요일
        prev_day = now - timedelta(days=2)
    else: # 화~토
        prev_day = now - timedelta(days=1)
        
    prev_date_str = prev_day.strftime("%Y.%m.%d")
    
    return today_str, prev_date_str

# [1] 랭킹 조회 (기존 유지)
@router.get("/rank/{rank_type}")
async def get_stock_ranking(rank_type: str, market_type: str = "DOMESTIC"):
    if market_type == "OVERSEAS":
        return await kis_data.get_overseas_ranking_data(rank_type, market_code="NAS")
    else:
        raw_data = await kis_data.get_ranking_data(rank_type)
        final_results = []
        for item in raw_data:
            name = stock_info_service.get_name(item['code'])
            if name:
                item['name'] = name
            final_results.append(item)
        return final_results

# [2] 종목 검색 (기존 유지)
@router.get("/search")
async def search_stocks(keyword: str = Query(..., min_length=1)):
    candidates = stock_info_service.search_stocks(keyword, limit=10)
    if not candidates:
        return []

    tasks = []
    for item in candidates:
        code = item['code']
        market = item.get('market', 'KR')
        if market == 'KR':
            tasks.append(kis_data.get_current_price(code))
        else:
            tasks.append(kis_data.get_overseas_current_price(code, market_code=market))

    price_infos = await asyncio.gather(*tasks)
    
    final_results = []
    for item, price_info in zip(candidates, price_infos):
        market_cap = 0.0
        if price_info:
            item['price'] = price_info.get('price', '-')
            item['change_rate'] = price_info.get('change_rate', '0.00')
            try:
                cap_str = price_info.get('amount', '0') 
                market_cap = float(cap_str.replace(',', '')) if cap_str else 0
            except:
                market_cap = 0
        else:
            item['price'] = "-"
            item['change_rate'] = "0.00"
        
        item['market_cap'] = market_cap
        final_results.append(item)

    final_results.sort(key=lambda x: (x.get('score', 999), -x['market_cap']))
    return final_results[:10]

# [3] 상세 정보 조회 (날짜 로직 적용)
@router.get("/{market}/{code}/detail")
async def get_stock_detail(market: str, code: str):
    # 1. API 데이터 조회
    detail_data = await kis_data.get_stock_detail(market, code)
    
    # 2. 이름 보완
    name = stock_info_service.get_name(code)
    if name: 
        detail_data["name"] = name

    # 3. 날짜 정보 추가 (오늘, 전날)
    today_str, prev_date_str = get_trading_dates()
    detail_data["date"] = today_str      # 오늘 (예: 11.24)
    detail_data["prev_date"] = prev_date_str # 전날 (예: 11.22)

    # 4. ROE 계산
    try:
        eps = float(str(detail_data.get('eps', 0)).replace(',', ''))
        bps = float(str(detail_data.get('bps', 0)).replace(',', ''))
        
        if bps > 0:
            roe = (eps / bps) * 100
            detail_data['roe'] = f"{roe:.2f}"
        else:
            detail_data['roe'] = "0"
    except:
        detail_data['roe'] = "0"

    return detail_data

# [4] 차트 데이터 조회 (기존 유지)
@router.get("/{market}/{code}/chart")
async def get_stock_chart(market: str, code: str, period: str = "day"):
    return await kis_data.get_stock_chart(market, code, period)

@router.get("/{market}/{code}/hoga")
async def get_stock_hoga(market: str, code: str):
    """호가 데이터 조회"""
    return await kis_data.get_hoga(market, code)

@router.get("/{market}/{code}/trades")
async def get_stock_trades(market: str, code: str):
    """체결 내역 조회"""
    return await kis_data.get_recent_trades(market, code)