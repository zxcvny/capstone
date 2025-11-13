from sqlalchemy import Column, String, DateTime
from sqlalchemy.sql import func

from app.database import Base

class KISToken(Base):
    __tablename__ = "kis_tokens"

    token_name = Column(String, primary_key=True, index=True)
    token_value = Column(String, nullable=False)

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)