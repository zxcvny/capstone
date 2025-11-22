from sqlalchemy import Column, String, ForeignKey, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from uuid import uuid4
from app.database import Base

class UserStock(Base):
    """사용자 관심 종목"""
    __tablename__ = "user_stocks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    stock_code = Column(String(20), nullable=False)
    stock_name = Column(String(100), nullable=True) # 편의상 이름도 저장
    market_type = Column(String(20), default="DOMESTIC") # DOMESTIC or OVERSEAS
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="interest_stocks")