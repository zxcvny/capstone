import httpx
import logging
import time
from app.services.kis_auth import kis_auth
from app.core.config import settings

logger = logging.getLogger(__name__)

class KisDataService:
    def __init__(self):
        # 환율 캐싱을 위한 변수 (매번 호출하면 느려질 수 있으므로 값 저장)
        self.cached_rate = 1460.0 
        self.last_fetch_time = 0
        self.cache_duration = 3600  # 1시간 동안 캐시 유지 (원하시면 0으로 설정하여 매번 갱신 가능)

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
                # 에러 발생 시 기존 캐시된 값(또는 기본값 1450) 반환
        
        return self.cached_rate

    async def get_top_volume(self):
        """기존 메서드 호환성 유지"""
        data = await self.get_ranking_data("volume")
        return [item['code'] for item in data]

    async def _fetch_ranking(self, tr_id, params, path):
        """순위 조회 공통 메서드"""
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
                        return res_json.get('output', [])
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
        
        if not amount:
            amount = "0"

        return {
            "code": code,
            "price": price,
            "change_rate": rate,
            "volume": volume,
            "amount": amount
        }

    async def get_ranking_data(self, rank_type="volume"):
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

    async def get_current_price(self, code: str):
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
        """해외 주식 시세 조회 (자동 환율 계산 적용)"""
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
                        
                        price_usd = float(output.get('last') or 0) # 달러 가격
                        
                        # [자동 환율 적용]
                        # 여기서 자동으로 환율을 가져와 계산합니다.
                        exchange_rate = await self.get_exchange_rate()
                        price_krw = int(price_usd * exchange_rate)
                        
                        return {
                            "code": code,
                            "price": str(price_krw),  # 원화로 변환된 값 (소수점 제거)
                            "change_rate": output.get('rate'),
                            "volume": output.get('tvol'),
                            "amount": output.get('tamt')
                        }
        except Exception as e:
            logger.error(f"Overseas Price Error: {e}")
            return None
        return None

kis_data = KisDataService()