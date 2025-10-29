"""
팀 회의 댓글 모델
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from models import Base

class TeamMeetingComment(Base):
    __tablename__ = "team_meeting_comments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    team_meeting_id = Column(Integer, ForeignKey("team_meetings.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    parent_id = Column(Integer, ForeignKey("team_meeting_comments.id"), nullable=True)  # 대댓글용
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)

    # 관계
    team_meeting = relationship("TeamMeeting")
    user = relationship("User", foreign_keys=[user_id])
    parent = relationship("TeamMeetingComment", remote_side=[id], overlaps="replies")
    replies = relationship("TeamMeetingComment", overlaps="parent")

    def to_dict(self):
        return {
            "id": self.id,
            "team_meeting_id": self.team_meeting_id,
            "user_id": self.user_id,
            "parent_id": self.parent_id,
            "content": self.content,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "is_deleted": self.is_deleted,
        }


class TeamMeetingLike(Base):
    __tablename__ = "team_meeting_likes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    team_meeting_id = Column(Integer, ForeignKey("team_meetings.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    comment_id = Column(Integer, ForeignKey("team_meeting_comments.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.now, nullable=False)

    # 관계
    team_meeting = relationship("TeamMeeting")
    user = relationship("User", foreign_keys=[user_id])
    comment = relationship("TeamMeetingComment")

    def to_dict(self):
        return {
            "id": self.id,
            "team_meeting_id": self.team_meeting_id,
            "user_id": self.user_id,
            "comment_id": self.comment_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
