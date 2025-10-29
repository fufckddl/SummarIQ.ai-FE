"""
Decision 모델 - 의사결정 테이블
"""
from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from models import Base


class Decision(Base):
    """의사결정 테이블"""
    __tablename__ = "decisions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    recording_id = Column(String(36), ForeignKey('recordings.id'), nullable=False)
    decision = Column(Text, nullable=False)
    decision_order = Column(Integer, default=0)
    
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    
    # 관계
    recording = relationship("Recording", back_populates="decisions")

