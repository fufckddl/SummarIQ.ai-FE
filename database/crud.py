"""
데이터베이스 CRUD 작업
"""
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional, Dict
from datetime import datetime, date as date_type
import uuid

from models.recording import Recording
from models.segment import Segment
from models.decision import Decision
from models.action import Action


# ==================== Recording CRUD ====================

def create_recording(
    db: Session,
    title: str = None,
    user_id: str = None,
    id: str = None,
    status: str = "recording"
) -> Recording:
    """녹음 생성"""
    recording_id = id or str(uuid.uuid4())
    
    recording = Recording(
        id=recording_id,
        title=title or f"녹음 {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        status=status,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        user_id=user_id
    )
    
    db.add(recording)
    db.commit()
    db.refresh(recording)
    
    return recording


def get_recording(db: Session, recording_id: str) -> Optional[Recording]:
    """녹음 조회"""
    return db.query(Recording).filter(Recording.id == recording_id).first()


def list_recordings(db: Session, user_id: int = None, limit: int = 100) -> List[Recording]:
    """
    녹음 목록 조회
    
    Args:
        db: 데이터베이스 세션
        user_id: 사용자 ID (None이면 모든 녹음, 지정하면 해당 사용자만)
        limit: 최대 개수
    """
    query = db.query(Recording)
    
    # user_id가 있으면 필터링
    if user_id is not None:
        query = query.filter(Recording.user_id == user_id)
    
    return query.order_by(Recording.created_at.desc()).limit(limit).all()


def update_recording(
    db: Session,
    recording_id: str,
    **kwargs
) -> Optional[Recording]:
    """녹음 업데이트"""
    recording = get_recording(db, recording_id)
    if not recording:
        return None
    
    for key, value in kwargs.items():
        if hasattr(recording, key):
            setattr(recording, key, value)
    
    recording.updated_at = datetime.now()
    
    db.commit()
    db.refresh(recording)
    
    return recording


def delete_recording(db: Session, recording_id: str) -> bool:
    """녹음 삭제"""
    recording = get_recording(db, recording_id)
    if not recording:
        return False
    
    db.delete(recording)
    db.commit()
    
    return True


# ==================== Segment CRUD ====================

def create_segment(
    db: Session,
    recording_id: str,
    seq: int,
    text: str,
    lang: str = "ko-KR",
    confidence: float = 0.95,
    start_ms: int = 0,
    end_ms: int = 0,
    audio_url: str = None,
    speakers: list = None,
    speaker: int = None
) -> Segment:
    """세그먼트 생성"""
    segment_id = f"seg_{recording_id}_{seq}"
    
    # speakers 처리: 단일 speaker 또는 speakers 리스트
    if speaker is not None and speakers is None:
        speakers = [{"speaker": speaker}]
    
    segment = Segment(
        id=segment_id,
        recording_id=recording_id,
        seq=seq,
        text=text,
        lang=lang,
        confidence=confidence,
        start_ms=start_ms,
        end_ms=end_ms,
        audio_url=audio_url,
        speakers=speakers or [],
        created_at=datetime.now()
    )
    
    db.add(segment)
    db.commit()
    db.refresh(segment)
    
    return segment


def get_segments(db: Session, recording_id: str) -> List[Segment]:
    """녹음의 모든 세그먼트 조회"""
    return db.query(Segment).filter(Segment.recording_id == recording_id).order_by(Segment.seq).all()


# ==================== Decision CRUD ====================

def create_decisions(
    db: Session,
    recording_id: str,
    decisions: List[str]
) -> List[Decision]:
    """의사결정 생성 (여러 개)"""
    decision_objects = []
    
    for order, decision_text in enumerate(decisions):
        decision = Decision(
            recording_id=recording_id,
            decision=decision_text,
            decision_order=order,
            created_at=datetime.now()
        )
        db.add(decision)
        decision_objects.append(decision)
    
    db.commit()
    
    return decision_objects


def get_decisions(db: Session, recording_id: str) -> List[Decision]:
    """녹음의 모든 의사결정 조회"""
    return db.query(Decision).filter(Decision.recording_id == recording_id).order_by(Decision.decision_order).all()


# ==================== Action CRUD ====================

def create_actions(
    db: Session,
    recording_id: str,
    actions: List[Dict]
) -> List[Action]:
    """액션 아이템 생성 (여러 개)"""
    action_objects = []
    
    for order, action_data in enumerate(actions):
        # due 날짜 파싱
        due_date = None
        if action_data.get("due"):
            try:
                from datetime import date
                due_str = action_data["due"]
                
                # YYYY-MM-DD 형식 처리
                if isinstance(due_str, str):
                    if len(due_str) == 10 and due_str.count('-') == 2:
                        # 이미 YYYY-MM-DD 형식
                        year, month, day = due_str.split('-')
                        due_date = date(int(year), int(month), int(day))
                    else:
                        # ISO 형식 시도
                        due_date = datetime.fromisoformat(due_str).date()
                
                print(f"  📅 액션 날짜 파싱: '{due_str}' → {due_date}")
            except Exception as e:
                print(f"  ⚠️ 액션 날짜 파싱 실패: '{action_data.get('due')}' - {e}")
        
        action = Action(
            recording_id=recording_id,
            task=action_data["task"],
            owner=action_data.get("owner"),
            due_date=due_date,
            priority=action_data.get("priority", "medium"),
            completed=False,
            action_order=order,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        db.add(action)
        action_objects.append(action)
    
    db.commit()
    
    return action_objects


def get_actions(db: Session, recording_id: str) -> List[Action]:
    """녹음의 모든 액션 아이템 조회"""
    return db.query(Action).filter(Action.recording_id == recording_id).order_by(Action.action_order).all()


# ==================== 통합 조회 ====================

def get_recording_with_details(db: Session, recording_id: str) -> Optional[Dict]:
    """녹음과 관련된 모든 데이터 조회"""
    recording = get_recording(db, recording_id)
    if not recording:
        return None
    
    # 관계된 데이터 자동 로드 (SQLAlchemy relationship)
    return recording.to_dict()

