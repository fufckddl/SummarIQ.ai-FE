"""
사용자 모델
"""
from sqlalchemy import Column, String, Boolean, DateTime, Integer, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from models import Base


class User(Base):
    """사용자 테이블"""
    __tablename__ = "users"
    
    # 기본 정보
    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), unique=True, nullable=True)
    email_verified = Column(Boolean, default=False, nullable=False)
    display_name = Column(String(100), nullable=True)
    avatar_url = Column(String, nullable=True)
    
    # 메타데이터
    locale = Column(String(10), default="ko-KR", nullable=False)
    created_via = Column(String(20), default="local", nullable=False)
    
    # 푸시 알림
    push_token = Column(String(255), nullable=True)
    push_enabled = Column(Boolean, default=True, nullable=False)
    
    # FCM 알림
    fcm_token = Column(String(512), nullable=True)
    platform = Column(String(20), nullable=True)  # 'ios' or 'android'
    
    # 음성 품질 설정
    audio_quality_enabled = Column(Boolean, default=True, nullable=False)
    audio_quality_settings = Column(JSON, nullable=True)
    
    # 관리자 권한
    is_admin = Column(Boolean, default=False, nullable=False)
    
    # 타임스탬프
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)
    last_login_at = Column(DateTime, nullable=True)
    
    # 관계
    identities = relationship("Identity", back_populates="user", cascade="all, delete-orphan")
    credentials = relationship("Credential", back_populates="user", uselist=False, cascade="all, delete-orphan")
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")
    recordings = relationship("Recording", back_populates="user")
    notion_connection = relationship("UserNotion", back_populates="user", uselist=False, cascade="all, delete-orphan")
    subscription = relationship("Subscription", back_populates="user", uselist=False, cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")
    announcements = relationship("Announcement", back_populates="author")
    inquiries = relationship("Inquiry", foreign_keys="Inquiry.author_id", back_populates="author")
    
    def to_dict(self):
        """딕셔너리 변환"""
        return {
            "id": self.id,
            "email": self.email,
            "email_verified": self.email_verified,
            "display_name": self.display_name,
            "avatar_url": self.avatar_url,
            "locale": self.locale,
            "created_via": self.created_via,
            "push_enabled": self.push_enabled,
            "audio_quality_enabled": self.audio_quality_enabled,
            "audio_quality_settings": self.audio_quality_settings,
            "is_admin": self.is_admin,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_login_at": self.last_login_at.isoformat() if self.last_login_at else None,
        }

