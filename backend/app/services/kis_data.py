import httpx
import logging
import time
from datetime import datetime, timedelta, timezone
from app.services.kis_auth import kis_auth
from app.core.config import settings

logger = logging.getLogger(__name__)

class KisDataService:
    def __init__(self):
        # 환율 캐싱을 위한 변수 (1시간마다 갱신)
        self.cached_rate = 1460.0 
        self.last_fetch_time = 0
        self.cache_duration = 3600 

    async def get_exchange_rate(self):
        """
        [자동 환율 조회]
        외부 API를 통해 실시간 환율을 가져옵니다.
        """
        current_time = time.time()
        
        # 캐시된 시간이 지났거나, 초기 상태라면 API 호출
        if current_time - self.last_fetch_time > self.cache_duration:
            try:
                # 무료 환율 API (USD 기준)
                url = "https://open.er-api.com/v6/latest/USD"
                
                async with httpx.AsyncClient(timeout=3.0) as client:
                    response = await client.get(url)
                    
                    if response.status_code == 200:
                        data = response.json()
                        rate = data['rates']['KRW']
                        
                        self.cached_rate = rate
                        self.last_fetch_time = current_time
                        logger.info(f"💱 최신 환율 갱신 완료: 1 USD = {rate} KRW")
                    else:
                        logger.warning("환율 API 호출 실패, 기존 캐시값 사용")
            
            except Exception as e:
                logger.error(f"환율 조회 중 에러 발생: {e}")
        
        return self.cached_rate

    # ---------------------------------------------------------
    # [국내 주식] 관련 메서드
    # ---------------------------------------------------------
    async def get_top_volume(self):
        """기존 메서드 호환성 유지"""
        data = await self.get_ranking_data("volume")
        return [item['code'] for item in data]

    async def get_ranking_data(self, rank_type="volume"):
        """국내 주식 순위 데이터 조회"""
        tr_id = ""
        path = ""
        params = {}

        if rank_type in ["volume", "amount"]: 
            tr_id = "FHPST01710000"
            path = "/uapi/domestic-stock/v1/quotations/volume-rank"
            sort_code = "3" if rank_type == "amount" else "0" 
            params = {
                "FID_COND_MRKT_DIV_CODE": "J",
                "FID_COND_SCR_DIV_CODE": "20171",
                "FID_INPUT_ISCD": "0000",
                "FID_DIV_CLS_CODE": "0",
                "FID_BLNG_CLS_CODE": sort_code, 
                "FID_TRGT_CLS_CODE": "11111111",
                "FID_TRGT_EXLS_CLS_CODE": "000000",
                "FID_INPUT_PRICE_1": "",
                "FID_INPUT_PRICE_2": "",
                "FID_VOL_CNT": "",
                "FID_INPUT_DATE_1": ""
            }
        elif rank_type == "cap":
            tr_id = "FHPST01740000"
            path = "/uapi/domestic-stock/v1/ranking/market-cap" 
            params = {
                "FID_COND_MRKT_DIV_CODE": "J",
                "FID_COND_SCR_DIV_CODE": "20174",
                "FID_DIV_CLS_CODE": "0",
                "FID_INPUT_ISCD": "0000",
                "FID_TRGT_CLS_CODE": "11111111",
                "FID_TRGT_EXLS_CLS_CODE": "000000",
                "FID_INPUT_PRICE_1": "",
                "FID_INPUT_PRICE_2": "",
                "FID_VOL_CNT": "",
                "FID_INPUT_DATE_1": ""
            }
        elif rank_type in ["rise", "fall"]:
            tr_id = "FHPST01700000"
            path = "/uapi/domestic-stock/v1/ranking/fluctuation"
            sort_cls_code = "0" if rank_type == "rise" else "1"
            params = {
                "FID_RSFL_RATE2": "",
                "FID_COND_MRKT_DIV_CODE": "J",
                "FID_COND_SCR_DIV_CODE": "20170",
                "FID_INPUT_ISCD": "0000",
                "FID_RANK_SORT_CLS_CODE": sort_cls_code,
                "FID_INPUT_CNT_1": "0",
                "FID_PRC_CLS_CODE": "1",
                "FID_INPUT_PRICE_1": "",
                "FID_INPUT_PRICE_2": "",
                "FID_VOL_CNT": "",
                "FID_TRGT_CLS_CODE": "0",
                "FID_TRGT_EXLS_CLS_CODE": "0",
                "FID_DIV_CLS_CODE": "0",
                "FID_RSFL_RATE1": ""
            }
        else:
            return []

        output = await self._fetch_ranking(tr_id, params, path)
        results = []
        for item in output[:30]:
            mapped_item = self._map_ranking_item(item)
            if mapped_item['code']:
                results.append(mapped_item)
        return results

    # ---------------------------------------------------------
    # [해외 주식] 관련 메서드 (수정됨)
    # ---------------------------------------------------------
    async def get_overseas_top_volume(self, market_code="NAS"):
        """해외(미국) 거래량 상위 종목 코드 리스트 반환"""
        data = await self.get_overseas_ranking_data("volume", market_code)
        return [item['code'] for item in data]

    async def get_overseas_ranking_data(self, rank_type="volume", market_code="NAS"):
        """
        해외 주식 순위 조회 (달러 -> 원화 변환 및 거래대금 계산 로직 개선)
        rank_type: volume, amount, market_cap, rise, fall
        """
        tr_id = ""
        path = ""
        # 기본 파라미터
        params = {
            "AUTH": "",
            "EXCD": market_code, # 기본 NAS(나스닥)
            "KEYB": "",
            "VOL_RANG": "0"
        }

        # 1. API 정보 설정
        if rank_type == "market_cap":
            tr_id = "HHDFS76350100"
            path = "/uapi/overseas-stock/v1/ranking/market-cap"
            
        elif rank_type == "volume":
            tr_id = "HHDFS76310010"
            path = "/uapi/overseas-stock/v1/ranking/trade-vol"
            params.update({"NDAY": "0", "PRC1": "", "PRC2": ""})

        elif rank_type == "amount":
            tr_id = "HHDFS76320010"
            path = "/uapi/overseas-stock/v1/ranking/trade-pbmn"
            params.update({"NDAY": "0", "PRC1": "", "PRC2": ""})

        elif rank_type in ["rise", "fall"]:
            tr_id = "HHDFS76290000"
            path = "/uapi/overseas-stock/v1/ranking/updown-rate"
            gubn_code = "1" if rank_type == "rise" else "0"
            # 급등락 조회 시 거래량 100주 이상 조건 추가 (동전주 필터링)
            params.update({"GUBN": gubn_code, "NDAY": "0", "VOL_RANG": "0"})
        else:
            return []

        # 2. API 호출
        output = await self._fetch_ranking(tr_id, params, path)
        
        # 3. 현재 환율 가져오기
        exchange_rate = await self.get_exchange_rate()

        results = []
        # 해외 주식 데이터 매핑 및 환율 적용
        for item in output[:30]:
            code = item.get('symb')
            
            if not code: continue

            try:
                # 1) 현재가 (달러 -> 원화)
                price_usd = float(item.get('last') or 0)
                price_krw = int(price_usd * exchange_rate)
                
                # 2) 거래량
                volume = float(item.get('tvol') or 0)

                # 3) 거래대금 계산 (핵심 수정)
                # 거래대금 순위(amount)나 거래량 순위(volume) API는 'tamt'(거래대금) 필드를 줍니다.
                # 하지만 시가총액(market_cap)이나 급등락(rise/fall) API는 'tamt'를 안 주거나 'tomv'(시가총액)를 줍니다.
                if rank_type in ["amount", "volume"] and item.get('tamt'):
                    amount_usd = float(item['tamt'])
                else:
                    # 시가총액 순위, 급등락 순위에서는 직접 계산 (현재가 x 거래량)
                    amount_usd = price_usd * volume

                # 원화 환산
                amount_krw = int(amount_usd * exchange_rate)

            except ValueError:
                price_krw = 0
                amount_krw = 0
                volume = 0

            results.append({
                "code": code,
                "name": item.get('name') or item.get('ename'),
                "price": str(price_krw),         # 원화 가격
                "change_rate": item.get('rate'), # 등락률
                "volume": str(int(volume)),      # 거래량
                "amount": str(amount_krw)        # 거래대금 (원화)
            })
            
        return results

    async def get_current_price(self, code: str):
        """국내 주식 현재가 단건 조회"""
        try:
            token = await kis_auth.get_access_token()
            headers = {
                "content-type": "application/json",
                "authorization": f"Bearer {token}",
                "appkey": settings.KIS_APP_KEY,
                "appsecret": settings.KIS_SECRET_KEY, 
                "tr_id": "FHKST01010100" 
            }
            params = { "fid_cond_mrkt_div_code": "J", "fid_input_iscd": code }

            async with httpx.AsyncClient() as client:
                url = f"{settings.KIS_BASE_URL}/uapi/domestic-stock/v1/quotations/inquire-price"
                response = await client.get(url, headers=headers, params=params)
                
                if response.status_code == 200:
                    res_json = response.json()
                    if res_json.get('rt_cd') == '0':
                        output = res_json.get('output', {})
                        return {
                            "code": code,
                            "price": output.get('stck_prpr'),
                            "change_rate": output.get('prdy_ctrt'),
                            "volume": output.get('acml_vol'),
                            "amount": output.get('acml_tr_pbmn')
                        }
        except Exception:
            return None
        return None

    async def get_overseas_current_price(self, code: str, market_code: str = "NAS"):
        """해외 주식 현재가 단건 조회 (자동 환율 계산 적용)"""
        try:
            token = await kis_auth.get_access_token()
            headers = {
                "content-type": "application/json",
                "authorization": f"Bearer {token}",
                "appkey": settings.KIS_APP_KEY,
                "appsecret": settings.KIS_SECRET_KEY, 
                "tr_id": "HHDFS00000300"
            }
            params = { "AUTH": "", "EXCD": market_code, "SYMB": code }

            async with httpx.AsyncClient() as client:
                url = f"{settings.KIS_BASE_URL}/uapi/overseas-price/v1/quotations/price"
                response = await client.get(url, headers=headers, params=params)
                
                if response.status_code == 200:
                    res_json = response.json()
                    if res_json.get('rt_cd') == '0':
                        output = res_json.get('output', {})
                        
                        price_usd = float(output.get('last') or 0)
                        exchange_rate = await self.get_exchange_rate()
                        price_krw = int(price_usd * exchange_rate)
                        
                        # 단건 조회 시 거래대금(tamt)이 없으면 직접 계산
                        tamt = output.get('tamt')
                        if not tamt:
                             tvol = float(output.get('tvol') or 0)
                             tamt = price_usd * tvol
                        
                        amount_krw = int(float(tamt) * exchange_rate)

                        return {
                            "code": code,
                            "price": str(price_krw),
                            "change_rate": output.get('rate'),
                            "volume": output.get('tvol'),
                            "amount": str(amount_krw)
                        }
        except Exception as e:
            logger.error(f"Overseas Price Error: {e}")
            return None
        return None

    # ---------------------------------------------------------
    # 공통 / 유틸리티
    # ---------------------------------------------------------
    async def _fetch_ranking(self, tr_id, params, path):
        """순위 조회 공통 메서드 (output, output2 모두 대응)"""
        try:
            token = await kis_auth.get_access_token()
            headers = {
                "content-type": "application/json",
                "authorization": f"Bearer {token}",
                "appkey": settings.KIS_APP_KEY,
                "appsecret": settings.KIS_SECRET_KEY,
                "tr_id": tr_id,
                "custtype": "P"
            }
            
            async with httpx.AsyncClient() as client:
                url = f"{settings.KIS_BASE_URL}{path}"
                response = await client.get(url, headers=headers, params=params)
                
                if response.status_code == 200:
                    res_json = response.json()
                    if res_json.get('rt_cd') == '0':
                        # 국내는 주로 output, 해외는 주로 output2에 리스트가 옴
                        return res_json.get('output') or res_json.get('output2') or []
                    else:
                        msg = res_json.get('msg1') or "알 수 없는 오류"
                        logger.error(f"API Error ({tr_id}): {msg}")
                        return []
                else:
                    logger.error(f"HTTP Error {response.status_code}: {response.text}")
                    return []
        except Exception as e:
            logger.error(f"Fetch Ranking Error: {e}")
            return []

    def _map_ranking_item(self, item):
        """국내 주식 데이터 매핑 헬퍼"""
        code = item.get('mksc_shrn_iscd') or item.get('stck_shrn_iscd')
        amount = item.get('acml_tr_pbmn') or item.get('tr_pbmn') or item.get('avrg_tr_pbmn')
        price = item.get('stck_prpr')
        rate = item.get('prdy_ctrt')
        volume = item.get('acml_vol')

        if not amount and price and volume:
            try:
                calc_amount = int(price) * int(volume)
                amount = str(calc_amount)
            except (ValueError, TypeError):
                amount = "0"
        
        if not amount: amount = "0"

        return {
            "code": code,
            "name": item.get('hts_kor_isnm'), 
            "price": price,
            "change_rate": rate,
            "volume": volume,
            "amount": amount
        }

    async def get_stock_detail(self, market: str, code: str):
        """
        종목 상세 정보 조회
        - 시가총액(market_cap)은 모두 '억 원' 단위로 통일하여 반환합니다.
        """
        data = {
            "market": market, "code": code, "price": "0", "diff": "0",
            "change_rate": "0.00", "market_cap": "0", "shares_outstanding": "0",
            "per": "0.00", "pbr": "0.00", "eps": "0", "bps": "0",
            "open_date": "-", "vol_power": "0.00"
        }
        try:
            token = await kis_auth.get_access_token()
            headers = {
                "content-type": "application/json",
                "authorization": f"Bearer {token}",
                "appkey": settings.KIS_APP_KEY,
                "appsecret": settings.KIS_SECRET_KEY
            }

            if market == "KR":
                headers["tr_id"] = "FHKST01010100"
                params = { "fid_cond_mrkt_div_code": "J", "fid_input_iscd": code }
                path = "/uapi/domestic-stock/v1/quotations/inquire-price"
                async with httpx.AsyncClient() as client:
                    res = await client.get(f"{settings.KIS_BASE_URL}{path}", headers=headers, params=params)
                    if res.status_code == 200:
                        out = res.json().get('output', {})
                        data.update({
                            "price": out.get('stck_prpr'), "diff": out.get('prdy_vrss'),
                            "change_rate": out.get('prdy_ctrt'), 
                            "market_cap": out.get('hts_avls'), # 국내는 이미 '억' 단위
                            "shares_outstanding": out.get('lstn_stcn'), "per": out.get('per'),
                            "pbr": out.get('pbr'), "eps": out.get('eps'), "bps": out.get('bps'),
                            "vol_power": out.get('vol_tnrt')
                        })
            else:
                # [해외] 데이터 직접 계산 및 환율 적용
                headers["tr_id"] = "HHDFS76200200"
                params = { "AUTH": "", "EXCD": "NAS", "SYMB": code }
                path = "/uapi/overseas-price/v1/quotations/price-detail"
                async with httpx.AsyncClient() as client:
                    res = await client.get(f"{settings.KIS_BASE_URL}{path}", headers=headers, params=params)
                    if res.status_code == 200:
                        out = res.json().get('output', {})
                        rate = await self.get_exchange_rate()
                        
                        # 1. 가격 데이터 추출 (달러)
                        last = float(out.get('last') or 0)  # 현재가
                        base = float(out.get('base') or 0)  # 전일종가
                        tomv = float(out.get('tomv') or 0)  # 시가총액
                        eps_usd = float(out.get('epsx') or 0) # EPS
                        bps_usd = float(out.get('bpsx') or 0) # BPS

                        # 2. 등락률 및 전일대비 직접 계산 (API 미제공 대비)
                        diff_usd = last - base
                        if base > 0:
                            change_rate = f"{((diff_usd / base) * 100):.2f}"
                        else:
                            change_rate = "0.00"

                        # 3. 원화 환산
                        price_krw = int(last * rate)
                        diff_krw = int(diff_usd * rate)
                        market_cap_krw_eok = (tomv * rate) / 100000000 # 억 단위
                        eps_krw = int(eps_usd * rate)
                        bps_krw = int(bps_usd * rate)

                        data.update({
                            "price": str(price_krw),
                            "diff": str(diff_krw),
                            "change_rate": str(change_rate),
                            "market_cap": str(int(market_cap_krw_eok)),
                            "shares_outstanding": out.get('shar') or "0",
                            "per": out.get('perx') or "0.00",
                            "pbr": out.get('pbrx') or "0.00",
                            "eps": str(eps_krw),  # 원화로 변환됨
                            "bps": str(bps_krw)   # 원화로 변환됨
                        })
        except Exception as e:
            logger.error(f"Detail Error: {e}")
        return data

   # ---------------------------------------------------------
    # [차트 조회] 핵심 메서드
    # ---------------------------------------------------------
    async def get_stock_chart(self, market: str, code: str, period: str):
        chart_data = []
        
        # 1. KST 시간대 정의 (UTC+9)
        KST = timezone(timedelta(hours=9))
        # 2. 현재 한국 시간 및 날짜 확정
        now_kst = datetime.now(KST)
        today = now_kst.strftime("%Y%m%d")

        try:
            token = await kis_auth.get_access_token()
            headers = {
                "content-type": "application/json",
                "authorization": f"Bearer {token}",
                "appkey": settings.KIS_APP_KEY,
                "appsecret": settings.KIS_SECRET_KEY
            }
            
            # 과거 데이터 조회용 기준일 (2년 전)
            target_start_date = (now_kst - timedelta(days=365*2)).strftime("%Y%m%d")
            
            # 실시간 모드 및 분봉 여부 판단
            is_realtime = (period == "realtime")
            is_minute = ("m" in period) or is_realtime

            # =================================================
            # 1. [국내 주식] (KR)
            # =================================================
            if market == "KR":
                if is_minute:
                    # [국내 분봉 / 실시간]
                    headers["tr_id"] = "FHKST03010230" 
                    path = "/uapi/domestic-stock/v1/quotations/inquire-time-dailychartprice"
                    
                    curr_date = today
                    # 실시간이면 현재 시간, 과거 조회면 장 마감 시간(15:30) 기준
                    curr_time = now_kst.strftime("%H%M%S") if is_realtime else "153000"
                    
                    # 페이징 (최대 100페이지)
                    for _ in range(100): 
                        params = {
                            "FID_COND_MRKT_DIV_CODE": "J", 
                            "FID_INPUT_ISCD": code, 
                            "FID_INPUT_DATE_1": curr_date, 
                            "FID_INPUT_HOUR_1": curr_time, 
                            "FID_PW_DATA_INCU_YN": "Y", 
                            "FID_FAKE_TICK_INCU_YN": "N"
                        }
                        async with httpx.AsyncClient() as client:
                            res = await client.get(f"{settings.KIS_BASE_URL}{path}", headers=headers, params=params)
                            if res.status_code != 200: break
                            
                            items = res.json().get('output2', [])
                            if not items: break
                            
                            for item in items:
                                d, t, c = item.get('stck_bsop_date'), item.get('stck_cntg_hour'), item.get('stck_prpr')
                                if d and t and c:
                                    dt_kr = datetime.strptime(f"{d}{t}", "%Y%m%d%H%M%S").replace(tzinfo=KST)
                                    ts = int(dt_kr.timestamp())

                                    # [국내 실시간 필터링]
                                    if is_realtime:
                                        # 1. 오늘 날짜가 아니면 제외
                                        if d != today: continue
                                        
                                        # 2. 정규장 시간(09:00 ~ 15:30) 외 데이터 제외
                                        time_int = int(t)
                                        if time_int < 90000 or time_int > 153000:
                                            continue

                                    chart_data.append({
                                        "time": ts, 
                                        "open": float(item['stck_oprc']), 
                                        "high": float(item['stck_hgpr']), 
                                        "low": float(item['stck_lwpr']), 
                                        "close": float(c), 
                                        "volume": float(item['cntg_vol'] or 0)
                                    })
                            
                            last = items[-1]
                            curr_date, curr_time = last.get('stck_bsop_date'), last.get('stck_cntg_hour')
                            
                            # [종료 조건]
                            # 실시간: 날짜가 어제로 넘어가면 종료
                            if is_realtime and curr_date < today: break
                            # 과거 조회: 1년 넘어가면 종료
                            if not is_realtime and curr_date < (now_kst - timedelta(days=365)).strftime("%Y%m%d"): break
                    
                    # [국내 분봉 병합] (실시간이 아니고 1분봉이 아닐 때만 수행)
                    if not is_realtime and period != '1m' and period != 'minute':
                        interval = int(period.replace('m', ''))
                        chart_data = self._aggregate_minute_data(chart_data, interval, start_h=9, start_m=0)

                else:
                    # [국내 일봉/주봉/월봉]
                    headers["tr_id"] = "FHKST03010100"
                    path = "/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice"
                    p_code = {"D": "D", "W": "W", "M": "M", "Y": "Y"}.get(period, "D")
                    curr_end_date = today
                    
                    for _ in range(10): 
                        params = {
                            "FID_COND_MRKT_DIV_CODE": "J", 
                            "FID_INPUT_ISCD": code, 
                            "FID_INPUT_DATE_1": target_start_date, 
                            "FID_INPUT_DATE_2": curr_end_date, 
                            "FID_PERIOD_DIV_CODE": p_code, 
                            "FID_ORG_ADJ_PRC": "1"
                        }
                        async with httpx.AsyncClient() as client:
                            res = await client.get(f"{settings.KIS_BASE_URL}{path}", headers=headers, params=params)
                            if res.status_code != 200: break
                            
                            items = res.json().get('output2', [])
                            if not items: break
                            
                            for item in items:
                                d = item.get('stck_bsop_date')
                                if d: 
                                    # 일봉 시간 고정: 09:00:00 KST
                                    dt_kr = datetime.strptime(d, "%Y%m%d").replace(hour=9, minute=0, second=0, tzinfo=KST)
                                    ts = int(dt_kr.timestamp())

                                    chart_data.append({
                                        "time": ts, 
                                        "open": float(item['stck_oprc']), 
                                        "high": float(item['stck_hgpr']), 
                                        "low": float(item['stck_lwpr']), 
                                        "close": float(item['stck_clpr']), 
                                        "volume": float(item['acml_vol'] or 0)
                                    })
                                    
                            if items: curr_end_date = (datetime.strptime(items[-1]['stck_bsop_date'], "%Y%m%d") - timedelta(days=1)).strftime("%Y%m%d")
                            if curr_end_date < target_start_date or len(items) < 100: break

            # =================================================
            # 2. [해외 주식] (NAS 등)
            # =================================================
            else:
                market_code = "NAS"
                if is_minute:
                    # [해외 분봉 / 실시간]
                    nmin = "1"
                    # 과거 조회이고 1분봉이 아니면 API 단계에서 n분봉 요청 가능 (단, 여기선 로직 통일을 위해 1분 요청 후 병합 권장)
                    if not is_realtime and period != '1m' and period != 'minute':
                        nmin = period.replace('m', '')
                    else:
                        nmin = "1"

                    headers["tr_id"] = "HHDFS76950200"
                    path = "/uapi/overseas-price/v1/quotations/inquire-time-itemchartprice"
                    next_key = ""
                    
                    for _ in range(30):
                        params = {"AUTH":"", "EXCD":market_code, "SYMB":code, "NMIN":nmin, "PINC":"1", "NEXT":"1" if next_key else "", "NREC":"120", "KEYB":next_key}
                        async with httpx.AsyncClient() as client:
                            res = await client.get(f"{settings.KIS_BASE_URL}{path}", headers=headers, params=params)
                            if res.status_code != 200: break
                            
                            body = res.json()
                            items = body.get('output2', [])
                            if not items: break
                            
                            for item in items:
                                d, t = item.get('kymd'), item.get('khms')
                                if d and t: 
                                    dt_kr = datetime.strptime(f"{d}{t}", "%Y%m%d%H%M%S").replace(tzinfo=KST)
                                    ts = int(dt_kr.timestamp())

                                    # [해외 실시간 필터링]
                                    if is_realtime:
                                        time_int = int(t) # HHMMSS
                                        # 23:30 ~ 06:00 사이의 데이터만 허용
                                        # (233000 이상) OR (060000 이하)
                                        if not (time_int >= 233000 or time_int <= 60000):
                                            continue

                                    chart_data.append({
                                        "time": ts, 
                                        "open": float(item['open']), 
                                        "high": float(item['high']), 
                                        "low": float(item['low']), 
                                        "close": float(item['last']), 
                                        "volume": float(item['evol'] or 0)
                                    })
                            
                            if body.get('output1', {}).get('next') == "1":
                                next_key = (items[-1].get('xymd') or "") + (items[-1].get('xhms') or "")
                            else: break
                            
                            # 실시간이면 1회(최신 120개)만 받고 종료
                            if is_realtime: break 
                    
                    # [해외 분봉 병합] (실시간이 아닐 때만)
                    if not is_realtime and period != '1m' and period != 'minute':
                         interval = int(period.replace('m', ''))
                         # 해외 시작시간: 23:30
                         chart_data = self._aggregate_minute_data(chart_data, interval, start_h=23, start_m=30)

                else:
                    # [해외 일봉/주봉/월봉]
                    headers["tr_id"] = "HHDFS76240000"
                    path = "/uapi/overseas-price/v1/quotations/dailyprice"
                    gubn = {"D":"0", "W":"1", "M":"2", "Y":"2"}.get(period, "0")
                    curr_base_date = today
                    
                    for _ in range(5):
                        params = {"AUTH":"", "EXCD":market_code, "SYMB":code, "GUBN":gubn, "BYMD":curr_base_date, "MODP":"1"}
                        async with httpx.AsyncClient() as client:
                            res = await client.get(f"{settings.KIS_BASE_URL}{path}", headers=headers, params=params)
                            if res.status_code != 200: break
                            
                            items = res.json().get('output2', [])
                            if not items: break
                            
                            for item in items:
                                d = item.get('xymd')
                                if d: 
                                    # 일봉 시간 고정: 23:30:00 KST
                                    dt_kr = datetime.strptime(d, "%Y%m%d").replace(hour=23, minute=30, second=0, tzinfo=KST)
                                    ts = int(dt_kr.timestamp())

                                    chart_data.append({
                                        "time": ts, 
                                        "open": float(item['open']), 
                                        "high": float(item['high']), 
                                        "low": float(item['low']), 
                                        "close": float(item['clos']), 
                                        "volume": float(item['tvol'] or 0)
                                    })
                                    
                            if items: curr_base_date = (datetime.strptime(items[-1].get('xymd'), "%Y%m%d") - timedelta(days=1)).strftime("%Y%m%d")
                            if curr_base_date < target_start_date: break

            # ---------------------------------------------------------
            # [공통] 정렬 및 중복 제거
            # ---------------------------------------------------------
            chart_data.sort(key=lambda x: x['time'])
            
            unique_data = []
            seen = set()
            for item in chart_data:
                if item['time'] not in seen:
                    unique_data.append(item)
                    seen.add(item['time'])
            return unique_data

        except Exception as e:
            logger.error(f"Chart Error: {e}")
            return chart_data

    # ---------------------------------------------------------
    # [차트 데이터 가공] - 분봉 합치기 (자정 넘김 대응)
    # ---------------------------------------------------------
    def _aggregate_minute_data(self, data, interval, start_h=9, start_m=0):
        """
        분봉 데이터 병합 로직
        - start_h: 장 시작 시 (국내 9, 해외 23)
        - start_m: 장 시작 분 (국내 0, 해외 30)
        - 자정(00시)을 넘어서 거래되는 해외 주식을 위해 날짜 보정 로직 포함
        """
        if not data: return []
        
        KST = timezone(timedelta(hours=9))
        data.sort(key=lambda x: x['time'])
        
        aggregated = []
        current_bucket = None
        
        for item in data:
            dt = datetime.fromtimestamp(item['time'], tz=KST)
            
            # 1. 날짜 보정 (해외주식 자정 넘김 처리)
            # 장 시작이 밤 8시 이후(20~)인데, 데이터가 아침 9시 이전이라면
            # 해당 데이터는 '어제 밤'에 시작된 장의 데이터로 간주 (하루 전으로 계산)
            calc_dt = dt
            if start_h >= 20 and dt.hour < 9:
                calc_dt = dt - timedelta(days=1)
            
            # 2. 해당 세션(장)의 정확한 시작 시각 계산
            # 예) 2025-01-01 23:30:00
            session_start_dt = calc_dt.replace(hour=start_h, minute=start_m, second=0, microsecond=0)
            
            # 3. 장 시작 시간으로부터 몇 분이 흘렀는지 계산
            diff_seconds = (dt - session_start_dt).total_seconds()
            diff_minutes = int(diff_seconds // 60)
            
            # 동시호가 등으로 장 시작 전 데이터가 들어온 경우 -> 0번 버킷 혹은 별도 처리
            if diff_minutes < 0:
                bucket_index = 0
            else:
                bucket_index = diff_minutes // interval
            
            # 4. 버킷의 기준 시간(Timestamp) 계산
            # 세션시작시간 + (버킷인덱스 * 간격)
            bucket_start_dt = session_start_dt + timedelta(minutes=(bucket_index * interval))
            bucket_ts = int(bucket_start_dt.timestamp())
            
            # Key: (Time 기준으로 유니크함)
            bucket_key = bucket_ts
            
            # 5. 버킷 생성 또는 데이터 갱신
            if (current_bucket is None) or (current_bucket['key'] != bucket_key):
                # 이전 버킷 저장
                if current_bucket: aggregated.append(current_bucket['data'])
                
                # 새 버킷 생성
                current_bucket = {
                    'key': bucket_key, 
                    'data': {
                        "time": bucket_ts, 
                        "open": item['open'], 
                        "high": item['high'], 
                        "low": item['low'], 
                        "close": item['close'], 
                        "volume": item['volume']
                    }
                }
            else:
                # 기존 버킷 업데이트 (고가, 저가, 종가, 거래량 누적)
                b = current_bucket['data']
                b['high'] = max(b['high'], item['high'])
                b['low'] = min(b['low'], item['low'])
                b['close'] = item['close']
                b['volume'] += item['volume']
                
        # 마지막 버킷 추가
        if current_bucket: aggregated.append(current_bucket['data'])
        return aggregated
# =========================================================
    # 2. [최종_진짜_완성] 해외 체결 (날짜 필터링 + 시간 필터링 + 정렬)
    # =========================================================
    async def get_recent_trades(self, market: str, code: str):
        trades_data = []
        vol_power = "0.00"

        try:
            token = await kis_auth.get_access_token()
            headers = {
                "content-type": "application/json",
                "authorization": f"Bearer {token}",
                "appkey": settings.KIS_APP_KEY,
                "appsecret": settings.KIS_SECRET_KEY
            }

            # [1] 국내 주식 (기존 유지)
            if market == "KR":
                headers["tr_id"] = "FHPST01060000" 
                path = "/uapi/domestic-stock/v1/quotations/inquire-time-itemconclusion" 
                curr_time = datetime.now().strftime("%H%M%S")

                params = { "FID_COND_MRKT_DIV_CODE": "J", "FID_INPUT_ISCD": code, "FID_INPUT_HOUR_1": curr_time }
                
                async with httpx.AsyncClient() as client:
                    res = await client.get(f"{settings.KIS_BASE_URL}{path}", headers=headers, params=params)
                    
                    if res.status_code == 200:
                        body = res.json()
                        items = body.get('output2')
                        if items is None: items = []
                        if isinstance(items, dict): items = [items]
                        
                        if isinstance(items, list):
                            if len(items) > 0:
                                vol_power = items[0].get('tday_rltv') or "0.00"

                            for item in items[:30]:
                                trades_data.append({
                                    "time": item.get('stck_cntg_hour') or "000000",
                                    "price": item.get('stck_prpr') or "0",
                                    "diff": item.get('prdy_vrss') or "0",
                                    "rate": item.get('prdy_ctrt') or "0.00",
                                    "volume": item.get('cnqn') or "0",        
                                    "total_vol": item.get('acml_vol') or "0", 
                                    "vol_power": item.get('tday_rltv') or vol_power 
                                })

            # [2] 해외 주식 (날짜 확인 로직 추가)
            else:
                headers["tr_id"] = "HHDFS76200300" 
                path = "/uapi/overseas-price/v1/quotations/inquire-ccnl"
                params = { "AUTH": "", "EXCD": "NAS", "SYMB": code }

                async with httpx.AsyncClient() as client:
                    res = await client.get(f"{settings.KIS_BASE_URL}{path}", headers=headers, params=params)
                    if res.status_code == 200:
                        items = res.json().get('output1')
                        if items is None: items = []
                        
                        rate = await self.get_exchange_rate()
                        if items and isinstance(items, list) and len(items) > 0: 
                            vol_power = items[0].get('vpow') or "0.00"

                        if isinstance(items, list) and len(items) > 0:
                            # [★핵심 1] 리스트 중 '가장 최신 날짜(xymd)' 찾기
                            # API는 보통 최신순으로 주므로 첫 번째 데이터의 날짜가 최신일 확률이 높음
                            # 하지만 안전하게 전체 스캔해서 max 날짜를 찾음
                            latest_date = max([item.get('xymd', '00000000') for item in items])
                            
                            temp_list = []
                            for item in items:
                                # [★핵심 2] 날짜 필터링: 최신 날짜가 아니면 버림 (어제 데이터 삭제)
                                if item.get('xymd') != latest_date:
                                    continue

                                price_usd = float(item.get('last') or 0)
                                price_krw = int(price_usd * rate)
                                
                                sign = item.get('sign')
                                diff_usd = float(item.get('diff') or 0)
                                if sign in ['4', '5']: diff_usd = -abs(diff_usd)
                                
                                kst_time_str = item.get('khms') or "000000"
                                time_int = int(kst_time_str)

                                # [★핵심 3] 시간 필터링: 정규장(23:30 ~ 06:00) 외 데이터 제외
                                # 06시 00분 ~ 23시 30분 사이의 데이터(장전/장후)는 버림
                                if 60000 < time_int < 233000:
                                    continue

                                # [★핵심 4] 정렬 키 생성 (자정 넘김 처리)
                                # 06:00(아침) > 23:30(밤)이 되도록 새벽 시간에 가중치 부여
                                if time_int <= 60000:
                                    sort_key = time_int + 240000
                                else:
                                    sort_key = time_int

                                temp_list.append({
                                    "time": kst_time_str,
                                    "price": str(price_krw),
                                    "diff": str(int(diff_usd * rate)),
                                    "rate": item.get('rate') or "0.00",
                                    "volume": item.get('evol') or "0",
                                    "total_vol": item.get('tvol') or "0",
                                    "vol_power": item.get('vpow') or vol_power,
                                    "_sort_key": sort_key
                                })
                            
                            # 내림차순 정렬 (최신순)
                            temp_list.sort(key=lambda x: x['_sort_key'], reverse=True)
                            
                            for t in temp_list[:30]:
                                del t['_sort_key']
                                trades_data.append(t)

        except Exception as e:
            logger.error(f"Trades Error: {e}")
        
        return {
            "trades": trades_data,
            "vol_power": vol_power
        }
kis_data = KisDataService()