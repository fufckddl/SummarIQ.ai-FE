"""
알림 모델
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from models import Base
import enum


class NotificationType(str, enum.Enum):
    """알림 타입"""
    TEAM_INVITE = "team_invite"
    MEETING_REMINDER = "meeting_reminder"
    SYSTEM = "system"
    MEETING_SHARED = "meeting_shared"
    TEAM_UPDATE = "team_update"


class NotificationStatus(str, enum.Enum):
    """알림 상태"""
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    READ = "read"
    UNREAD = "unread"


class Notification(Base):
    """알림 모델"""
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    
    # 알림을 받는 사용자
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # 알림 타입
    type = Column(Enum(NotificationType), nullable=False, index=True)
    
    # 알림 제목
    title = Column(String(255), nullable=False)
    
    # 알림 메시지
    message = Column(Text, nullable=False)
    
    # 알림 상태
    status = Column(Enum(NotificationStatus), default=NotificationStatus.UNREAD, nullable=False)
    
    # 알림 데이터 (JSON 형태로 저장)
    data = Column(Text)  # JSON 문자열로 저장
    
    # 읽음 여부
    is_read = Column(Boolean, default=False, nullable=False)
    
    # 만료 시간 (선택적)
    expires_at = Column(DateTime, nullable=True)
    
    # 생성 시간
    created_at = Column(DateTime, default=func.now(), nullable=False)
    
    # 업데이트 시간
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    
    # 관계 설정
    user = relationship("User", back_populates="notifications")
    
    def to_dict(self):
        """딕셔너리로 변환"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "type": self.type.value,
            "title": self.title,
            "message": self.message,
            "status": self.status.value,
            "data": self.data,
            "is_read": self.is_read,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
