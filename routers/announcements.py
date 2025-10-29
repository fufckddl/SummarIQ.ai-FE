from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from database.connection import get_db
from models import Announcement, User
from utils.auth_dependency import get_current_user

router = APIRouter(prefix="/api/announcements", tags=["announcements"])


# Pydantic 모델
class AnnouncementCreate(BaseModel):
    title: str
    content: str


class AnnouncementUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    is_active: Optional[bool] = None


class AnnouncementResponse(BaseModel):
    id: int
    title: str
    content: str
    view_count: int
    author_id: int
    author_name: Optional[str]
    is_active: bool
    created_at: Optional[str]
    updated_at: Optional[str]

    class Config:
        from_attributes = True


# 공지사항 목록 조회 (모든 사용자)
@router.get("/", response_model=List[AnnouncementResponse])
async def get_announcements(
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """공지사항 목록 조회"""
    announcements = db.query(Announcement).options(
        joinedload(Announcement.author)
    ).filter(
        Announcement.is_active == True
    ).order_by(
        Announcement.created_at.desc()
    ).offset(skip).limit(limit).all()
    
    return [announcement.to_dict() for announcement in announcements]


# 공지사항 상세 조회 (조회수 증가)
@router.get("/{announcement_id}", response_model=AnnouncementResponse)
async def get_announcement(
    announcement_id: int,
    db: Session = Depends(get_db)
):
    """공지사항 상세 조회 (조회수 증가)"""
    announcement = db.query(Announcement).options(
        joinedload(Announcement.author)
    ).filter(
        Announcement.id == announcement_id,
        Announcement.is_active == True
    ).first()
    
    if not announcement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="공지사항을 찾을 수 없습니다."
        )
    
    return announcement.to_dict()


# 공지사항 작성 (관리자만)
@router.post("/", response_model=AnnouncementResponse)
async def create_announcement(
    announcement_data: AnnouncementCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """공지사항 작성 (관리자만)"""
    # 관리자 권한 체크
    if not current_user.get("is_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="관리자만 공지사항을 작성할 수 있습니다."
        )
    
    announcement = Announcement(
        title=announcement_data.title,
        content=announcement_data.content,
        author_id=current_user["id"]
    )
    
    db.add(announcement)
    db.commit()
    db.refresh(announcement)
    
    return announcement.to_dict()


# 공지사항 수정 (작성자 또는 관리자만)
@router.put("/{announcement_id}", response_model=AnnouncementResponse)
async def update_announcement(
    announcement_id: int,
    announcement_data: AnnouncementUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """공지사항 수정 (작성자 또는 관리자만)"""
    announcement = db.query(Announcement).filter(
        Announcement.id == announcement_id
    ).first()
    
    if not announcement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="공지사항을 찾을 수 없습니다."
        )
    
    # 작성자 확인 (관리자 권한 체크)
    if not current_user.get("is_admin", False) and announcement.author_id != current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="공지사항을 수정할 권한이 없습니다."
        )
    
    # 업데이트할 필드만 수정
    if announcement_data.title is not None:
        announcement.title = announcement_data.title
    if announcement_data.content is not None:
        announcement.content = announcement_data.content
    if announcement_data.is_active is not None:
        announcement.is_active = announcement_data.is_active
    
    db.commit()
    db.refresh(announcement)
    
    return announcement.to_dict()


# 공지사항 삭제 (작성자 또는 관리자만)
@router.delete("/{announcement_id}")
async def delete_announcement(
    announcement_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """공지사항 삭제 (작성자 또는 관리자만)"""
    announcement = db.query(Announcement).filter(
        Announcement.id == announcement_id
    ).first()
    
    if not announcement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="공지사항을 찾을 수 없습니다."
        )
    
    # 작성자 확인 (관리자 권한 체크)
    if not current_user.get("is_admin", False) and announcement.author_id != current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="공지사항을 삭제할 권한이 없습니다."
        )
    
    # 실제 삭제 대신 비활성화
    announcement.is_active = False
    db.commit()
    
    return {"message": "공지사항이 삭제되었습니다."}


# 관리자용 공지사항 목록 조회 (비활성화된 것 포함)
@router.get("/admin/all", response_model=List[AnnouncementResponse])
async def get_all_announcements_admin(
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """관리자용 공지사항 목록 조회 (비활성화된 것 포함)"""
    # TODO: 관리자 권한 체크 로직 추가
    
    announcements = db.query(Announcement).options(
        joinedload(Announcement.author)
    ).order_by(
        Announcement.created_at.desc()
    ).offset(skip).limit(limit).all()
    
    return [announcement.to_dict() for announcement in announcements]


# 조회수 증가
@router.post("/{announcement_id}/view")
async def increment_view_count(
    announcement_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """공지사항 조회수 증가"""
    announcement = db.query(Announcement).filter(
        Announcement.id == announcement_id,
        Announcement.is_active == True
    ).first()
    
    if not announcement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="공지사항을 찾을 수 없습니다."
        )
    
    # 조회수 증가
    announcement.view_count += 1
    db.commit()
    
    return {"message": "조회수가 증가되었습니다.", "view_count": announcement.view_count}
