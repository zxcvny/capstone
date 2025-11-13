import uuid
import secrets
from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt

from app.core.config import settings
from app.schemas.token import TokenData

def create_access_token(user_id: uuid.UUID) -> str:
    """
    Access Token (JWT) 생성
    """
    expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    expire = datetime.now(timezone.utc) + expires_delta
    
    to_encode = {
        "sub": str(user_id),
        "exp": expire,
        "type": "access"
    }
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt

def create_refresh_token() -> str:
    """
    Refresh Token (단순 랜덤 문자열) 생성
    """
    return secrets.token_hex(32)

def verify_access_token(token: str) -> TokenData | None:
    """
    Access Token을 검증하고 페이로드(TokenData)를 반환
    """
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        
        user_id_str = payload.get("sub")
        if user_id_str is None:
            return None

        try:
            user_id_uuid = uuid.UUID(user_id_str)
        except ValueError:
            return None

        return TokenData(user_id=user_id_uuid)
    
    except JWTError:
        return None