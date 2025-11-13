import logging
from fastapi import APIRouter, Depends, HTTPException, Cookie, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.user_services import user_service
from app.schemas.token import AccessTokenResponse
from app.core.security.token import create_access_token, create_refresh_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix='/auth', tags=['Token'])

@router.post('/token/refresh', response_model=AccessTokenResponse)
async def refresh_access_token(
    refresh_token: str = Cookie(None), 
    db: AsyncSession = Depends(get_db)
):
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token이 없습니다."
        )

    try:
        user = await user_service.get_user_by_refresh_token(db, refresh_token)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="유효하지 않거나 만료된 Refresh token입니다."
            )

        # 새 토큰 생성
        app_access_token = create_access_token(user_id=user.user_id)
        app_refresh_token = create_refresh_token()

        # 새 Refresh Token을 DB에 저장
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
        
        # 새 Refresh Token을 쿠키로 설정
        response.set_cookie(
            key="refresh_token",
            value=app_refresh_token,
            httponly=True,
            secure=True,
            samesite="lax",
            path="/auth/token/refresh"
        )
        return response

    except Exception as e:
        logger.error(f"⛔ 토큰 재발급 중 예외 발생: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="토큰 재발급 중 오류 발생"
        )