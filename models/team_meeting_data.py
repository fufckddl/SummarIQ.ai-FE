from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Text, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from models import Base

class TeamAction(Base):
    """팀 회의 액션 아이템"""
    __tablename__ = "team_actions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    team_meeting_id = Column(Integer, ForeignKey("team_meetings.id"), nullable=False)
    content = Column(Text, nullable=False)
    completed = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)
    
    team_meeting = relationship("TeamMeeting")
    
    def to_dict(self):
        return {
            "id": self.id,
            "team_meeting_id": self.team_meeting_id,
            "content": self.content,
            "completed": self.completed,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

class TeamDecision(Base):
    """팀 회의 결정사항"""
    __tablename__ = "team_decisions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    team_meeting_id = Column(Integer, ForeignKey("team_meetings.id"), nullable=False)
    content = Column(Text, nullable=False)
    completed = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)
    
    team_meeting = relationship("TeamMeeting")
    
    def to_dict(self):
        return {
            "id": self.id,
            "team_meeting_id": self.team_meeting_id,
            "content": self.content,
            "completed": self.completed,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

class TeamTag(Base):
    """팀 회의 태그"""
    __tablename__ = "team_tags"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    team_meeting_id = Column(Integer, ForeignKey("team_meetings.id"), nullable=False)
    name = Column(String(100), nullable=False)
    color = Column(String(20), nullable=True)
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    
    team_meeting = relationship("TeamMeeting")
    
    def to_dict(self):
        return {
            "id": self.id,
            "team_meeting_id": self.team_meeting_id,
            "name": self.name,
            "color": self.color,
            "created_at": self.created_at.isoformat(),
        }



