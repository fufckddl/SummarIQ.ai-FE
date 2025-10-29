"""
Action 모델 - 액션 아이템 테이블
"""
from sqlalchemy import Column, String, Integer, Text, DateTime, Enum, Boolean, Date, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from models import Base


class Action(Base):
    """액션 아이템 테이블"""
    __tablename__ = "actions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    recording_id = Column(String(36), ForeignKey('recordings.id'), nullable=False)
    
    task = Column(Text, nullable=False)
    owner = Column(String(100))
    due_date = Column(Date)
    priority = Column(Enum('low', 'medium', 'high'), default='medium')
    completed = Column(Boolean, default=False)
    action_order = Column(Integer, default=0)
    
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)
    
    # 관계
    recording = relationship("Recording", back_populates="actions")

    def to_dict(self):
        """딕셔너리로 변환"""
        return {
            "task": self.task,
            "owner": self.owner,
            "due": self.due_date.isoformat() if self.due_date else None,
            "priority": self.priority,
            "completed": self.completed,
        }

