from uuid import uuid4
from sqlalchemy import Column, String, DateTime, func, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base

class RefreshToken(Base):
    """
    리프레시 토큰 저장소
    """
    __tablename__ = "refresh_tokens"
    refresh_token_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    
    token = Column(String(512), unique=True, index=True, nullable=False)
    
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    is_revoked = Column(Boolean, default=False, nullable=False)

    user = relationship("User", back_populates="refresh_tokens")