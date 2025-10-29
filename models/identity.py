"""
외부 인증 연동 모델
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from models import Base


class Identity(Base):
    """외부 인증 연동 테이블"""
    __tablename__ = "identities"
    
    # 기본 정보
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # OAuth 프로바이더 정보
    provider = Column(String(20), nullable=False)  # kakao|google|naver|apple
    subject = Column(String(255), nullable=False)  # 프로바이더 사용자 ID
    
    # 프로필 정보
    email_verified = Column(Boolean, nullable=True)
    profile_name = Column(String(100), nullable=True)
    profile_picture = Column(String, nullable=True)
    
    # 메타데이터
    raw_profile = Column(JSON, nullable=True)
    
    # 타임스탬프
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)
    
    # 관계
    user = relationship("User", back_populates="identities")
    
    def to_dict(self):
        """딕셔너리 변환"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "provider": self.provider,
            "subject": self.subject,
            "email_verified": self.email_verified,
            "profile_name": self.profile_name,
            "profile_picture": self.profile_picture,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

