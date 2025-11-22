import httpx
import logging
from app.services.kis_auth import kis_auth
from app.core.config import settings

logger = logging.getLogger(__name__)

class KisDataService:
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
                        msg = res_json.get('msg1') or "알 수 없는 오류 (메시지 없음)"
                        logger.error(f"API Error ({tr_id}): {msg}")
                        return []
                else:
                    logger.error(f"HTTP Error {response.status_code}: {response.text}")
                    return []
        except Exception as e:
            logger.error(f"Fetch Ranking Error: {e}")
            return []

    def _map_ranking_item(self, item):
        """
        API별로 다른 필드명을 하나의 포맷으로 통일합니다.
        """
        # 1. 종목 코드
        code = item.get('mksc_shrn_iscd') or item.get('stck_shrn_iscd')
        
        # 2. 거래대금 (우선순위: 누적거래대금 > 거래대금 > 평균거래대금)
        amount = item.get('acml_tr_pbmn') or item.get('tr_pbmn') or item.get('avrg_tr_pbmn')
        
        # 3. 현재가, 등락률, 거래량
        price = item.get('stck_prpr')
        rate = item.get('prdy_ctrt')
        volume = item.get('acml_vol')

        # [거래대금 계산] API 응답에 없고(시가총액 순위 등), 가격과 거래량이 있다면 계산
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
        """
        [통합 순위 조회]
        rank_type: volume, amount, cap, rise, fall
        """
        tr_id = ""
        path = ""
        params = {}

        # 1. 거래량(volume) / 거래대금(amount) 상위
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

        # 2. 시가총액(cap) 상위
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

        # 3. 급상승(rise) / 급하락(fall) - [사용자 제공 명세 적용]
        elif rank_type in ["rise", "fall"]:
            tr_id = "FHPST01700000"
            path = "/uapi/domestic-stock/v1/ranking/fluctuation"
            
            # 0: 상승율순, 1: 하락율순
            sort_cls_code = "0" if rank_type == "rise" else "1"
            
            params = {
                "FID_RSFL_RATE2": "",            # 등락 비율2 (전체)
                "FID_COND_MRKT_DIV_CODE": "J",   # 시장구분 (J:KRX)
                "FID_COND_SCR_DIV_CODE": "20170",
                "FID_INPUT_ISCD": "0000",        # 전 종목
                "FID_RANK_SORT_CLS_CODE": sort_cls_code,
                "FID_INPUT_CNT_1": "0",          # 0: 전체 (혹은 누적일수)
                "FID_PRC_CLS_CODE": "1",         # [중요] 가격구분 (0:저가/고가대비, 1:종가대비) -> 통상적인 등락률인 '1' 사용
                "FID_INPUT_PRICE_1": "",         # 가격대 (전체)
                "FID_INPUT_PRICE_2": "",
                "FID_VOL_CNT": "",               # 거래량 (전체)
                "FID_TRGT_CLS_CODE": "0",        # 대상 구분 (0:전체)
                "FID_TRGT_EXLS_CLS_CODE": "0",   # 제외 구분 (0:전체)
                "FID_DIV_CLS_CODE": "0",         # 분류 구분 (0:전체)
                "FID_RSFL_RATE1": ""             # 등락 비율1 (전체)
            }
        
        else:
            return []

        # API 호출
        output = await self._fetch_ranking(tr_id, params, path)
        
        # 결과 데이터 정제
        results = []
        for item in output[:30]:
            mapped_item = self._map_ranking_item(item)
            if mapped_item['code']:
                results.append(mapped_item)
        
        return results

    async def get_current_price(self, code: str):
        """상세 시세 조회"""
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

kis_data = KisDataService()