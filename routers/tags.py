"""
태그 관리 API 라우터
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import List, Dict, Optional
from datetime import datetime

from database.connection import get_db
from utils.auth_dependency import get_current_user
from models.tag import Tag
from models.recording import Recording
from models.tag import recording_tags

router = APIRouter(prefix="/api/tags", tags=["tags"])

# ==================== Pydantic 모델 ====================

class TagCreate(BaseModel):
    name: str
    color: Optional[str] = None

class TagsAddToRecording(BaseModel):
    recording_id: str
    tag_names: List[str]

# ==================== API 엔드포인트 ====================

@router.get("/")
async def list_tags(
    db: Session = Depends(get_db),
    search: Optional[str] = None
):
    """
    모든 태그 목록 조회 (사용 빈도순)
    """
    query = db.query(Tag)
    
    if search:
        query = query.filter(Tag.name.contains(search))
    
    tags = query.order_by(Tag.usage_count.desc()).limit(50).all()
    
    return {"tags": [tag.to_dict() for tag in tags]}

@router.post("/")
async def create_tag(
    tag_data: TagCreate,
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    새 태그 생성
    """
    user_id = current_user["id"]
    
    # 중복 확인
    existing = db.query(Tag).filter(Tag.name == tag_data.name).first()
    if existing:
        return {"tag": existing.to_dict(), "created": False}
    
    # 태그 생성
    tag = Tag(
        name=tag_data.name,
        color=tag_data.color,
        created_by=user_id
    )
    db.add(tag)
    db.commit()
    db.refresh(tag)
    
    return {"tag": tag.to_dict(), "created": True}

@router.post("/recordings/{recording_id}")
async def add_tags_to_recording(
    recording_id: str,
    tag_names: List[str],
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    녹음에 태그 추가
    """
    user_id = current_user["id"]
    
    # 녹음 존재 및 권한 확인
    recording = db.query(Recording).filter(Recording.id == recording_id).first()
    if not recording:
        raise HTTPException(status_code=404, detail="Recording not found")
    
    if recording.user_id != user_id:
        raise HTTPException(status_code=403, detail="You can only tag your own recordings")
    
    # 태그 처리
    added_tags = []
    
    for tag_name in tag_names:
        # 빈 태그 건너뛰기
        cleaned_name = tag_name.strip().replace('#', '')
        if not cleaned_name:
            continue
        
        # 태그 찾기 또는 생성
        tag = db.query(Tag).filter(Tag.name == cleaned_name).first()
        
        if not tag:
            tag = Tag(name=cleaned_name, created_by=user_id)
            db.add(tag)
            db.flush()
        
        # 이미 추가된 태그인지 확인
        exists = db.execute(
            recording_tags.select().where(
                recording_tags.c.recording_id == recording_id,
                recording_tags.c.tag_id == tag.id
            )
        ).first()
        
        if not exists:
            # 태그 추가
            db.execute(
                recording_tags.insert().values(
                    recording_id=recording_id,
                    tag_id=tag.id
                )
            )
            tag.usage_count += 1
            added_tags.append(tag.to_dict())
    
    db.commit()
    
    return {
        "message": f"{len(added_tags)}개 태그가 추가되었습니다",
        "tags": added_tags
    }

@router.delete("/recordings/{recording_id}/tags/{tag_id}")
async def remove_tag_from_recording(
    recording_id: str,
    tag_id: int,
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    녹음에서 태그 제거
    """
    user_id = current_user["id"]
    
    # 녹음 존재 및 권한 확인
    recording = db.query(Recording).filter(Recording.id == recording_id).first()
    if not recording:
        raise HTTPException(status_code=404, detail="Recording not found")
    
    if recording.user_id != user_id:
        raise HTTPException(status_code=403, detail="You can only modify your own recordings")
    
    # 태그 제거
    result = db.execute(
        recording_tags.delete().where(
            recording_tags.c.recording_id == recording_id,
            recording_tags.c.tag_id == tag_id
        )
    )
    
    if result.rowcount > 0:
        # 사용 횟수 감소
        tag = db.query(Tag).filter(Tag.id == tag_id).first()
        if tag and tag.usage_count > 0:
            tag.usage_count -= 1
        
        db.commit()
        return {"message": "Tag removed successfully"}
    else:
        raise HTTPException(status_code=404, detail="Tag not found on this recording")

@router.post("/recordings/{recording_id}/favorite")
async def toggle_favorite(
    recording_id: str,
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    즐겨찾기 토글
    """
    user_id = current_user["id"]
    
    # 녹음 존재 및 권한 확인
    recording = db.query(Recording).filter(Recording.id == recording_id).first()
    if not recording:
        raise HTTPException(status_code=404, detail="Recording not found")
    
    if recording.user_id != user_id:
        raise HTTPException(status_code=403, detail="You can only favorite your own recordings")
    
    # 즐겨찾기 토글
    recording.is_favorite = not recording.is_favorite
    recording.favorited_at = datetime.now() if recording.is_favorite else None
    
    db.commit()
    db.refresh(recording)
    
    return {
        "message": "즐겨찾기가 " + ("추가" if recording.is_favorite else "제거") + "되었습니다",
        "is_favorite": recording.is_favorite
    }

@router.get("/suggest/{recording_id}")
async def get_suggested_tags(
    recording_id: str,
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    AI가 녹음 내용 기반으로 태그 추천 (GET 방식)
    """
    user_id = current_user["id"]
    
    # 녹음 존재 및 권한 확인
    recording = db.query(Recording).filter(Recording.id == recording_id).first()
    if not recording:
        raise HTTPException(status_code=404, detail="Recording not found")
    
    if recording.user_id != user_id:
        raise HTTPException(status_code=403, detail="You can only access your own recordings")
    
    # AI 태그 추천
    from services.summarizer import MeetingSummarizer
    summarizer = MeetingSummarizer()
    
    suggested_tags = summarizer.suggest_tags(
        transcript=recording.transcript or "",
        summary=recording.summary
    )
    
    return {
        "suggested_tags": suggested_tags
    }

@router.post("/recordings/{recording_id}/suggest")
async def suggest_tags_for_recording(
    recording_id: str,
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    AI가 녹음 내용 기반으로 태그 추천 (POST 방식)
    """
    user_id = current_user["id"]
    
    # 녹음 존재 및 권한 확인
    recording = db.query(Recording).filter(Recording.id == recording_id).first()
    if not recording:
        raise HTTPException(status_code=404, detail="Recording not found")
    
    if recording.user_id != user_id:
        raise HTTPException(status_code=403, detail="You can only access your own recordings")
    
    # AI 태그 추천
    from services.summarizer import MeetingSummarizer
    summarizer = MeetingSummarizer()
    
    suggested_tags = summarizer.suggest_tags(
        transcript=recording.transcript or "",
        summary=recording.summary
    )
    
    return {
        "suggested_tags": suggested_tags
    }

