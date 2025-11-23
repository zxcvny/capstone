import httpx
import logging
import time
from datetime import datetime, timedelta
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
    # [차트 조회] (이전 코드와 동일)
    # ---------------------------------------------------------
    async def get_stock_chart(self, market: str, code: str, period: str):
        chart_data = []
        try:
            token = await kis_auth.get_access_token()
            headers = {
                "content-type": "application/json",
                "authorization": f"Bearer {token}",
                "appkey": settings.KIS_APP_KEY,
                "appsecret": settings.KIS_SECRET_KEY
            }
            
            today = datetime.now().strftime("%Y%m%d")
            target_start_date = (datetime.now() - timedelta(days=365*2)).strftime("%Y%m%d")
            is_minute = "m" in period

            if market == "KR":
                if is_minute:
                    headers["tr_id"] = "FHKST03010230" 
                    path = "/uapi/domestic-stock/v1/quotations/inquire-time-dailychartprice"
                    curr_date = today
                    curr_time = "153000" 
                    for _ in range(100): 
                        params = {"FID_COND_MRKT_DIV_CODE": "J", "FID_INPUT_ISCD": code, "FID_INPUT_DATE_1": curr_date, "FID_INPUT_HOUR_1": curr_time, "FID_PW_DATA_INCU_YN": "Y", "FID_FAKE_TICK_INCU_YN": "N"}
                        async with httpx.AsyncClient() as client:
                            res = await client.get(f"{settings.KIS_BASE_URL}{path}", headers=headers, params=params)
                            if res.status_code != 200: break
                            items = res.json().get('output2', [])
                            if not items: break
                            for item in items:
                                d, t, c = item.get('stck_bsop_date'), item.get('stck_cntg_hour'), item.get('stck_prpr')
                                if d and t and c:
                                    chart_data.append({"time": f"{d[:4]}-{d[4:6]}-{d[6:8]} {t[:2]}:{t[2:4]}:{t[4:6]}", "open": float(item['stck_oprc']), "high": float(item['stck_hgpr']), "low": float(item['stck_lwpr']), "close": float(c), "volume": float(item['cntg_vol'] or 0)})
                            last = items[-1]
                            curr_date, curr_time = last.get('stck_bsop_date'), last.get('stck_cntg_hour')
                            if curr_date < (datetime.now() - timedelta(days=365)).strftime("%Y%m%d"): break
                    if period != '1m' and period != 'minute':
                        interval = int(period.replace('m', ''))
                        chart_data = self._aggregate_minute_data(chart_data, interval)
                else:
                    headers["tr_id"] = "FHKST03010100"
                    path = "/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice"
                    p_code = {"D": "D", "W": "W", "M": "M", "Y": "Y"}.get(period, "D")
                    curr_end_date = today
                    for _ in range(10): 
                        params = {"FID_COND_MRKT_DIV_CODE": "J", "FID_INPUT_ISCD": code, "FID_INPUT_DATE_1": target_start_date, "FID_INPUT_DATE_2": curr_end_date, "FID_PERIOD_DIV_CODE": p_code, "FID_ORG_ADJ_PRC": "1"}
                        async with httpx.AsyncClient() as client:
                            res = await client.get(f"{settings.KIS_BASE_URL}{path}", headers=headers, params=params)
                            if res.status_code != 200: break
                            items = res.json().get('output2', [])
                            if not items: break
                            for item in items:
                                d = item.get('stck_bsop_date')
                                if d: chart_data.append({"time": f"{d[:4]}-{d[4:6]}-{d[6:8]}", "open": float(item['stck_oprc']), "high": float(item['stck_hgpr']), "low": float(item['stck_lwpr']), "close": float(item['stck_clpr']), "volume": float(item['acml_vol'] or 0)})
                            if items: curr_end_date = (datetime.strptime(items[-1]['stck_bsop_date'], "%Y%m%d") - timedelta(days=1)).strftime("%Y%m%d")
                            if curr_end_date < target_start_date or len(items) < 100: break
            else:
                market_code = "NAS"
                if is_minute:
                    nmin = period.replace('m', '')
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
                                if d and t: chart_data.append({"time": f"{d[:4]}-{d[4:6]}-{d[6:8]} {t[:2]}:{t[2:4]}:{t[4:6]}", "open": float(item['open']), "high": float(item['high']), "low": float(item['low']), "close": float(item['last']), "volume": float(item['evol'] or 0)})
                            if body.get('output1', {}).get('next') == "1":
                                next_key = (items[-1].get('xymd') or "") + (items[-1].get('xhms') or "")
                            else: break
                else:
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
                                if d: chart_data.append({"time": f"{d[:4]}-{d[4:6]}-{d[6:8]}", "open": float(item['open']), "high": float(item['high']), "low": float(item['low']), "close": float(item['clos']), "volume": float(item['tvol'] or 0)})
                            if items: curr_base_date = (datetime.strptime(items[-1].get('xymd'), "%Y%m%d") - timedelta(days=1)).strftime("%Y%m%d")
                            if curr_base_date < target_start_date: break

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

    def _aggregate_minute_data(self, data, interval):
        if not data: return []
        data.sort(key=lambda x: x['time'])
        aggregated = []
        current_bucket = None
        for item in data:
            dt = datetime.strptime(item['time'], "%Y-%m-%d %H:%M:%S")
            minute_of_day = dt.hour * 60 + dt.minute
            bucket_index = minute_of_day // interval
            date_str = dt.strftime("%Y-%m-%d")
            bucket_key = (date_str, bucket_index)
            if (current_bucket is None) or (current_bucket['key'] != bucket_key):
                if current_bucket: aggregated.append(current_bucket['data'])
                start_h = (bucket_index * interval) // 60
                start_m = (bucket_index * interval) % 60
                start_time_str = f"{date_str} {start_h:02}:{start_m:02}:00"
                current_bucket = {'key': bucket_key, 'data': {"time": start_time_str, "open": item['open'], "high": item['high'], "low": item['low'], "close": item['close'], "volume": item['volume']}}
            else:
                b = current_bucket['data']
                b['high'] = max(b['high'], item['high'])
                b['low'] = min(b['low'], item['low'])
                b['close'] = item['close']
                b['volume'] += item['volume']
        if current_bucket: aggregated.append(current_bucket['data'])
        return aggregated
    
  # =========================================================
    # 2. [수정됨] 실시간 체결 내역 (시세) - 최근 체결 API 사용
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

            if market == "KR":
                # [STEP 1] 현재가 API에서 체결강도 확보
                headers["tr_id"] = "FHKST01010100"
                params = { "fid_cond_mrkt_div_code": "J", "fid_input_iscd": code }
                async with httpx.AsyncClient() as client:
                    res = await client.get(f"{settings.KIS_BASE_URL}/uapi/domestic-stock/v1/quotations/inquire-price", headers=headers, params=params)
                    if res.status_code == 200:
                        out = res.json().get('output', {})
                        vol_power = out.get('vol_tnrt', '0.00')

                # [STEP 2] 최근 체결 API (FHKST01010300) - 시간 무관하게 최신 30건 조회
                headers["tr_id"] = "FHKST01010300" 
                path = "/uapi/domestic-stock/v1/quotations/inquire-ccnl"
                
                async with httpx.AsyncClient() as client:
                    res = await client.get(f"{settings.KIS_BASE_URL}{path}", headers=headers, params=params)
                    if res.status_code == 200:
                        items = res.json().get('output', [])
                        for item in items:
                            trades_data.append({
                                "time": item['stck_cntg_hour'],
                                "price": item['stck_prpr'],
                                "diff": item['prdy_vrss'],
                                "rate": item['prdy_ctrt'],
                                "volume": item['cntg_vol'],
                                "total_vol": "-", # 이 API는 누적거래량 안 줌 (화면엔 '-' 표시)
                                "vol_power": vol_power # 개별 틱 체결강도는 없으므로 현재값 공통 사용
                            })

            else:
                # [해외] 최근 체결 API
                headers["tr_id"] = "HHDFS76200300" 
                path = "/uapi/overseas-price/v1/quotations/inquire-ccnl"
                params = { "AUTH": "", "EXCD": "NAS", "SYMB": code }

                async with httpx.AsyncClient() as client:
                    res = await client.get(f"{settings.KIS_BASE_URL}{path}", headers=headers, params=params)
                    if res.status_code == 200:
                        items = res.json().get('output1', [])
                        rate = await self.get_exchange_rate()
                        
                        if items: vol_power = items[0].get('vpow', '0.00')

                        for item in items:
                            price_krw = int(float(item['last']) * rate)
                            
                            # 부호 처리 (1,2:상승 / 4,5:하락)
                            sign = item.get('sign')
                            diff_usd = float(item.get('diff') or 0)
                            if sign in ['4', '5']: 
                                diff_usd = -abs(diff_usd)
                            
                            trades_data.append({
                                "time": item['khms'], 
                                "price": str(price_krw),
                                "diff": str(int(diff_usd * rate)),
                                "rate": item.get('rate', '0.00'),
                                "volume": item['evol'],
                                "total_vol": item.get('tvol', '0'),
                                "vol_power": item.get('vpow', vol_power)
                            })

        except Exception as e:
            logger.error(f"Trades Error: {e}")
        
        return {
            "trades": trades_data,
            "vol_power": vol_power
        }
kis_data = KisDataService()