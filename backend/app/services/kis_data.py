import httpx
from app.services.kis_auth import kis_auth
from app.core.config import settings

class KISData:
    async def get_top_volume(self):
        """거래량 상위 종목 조회"""
        token = await kis_auth.get_access_token()

        url = f"{settings.KIS_BASE_URL}/uapi/domestic-stock/v1/quotations/volume-rank"

        headers = {
            "content-type": "application/json; charset=utf-8",
            "authorization": f"Bearer {token}", # OAuth 2.0의 Client Credentials Grant 절차를 준용
            "appkey": settings.KIS_APP_KEY,
            "appsecret": settings.KIS_SECRET_KEY,
            "tr_id": "FHPST01710000",
            "custtype": "P"
        }
        params = {
            "FID_COND_MRKT_DIV_CODE": "J",          #조건 시장 분류 코드: 한국거래소, 코스피
            "FID_COND_SCR_DIV_CODE": "20171",       #조건 화면 분류 코드: 거래량 순위
            "FID_INPUT_ISCD": "0000",               #입력 종목코드: 전체
            "FID_DIV_CLS_CODE": "0",                #분류 구분 코드: 전체
            "FID_BLNG_CLS_CODE": "0",               #소속 구분 코드: 평균거래량
            "FID_TRGT_CLS_CODE": "111111111",       #대상 구분 코드: 전체 허용
            "FID_TRGT_EXLS_CLS_CODE": "0000000000", #대상 제외 구분 코드: 제외 없음
            "FID_INPUT_PRICE_1": "",                #입력 가격1: 전체
            "FID_INPUT_PRICE_2": "",                #입력 가격2: 전체
            "FID_VOL_CNT": "",                      #거래량 수: 전체
            "FID_INPUT_DATE_1": "",                 #입력 날짜1
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            return [item["mksc_shrn_iscd"] for item in data.get("output", [])] # 종목 코드만 출력 (임시)
        
kis_data = KISData()