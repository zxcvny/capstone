import uuid
from pydantic import BaseModel

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