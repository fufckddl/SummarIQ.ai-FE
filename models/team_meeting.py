"""
팀 회의록 모델
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from models import Base

class TeamMeeting(Base):
    __tablename__ = "team_meetings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    meeting_id = Column(String, nullable=False)  # recordings 테이블의 recording_id (UUID)
    shared_by = Column(Integer, ForeignKey("users.id"), nullable=False)  # 공유한 사용자
    shared_at = Column(DateTime, default=datetime.now, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)  # 공유 상태

    team = relationship("Team", back_populates="team_meetings")
    sharer = relationship("User", foreign_keys=[shared_by])
    # comments = relationship("TeamMeetingComment", back_populates="team_meeting")
    # likes = relationship("TeamMeetingLike", back_populates="team_meeting")

    def to_dict(self):
        return {
            "id": self.id,
            "team_id": self.team_id,
            "meeting_id": self.meeting_id,
            "shared_by": self.shared_by,
            "shared_at": self.shared_at.isoformat() if self.shared_at else None,
            "is_active": self.is_active,
        }
