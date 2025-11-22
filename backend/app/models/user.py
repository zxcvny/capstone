from uuid import uuid4
from sqlalchemy import Column, String, DateTime, func, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base

class User(Base):
    """회원 전체(users)"""
    __tablename__ = "users"

    # 기본 정보
    user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(50), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now(), nullable=False)

    # 일반 로그인용 정보
    username = Column(String(100), unique=True, index=True, nullable=True)
    email = Column(String(255), unique=True, index=True, nullable=True)
    phone_number = Column(String(20), index=True, nullable=True)
    hashed_password = Column(String(255), nullable=True)

    social_accounts = relationship("SocialAccount", back_populates="user", cascade="all, delete-orphan")
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")