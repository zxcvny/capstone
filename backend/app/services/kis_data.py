import httpx
import logging
import time
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
            params.update({"GUBN": gubn_code, "NDAY": "0", "VOL_RANG": "1"})
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

kis_data = KisDataService()