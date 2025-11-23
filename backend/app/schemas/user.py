import uuid
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    name: str
    phone_number: str | None = None

class UserPublic(BaseModel):
    user_id: uuid.UUID
    username: str | None = None
    email: EmailStr
    name: str
    phone_number: str | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class UserUpdate(BaseModel):
    """
    일반 사용자 정보 수정 시 받을 데이터
    """
    username: str | None = Field(None)
    password: str | None = Field(None)

class MessageResponse(BaseModel):
    """
    간단한 성공/오류 메시지 반환용
    """
    message: str

class CheckAvailabilityRequest(BaseModel):
    """실시간 중복 확인 요청"""
    field: str  # 'username', 'email', 'phone_number'
    value: str

class PhoneVerificationRequest(BaseModel):
    "전화번호 인증 요청"
    phone_number: str