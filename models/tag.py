"""
태그 모델
"""
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Table
from sqlalchemy.orm import relationship
from datetime import datetime
from models import Base


# 다대다 관계를 위한 연결 테이블
recording_tags = Table(
    'recording_tags',
    Base.metadata,
    Column('recording_id', String(36), ForeignKey('recordings.id', ondelete='CASCADE'), primary_key=True),
    Column('tag_id', Integer, ForeignKey('tags.id', ondelete='CASCADE'), primary_key=True),
    Column('created_at', DateTime, default=datetime.now, nullable=False),
    Column('tags', String(1000), nullable=True),  # JSON 태그 데이터 저장
)


class Tag(Base):
    """태그 테이블"""
    __tablename__ = "tags"
    
    # 기본 정보
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), unique=True, nullable=False)  # 태그 이름 (예: "기획회의")
    color = Column(String(7), nullable=True)  # 색상 코드 (예: "#FF5733")
    
    # 사용 통계
    usage_count = Column(Integer, default=0, nullable=False)  # 사용 횟수
    
    # 메타데이터
    created_by = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    
    # 타임스탬프
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)
    
    # 관계
    creator = relationship("User", backref="created_tags")
    recordings = relationship("Recording", secondary=recording_tags, back_populates="recording_tags")
    
    def to_dict(self):
        """딕셔너리 변환"""
        return {
            "id": self.id,
            "name": self.name,
            "color": self.color,
            "usage_count": self.usage_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

