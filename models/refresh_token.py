"""
리프레시 토큰 모델
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from models import Base


class RefreshToken(Base):
    """리프레시 토큰 테이블"""
    __tablename__ = "refresh_tokens"
    
    # 기본 정보
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # 토큰 정보
    token_hash = Column(String(255), unique=True, nullable=False)
    family_id = Column(String(36), nullable=False)
    
    # 메타데이터
    device_info = Column(String(255), nullable=True)
    ip_address = Column(String(45), nullable=True)
    
    # 만료 정보
    expires_at = Column(DateTime, nullable=False)
    revoked = Column(Boolean, default=False, nullable=False)
    
    # 타임스탬프
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    
    # 관계
    user = relationship("User", back_populates="refresh_tokens")

