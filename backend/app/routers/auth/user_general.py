import logging
import random
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.user import UserCreate, UserPublic, CheckAvailabilityRequest, PhoneVerificationRequest
from app.schemas.token import AccessTokenResponse
from app.services.user_services import user_service
from app.core.security.token import create_access_token, create_refresh_token
from app.core.security.hashing import verify_password

logger = logging.getLogger(__name__)

router = APIRouter(prefix='/auth', tags=['User-General'])

# 임시 인증번호 저장소
verification_store = {}

@router.post("/send-verification-code")
async def send_verification_code(req: PhoneVerificationRequest):
    """
    전화번호 인증번호 발송 (모의)
    실제 SMS 발송 대신, 생성된 코드를 응답으로 반환하여 Alert로 띄울 수 있게 함
    """
    # 1. 6자리 랜덤 숫자 생성
    code = str(random.randint(100000, 999999))
    
    # 2. 저장 (나중에 검증용 API를 만들 경우 사용)
    verification_store[req.phone_number] = code
    
    logger.info(f"📱 [SMS 발송 시뮬레이션] 번호: {req.phone_number}, 인증코드: {code}")

    # 3. 클라이언트에 반환 (개발용: Alert에 띄우기 위함)
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "message": "인증번호가 발송되었습니다.",
            "code": code
        }
    )

@router.post("/check-availability")
async def check_availability(
    req: CheckAvailabilityRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    회원가입 정보 실시간 중복 확인 (username, email, phone_number)
    """
    try:
        is_exist = await user_service.check_existence(db, req.field, req.value)
    except ValueError:
        raise HTTPException(status_code=400, detail="잘못된 필드 요청입니다.")

    if is_exist:
        error_msg = {
            "username": "이미 사용 중인 아이디입니다.",
            "email": "이미 사용 중인 이메일입니다."
        }.get(req.field, "이미 존재하는 값입니다.")
        
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"message": error_msg, "available": False}
        )
    
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "회원가입 성공", "available": True}
    )

@router.post("/register", status_code=status.HTTP_201_CREATED, response_model=UserPublic)
async def register_user(
    user_in: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    일반 회원가입
    """
    if await user_service.check_existence(db, "username", user_in.username):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이미 사용 중인 유저이름입니다."
        )
    
    if await user_service.check_existence(db, "email", user_in.email):
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
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="탈퇴한 회원입니다.",
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