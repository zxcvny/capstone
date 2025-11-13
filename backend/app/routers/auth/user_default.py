import logging
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.user import UserCreate, UserPublic
from app.schemas.token import AccessTokenResponse
from app.services.user_services import user_service
from app.core.security.token import create_access_token, create_refresh_token
from app.core.security.hashing import verify_password

logger = logging.getLogger(__name__)

router = APIRouter(prefix='/auth', tags=['User-Default'])

@router.post("/register", status_code=status.HTTP_201_CREATED, response_model=UserPublic)
async def register_user(
    user_in: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    일반 회원가입
    """
    # 이메일 또는 유저이름 중복 확인
    existing_user = await user_service.get_user_by_username_or_email(db, user_in.username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이미 사용 중인 유저이름입니다."
        )
    
    existing_user = await user_service.get_user_by_username_or_email(db, user_in.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이미 사용 중인 이메일입니다."
        )
    
    try:
        user = await user_service.create_user_general(
            db=db,
            username=user_in.username,
            email=user_in.email,
            password=user_in.password,
            name=user_in.name,
            phone_number=user_in.phone_number
        )
        return user
    except Exception as e:
        logger.error(f"⛔ 회원가입 중 예외 발생: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="회원가입 중 오류가 발생했습니다."
        )

@router.post("/login", response_model=AccessTokenResponse)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """
    일반 로그인 (유저이름 또는 이메일 사용)
    """
    user = await user_service.get_user_by_username_or_email(db, form_data.username)
    
    if not user or not user.hashed_password or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="유저이름 또는 비밀번호가 잘못되었습니다.",
            headers={"WWW-Authenticate": "Bearer"},
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
        httponly=True,
        secure=True,
        samesite="lax",
        path="/auth/token/refresh"
    )

    return response