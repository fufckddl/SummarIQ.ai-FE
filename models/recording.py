"""
Recording 모델 - 녹음 메인 테이블
"""
from sqlalchemy import Column, String, Integer, Text, DateTime, Enum, ForeignKey, JSON, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime

from models import Base
from models.tag import recording_tags


class Recording(Base):
    """녹음 메인 테이블"""
    __tablename__ = "recordings"

    id = Column(String(36), primary_key=True)  # UUID (기존)
    recording_id = Column(Integer, autoincrement=True, unique=True)  # auto_increment ID
    title = Column(String(255), nullable=False)
    status = Column(
        Enum('recording', 'processing', 'stt_started', 'ready', 'failed', 'cancelled'), 
        default='recording'
    )
    
    # 메타데이터
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)
    duration = Column(Integer, default=0)
    lang_auto = Column(String(10), default='ko-KR')
    
    # 파일 정보
    audio_url = Column(String(500))
    local_audio_path = Column(String(500))
    
    # 전사 및 요약
    transcript = Column(Text)
    summary = Column(Text)
    
    # 회의 정보 (Notion 템플릿 필드)
    participants = Column(JSON)  # 참석자 목록
    tags = Column(JSON)  # 레거시 필드 (하위 호환성 유지)
    meeting_status = Column(String(20), default='완료')  # 회의 상태
    
    # 1단계 추가 필드
    questions_answers = Column(JSON)  # Q&A 목록
    open_issues = Column(JSON)  # 미결 사항
    key_insights = Column(JSON)  # 핵심 인사이트
    
    # 검증 시스템
    verified_numbers = Column(JSON, nullable=True)  # 숫자 검증 정보
    
    # 사용자 정보
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    # 팀 정보
    team_id = Column(Integer, ForeignKey("teams.id", ondelete="SET NULL"), nullable=True)
    is_shared = Column(Boolean, default=False, nullable=False)  # 팀 내 공유 여부
    shared_at = Column(DateTime, nullable=True)  # 공유 시점
    
    # 즐겨찾기
    is_favorite = Column(Boolean, default=False, nullable=False)
    favorited_at = Column(DateTime, nullable=True)
    
    # 관계 (문자열로 정의하여 순환 import 방지)
    user = relationship("User", back_populates="recordings", lazy="select")
    team = relationship("Team", back_populates="recordings", lazy="select")
    segments = relationship("Segment", back_populates="recording", cascade="all, delete-orphan", lazy="select")
    decisions = relationship("Decision", back_populates="recording", cascade="all, delete-orphan", lazy="select")
    actions = relationship("Action", back_populates="recording", cascade="all, delete-orphan", lazy="select")
    recording_tags = relationship("Tag", secondary=recording_tags, back_populates="recordings")

    def to_dict(self, include_segments=True):
        """딕셔너리로 변환
        
        Args:
            include_segments: segments 포함 여부 (기본값: True, 목록 조회 시 False)
        """
        # 안전한 속성 접근
        recording_id = self.id if hasattr(self, 'id') else getattr(self, 'id', '')
        recording_id_auto = self.recording_id if hasattr(self, 'recording_id') else getattr(self, 'recording_id', '')
        title = self.title if hasattr(self, 'title') else getattr(self, 'title', '')
        status = self.status if hasattr(self, 'status') else getattr(self, 'status', '')
        created_at = self.created_at if hasattr(self, 'created_at') else getattr(self, 'created_at', None)
        duration = self.duration if hasattr(self, 'duration') else getattr(self, 'duration', 0)
        lang_auto = self.lang_auto if hasattr(self, 'lang_auto') else getattr(self, 'lang_auto', '')
        audio_url = self.audio_url if hasattr(self, 'audio_url') else getattr(self, 'audio_url', '')
        local_audio_path = self.local_audio_path if hasattr(self, 'local_audio_path') else getattr(self, 'local_audio_path', '')
        transcript = self.transcript if hasattr(self, 'transcript') else getattr(self, 'transcript', '')
        summary = self.summary if hasattr(self, 'summary') else getattr(self, 'summary', '')
        user_id = self.user_id if hasattr(self, 'user_id') else getattr(self, 'user_id', None)
        
        result = {
            "id": recording_id,
            "recording_id": recording_id_auto,  # auto_increment ID 추가
            "title": title,
            "status": status,
            "createdAt": created_at.isoformat() if created_at else None,
            "duration": duration,
            "langAuto": lang_auto,
            "audioUrl": audio_url,
            "localAudioPath": local_audio_path,
            "transcript": transcript,
            "summary": summary,
            "userId": user_id,
            "teamId": self.team_id if hasattr(self, 'team_id') else getattr(self, 'team_id', None),
            "isShared": self.is_shared if hasattr(self, 'is_shared') else getattr(self, 'is_shared', False),
            "sharedAt": self.shared_at.isoformat() if self.shared_at else None,
            "isFavorite": self.is_favorite if hasattr(self, 'is_favorite') else getattr(self, 'is_favorite', False),
            "favoritedAt": self.favorited_at.isoformat() if self.favorited_at else None,
            "participants": self.participants if self.participants else [],
            "tags": self._get_tags_from_recording_tags(),
            "meetingStatus": self.meeting_status if hasattr(self, 'meeting_status') else getattr(self, 'meeting_status', ''),
            "questionsAnswers": self.questions_answers if self.questions_answers else [],
            "openIssues": self.open_issues if self.open_issues else [],
            "keyInsights": self.key_insights if self.key_insights else [],
            "decisions": [dec.decision for dec in self.decisions] if self.decisions else [],
            "actions": [act.to_dict() for act in self.actions] if self.actions else [],
        }
        
        # 목록 조회 시 segments 제외 (성능 향상)
        if include_segments:
            result["segments"] = [seg.to_dict() for seg in self.segments] if self.segments else []
        
        return result
    
    def _get_tags_from_recording_tags(self):
        """recording_tags 테이블에서 JSON 태그 데이터를 가져옴"""
        try:
            from sqlalchemy import text
            from database.connection import SessionLocal
            
            # 안전한 ID 접근
            recording_id = self.id if hasattr(self, 'id') else getattr(self, 'id', '')
            if not recording_id:
                print(f"❌ recording ID가 없음: {type(self)}")
                return []
            
            # 새로운 세션 생성
            db = SessionLocal()
            
            try:
                # recording_tags 테이블에서 tags JSON 필드 조회
                result = db.execute(text("""
                    SELECT tags 
                    FROM recording_tags 
                    WHERE recording_id = :recording_id
                    LIMIT 1
                """), {"recording_id": recording_id})
                
                row = result.fetchone()
                if row and row[0]:
                    import json
                    return json.loads(row[0])
                else:
                    return []
            finally:
                db.close()
        except Exception as e:
            print(f"❌ 태그 조회 실패: {e}")
            import traceback
            traceback.print_exc()
            return []

