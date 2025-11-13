import enum
from uuid import uuid4
from sqlalchemy import Column, String, DateTime, func, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base

class AuthProvider(str, enum.Enum):
    KAKAO = "kakao"
    GOOGLE = "google"

class SocialAccount(Base):
    """
    연동된 소셜 계정 정보
    """
    __tablename__ = "social_accounts"

    social_account_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)

    provider = Column(SAEnum(AuthProvider, name="auth_provider_enum"), nullable=False)
    provider_user_id = Column(String(255), nullable=False, index=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="social_accounts")