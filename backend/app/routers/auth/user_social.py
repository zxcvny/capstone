import logging
import httpx
from fastapi import APIRouter, Query, Depends
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession


from app.core.config import settings
from app.database import get_db
from app.models.social_account import AuthProvider
from app.schemas.token import AccessTokenResponse
from app.services.user_services import user_service
from app.core.security.token import create_access_token, create_refresh_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix='/auth', tags=['User-Social'])

@router.get('/kakao/login')
async def kakao_login():
    """카카오 로그인"""
    kakao_auth_url = (
        f"https://kauth.kakao.com/oauth/authorize"
        f"?response_type=code"
        f"&client_id={settings.KAKAO_CLIENT_ID}"
        f"&redirect_uri={settings.KAKAO_REDIRECT_URI}"
    )
    return RedirectResponse(url=kakao_auth_url)

@router.get('/kakao/callback', response_model=AccessTokenResponse)
async def kakao_callback(
    code: str = Query(...),
    db: AsyncSession = Depends(get_db)
):
    """
    카카오 로그인 콜백 처리
    1. 카카오 토큰 요청
    2. 카카오 사용자 정보 요청
    3. (user_service) DB 사용자 조회/생성
    4. (security) Access, Refresh 토큰 생성
    5. (user_service) Refresh 토큰 DB 저장
    6. 클라이언트에 두 토큰 모두 반환
    """
    token_url = 'https://kauth.kakao.com/oauth/token'
    token_data = {
        "grant_type": 'authorization_code',
        "client_id": settings.KAKAO_CLIENT_ID,
        "redirect_uri": settings.KAKAO_REDIRECT_URI,
        "client_secret": settings.KAKAO_CLIENT_SECRET,
        "code": code
    }

    async with httpx.AsyncClient() as client:
        try:
            token_response = await client.post(token_url, data=token_data)
            token_response.raise_for_status()
            kakao_access_token = token_response.json().get("access_token")

            if not kakao_access_token:
                logger.warning("⚠️ 카카오 Access Token 발급 실패 (토큰 값 없음)")
                return JSONResponse(status_code=400, content={"error": "Kakao Access Token 발급 실패"})

            user_info_url = "https://kapi.kakao.com/v2/user/me"
            headers = {"Authorization": f"Bearer {kakao_access_token}"}
            user_info_response = await client.get(user_info_url, headers=headers)
            user_info_response.raise_for_status()
            user_info_json = user_info_response.json()

            kakao_id = user_info_json.get("id")

            if not kakao_id:
                logger.warning("⚠️ 카카오 User ID 조회 실패 (ID 값 없음)")
                return JSONResponse(status_code=400, content={"error": "Kakao User ID 조회 실패"})

            kakao_account = user_info_json.get("kakao_account", {})
            kakao_email = kakao_account.get("email")
            kakao_name = kakao_account.get("name")
            if not kakao_name:
                kakao_name = f"사용자_{str(kakao_id)[:4]}"
            kakao_phone_number = kakao_account.get("phone_number")

            user = await user_service.get_or_create_user_social(
                db=db,
                provider=AuthProvider.KAKAO,
                provider_user_id=str(kakao_id),
                name=kakao_name,
                email=kakao_email,
                phone_number=kakao_phone_number
            )

            app_access_token = create_access_token(user_id=user.user_id)
            app_refresh_token = create_refresh_token()

            await user_service.save_refresh_token(
                db=db,
                user_id=user.user_id,
                token=app_refresh_token,
            )

            response_content = {
                "access_token": app_access_token,
                "token_type": "bearer"
            }

            response = JSONResponse(content=response_content)

            response.set_cookie(
                key="refresh_token",
                value=app_refresh_token,
                httponly=True,            # JS가 접근하지 못하도록
                secure=True,              # HTTPS에서만 전송
                samesite="lax",           # CSRF 방어. 'strict'도 가능
                path="/auth/token/refresh" # 오직 /auth/token/refresh 엔드포인트에만 이 쿠키를 전송
            )

            return response

        except httpx.HTTPStatusError as e:
            logger.error(f"⛔ 카카오 API 연동 오류 발생: {e}", exc_info=True)
            return JSONResponse(status_code=500, content={"error": "카카오 API 연동 오류", "details": str(e)})
        except Exception as e:
            logger.error(f"⛔ 카카오 콜백 처리 중 예외 발생: {e}", exc_info=True)
            return JSONResponse(status_code=500, content={"error": "내부 서버 오류", "details": str(e)})
        
@router.get('/google/login')
async def google_login():
    """구글 로그인"""
    google_auth_url = (
        f"https://accounts.google.com/o/oauth2/v2/auth"
        f"?client_id={settings.GOOGLE_CLIENT_ID}"
        f"&redirect_uri={settings.GOOGLE_REDIRECT_URI}"
        f"&response_type=code"
        f"&scope=openid%20email%20profile" # openid, email, profile 범위 요청
    )
    return RedirectResponse(url=google_auth_url)


@router.get('/google/callback', response_model=AccessTokenResponse)
async def google_callback(
    code: str = Query(...),
    db: AsyncSession = Depends(get_db)
):
    """
    구글 로그인 콜백 처리
    1. 구글 토큰 요청
    2. 구글 사용자 정보 요청
    3. (user_service) DB 사용자 조회/생성
    4. (security) Access, Refresh 토큰 생성
    5. (user_service) Refresh 토큰 DB 저장
    6. 클라이언트에 두 토큰 모두 반환
    """
    token_url = 'https://oauth2.googleapis.com/token'
    token_data = {
        "grant_type": 'authorization_code',
        "client_id": settings.GOOGLE_CLIENT_ID,
        "client_secret": settings.GOOGLE_CLIENT_SECRET,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "code": code
    }

    async with httpx.AsyncClient() as client:
        try:
            # 1. 구글에 토큰 요청
            token_response = await client.post(token_url, data=token_data)
            token_response.raise_for_status()
            google_access_token = token_response.json().get("access_token")

            if not google_access_token:
                logger.warning("⚠️ 구글 Access Token 발급 실패 (토큰 값 없음)")
                return JSONResponse(status_code=400, content={"error": "Google Access Token 발급 실패"})

            # 2. 구글 사용자 정보 요청
            user_info_url = "https://www.googleapis.com/oauth2/v3/userinfo"
            headers = {"Authorization": f"Bearer {google_access_token}"}
            user_info_response = await client.get(user_info_url, headers=headers)
            user_info_response.raise_for_status()
            user_info_json = user_info_response.json()

            google_id = user_info_json.get("sub") # 구글은 'sub' 필드를 고유 ID로 사용

            if not google_id:
                logger.warning("⚠️ 구글 User ID 조회 실패 (ID 값 없음)")
                return JSONResponse(status_code=400, content={"error": "Google User ID 조회 실패"})

            google_email = user_info_json.get("email")
            google_name = user_info_json.get("name")
            if not google_name:
                google_name = f"사용자_{str(google_id)[:4]}"
            # 구글은 전화번호를 기본 범위로 제공하지 않습니다.

            # 3. 사용자 조회 또는 생성
            user = await user_service.get_or_create_user_social(
                db=db,
                provider=AuthProvider.GOOGLE,
                provider_user_id=str(google_id),
                name=google_name,
                email=google_email,
                phone_number=None # 전화번호는 없음
            )

            # 4. 앱 토큰 생성
            app_access_token = create_access_token(user_id=user.user_id)
            app_refresh_token = create_refresh_token()

            # 5. Refresh 토큰 DB 저장
            await user_service.save_refresh_token(
                db=db,
                user_id=user.user_id,
                token=app_refresh_token,
            )

            # 6. 토큰 반환
            response_content = {
                "access_token": app_access_token,
                "token_type": "bearer"
            }
            response = JSONResponse(content=response_content)
            response.set_cookie(
                key="refresh_token",
                value=app_refresh_token,
                httponly=True,
                secure=True,
                samesite="lax",
                path="/auth/token/refresh"
            )
            return response

        except httpx.HTTPStatusError as e:
            logger.error(f"⛔ 구글 API 연동 오류 발생: {e}", exc_info=True)
            return JSONResponse(status_code=500, content={"error": "구글 API 연동 오류", "details": str(e)})
        except Exception as e:
            logger.error(f"⛔ 구글 콜백 처리 중 예외 발생: {e}", exc_info=True)
            return JSONResponse(status_code=500, content={"error": "내부 서버 오류", "details": str(e)})