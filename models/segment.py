"""
Segment 모델 - 녹음 세그먼트 테이블
"""
from sqlalchemy import Column, String, Integer, Text, DateTime, JSON, ForeignKey, Numeric
from sqlalchemy.orm import relationship
from datetime import datetime

from models import Base


class Segment(Base):
    """세그먼트 테이블"""
    __tablename__ = "segments"

    id = Column(String(50), primary_key=True)
    recording_id = Column(String(36), ForeignKey('recordings.id'), nullable=False)
    seq = Column(Integer, nullable=False)
    
    # 오디오 정보
    audio_url = Column(String(500))
    start_ms = Column(Integer, nullable=False)
    end_ms = Column(Integer, nullable=False)
    
    # STT 결과
    text = Column(Text, nullable=False)
    lang = Column(String(10), default='ko-KR')
    confidence = Column(Numeric(4, 3), default=0.95)
    
    # 화자 정보
    speakers = Column(JSON)
    
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    
    # 관계
    recording = relationship("Recording", back_populates="segments")

    def to_dict(self):
        """딕셔너리로 변환"""
        return {
            "id": self.id,
            "recordingId": self.recording_id,
            "seq": self.seq,
            "audioUrl": self.audio_url,
            "startMs": self.start_ms,
            "endMs": self.end_ms,
            "text": self.text,
            "lang": self.lang,
            "confidence": float(self.confidence) if self.confidence else 0.95,
            "speakers": self.speakers or [],
        }

