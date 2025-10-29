"""
회의 조회 기록 모델
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from models import Base

class MeetingViewLog(Base):
    __tablename__ = "meeting_view_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    meeting_id = Column(String(36), ForeignKey("recordings.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    viewed_at = Column(DateTime, default=datetime.now, nullable=False)

    # 관계
    meeting = relationship("Recording")
    user = relationship("User", foreign_keys=[user_id])

    def to_dict(self):
        return {
            "id": self.id,
            "meeting_id": self.meeting_id,
            "user_id": self.user_id,
            "viewed_at": self.viewed_at.isoformat() if self.viewed_at else None,
            "user_name": self.user.display_name if self.user else "알 수 없음",
            "user_initial": (self.user.display_name[0] if self.user and self.user.display_name else "?")[:1].upper(),
        }

