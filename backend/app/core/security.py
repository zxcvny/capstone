from passlib.context import CryptContext
from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt
from app.core.config import settings
from pydantic import BaseModel
import uuid
import secrets

# bcrypt 알고리즘을 사용하도록 CryptContext 설정
# deprecated="auto": 안전하지 않은 알고리즘 사용 시 경고.
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str):
    """
    비밀번호를 bcrypt 알고리즘으로 해싱하는 함수.
    :param password: 사용자가 입력한 평문 비밀번호
    :return: bcrpyt로 해싱된 비밀번호 문자열
    """
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str):
    """
    입력된 평문 비밀번호와 해싱된 비밀번호를 비교하는 함수.
    :param plain_password: 사용자가 입력한 평문 비밀번호
    :param hashed_password: 데이터베이스에 저장된 해싱된 비밀번호
    :return: 두 비밀번호가 일치하면 True, 그렇지 않으면 False
    """
    return pwd_context.verify(plain_password, hashed_password)

# --- Pydantic 스키마 (토큰 응답용) ---
class TokenData(BaseModel):
    user_id: uuid.UUID | None = None

class AccessTokenResponse(BaseModel):
    """
    클라이언트에게 JSON 바디로 실제 반환될 Access Token 응답
    (Refresh Token은 쿠키로 전달됨)
    """
    access_token: str
    token_type: str = "bearer"

class TokenResponse(BaseModel):
    """
    클라이언트에게 최종 반환될 토큰 응답
    """
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

# --- JWT 토큰 생성 및 검증 ---
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