"""
로컬 인증 (비밀번호) 모델
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from models import Base


class Credential(Base):
    """로컬 비밀번호 인증 테이블"""
    __tablename__ = "credentials"
    
    # 기본 정보
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    
    # 비밀번호
    password_hash = Column(String(255), nullable=False)
    
    # 타임스탬프
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)
    
    # 관계
    user = relationship("User", back_populates="credentials")

