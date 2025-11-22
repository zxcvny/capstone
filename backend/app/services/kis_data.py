import httpx
import logging
from app.services.kis_auth import kis_auth
from app.core.config import settings

logger = logging.getLogger(__name__)

class KisDataService:
    async def get_top_volume(self):
        """
        [거래량 상위 종목 가져오기 - 실제 API 호출]
        KIS API (FHPST01710000)를 사용하여 거래량 상위 30개 종목 코드를 반환합니다.
        """
        try:
            token = await kis_auth.get_access_token()
            headers = {
                "content-type": "application/json",
                "authorization": f"Bearer {token}",
                "appkey": settings.KIS_APP_KEY,
                "appsecret": settings.KIS_SECRET_KEY,
                "tr_id": "FHPST01710000", # 거래량 순위 조회 TR ID
                "custtype": "P"
            }
            
            # 거래량 순위 조회 파라미터 (API 문서 표준)
            params = {
                "FID_COND_MRKT_DIV_CODE": "J",      # J: 주식
                "FID_COND_SCR_DIV_CODE": "20171",   # 20171: 화면번호
                "FID_INPUT_ISCD": "0000",           # 0000: 전체 종목
                "FID_DIV_CLS_CODE": "0",            # 0: 전체
                "FID_BLNG_CLS_CODE": "0",           # 0: 평균
                "FID_TRGT_CLS_CODE": "11111111",    # 1: 대상 포함 (일반주식 등)
                "FID_TRGT_EXLS_CLS_CODE": "000000", # 0: 제외 없음
                "FID_INPUT_PRICE_1": "",            # 가격대 (~From)
                "FID_INPUT_PRICE_2": "",            # 가격대 (~To)
                "FID_VOL_CNT": "",                  # 거래량 (~From)
                "FID_INPUT_DATE_1": ""              # 날짜 (비우면 당일)
            }

            async with httpx.AsyncClient() as client:
                url = f"{settings.KIS_BASE_URL}/uapi/domestic-stock/v1/quotations/volume-rank"
                response = await client.get(url, headers=headers, params=params)
                
                if response.status_code == 200:
                    res_json = response.json()
                    
                    if res_json.get('rt_cd') == '0':
                        output = res_json.get('output', [])
                        # API 결과에서 종목코드(mksc_shrn_iscd)만 추출해서 상위 30개 자르기
                        top_30 = [item['mksc_shrn_iscd'] for item in output[:30]]
                        
                        logger.info(f"✅ 거래량 상위 30개 종목 조회 성공 ({len(top_30)}개)")
                        return top_30
                    else:
                        logger.error(f"거래량 상위 조회 실패: {res_json.get('msg1')}")
                        # 실패 시 안전하게 기존 대형주 리스트 반환 (Fail-over)
                        return ["005930", "000660", "035420", "035720", "005380"]
                else:
                    logger.error(f"HTTP Error {response.status_code}: {response.text}")
                    return []

        except Exception as e:
            logger.error(f"get_top_volume 에러 발생: {e}")
            return []

    async def get_current_price(self, code: str):
        """
        [REST API] 특정 종목의 '현재가(또는 종가)' 조회
        """
        try:
            token = await kis_auth.get_access_token()
            headers = {
                "content-type": "application/json",
                "authorization": f"Bearer {token}",
                "appkey": settings.KIS_APP_KEY,
                "appsecret": settings.KIS_SECRET_KEY, # config.py 변수명 일치
                "tr_id": "FHKST01010100" 
            }
            
            params = {
                "fid_cond_mrkt_div_code": "J",
                "fid_input_iscd": code
            }

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
                        }
                    else:
                        logger.error(f"KIS API 조회 실패 ({code}): {res_json.get('msg1')}")
                        return None
                else:
                    logger.error(f"HTTP Error {response.status_code}: {response.text}")
                    return None

        except Exception as e:
            logger.error(f"get_current_price 에러 발생: {e}")
            return None

kis_data = KisDataService()