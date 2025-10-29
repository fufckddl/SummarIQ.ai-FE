"""
문의하기 API 라우터
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from database.connection import get_db
from models import Inquiry, User, InquiryStatus
from schemas.inquiry import InquiryCreate, InquiryUpdate, InquiryResponse, InquiryAdminReply, InquiryStatsResponse
from utils.auth_dependency import get_current_user

router = APIRouter(prefix="/api/inquiries", tags=["inquiries"])

# 내 문의 목록 조회
@router.get("/my", response_model=List[InquiryResponse])
async def get_my_inquiries(
    skip: int = 0,
    limit: int = 20,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """내 문의 목록 조회"""
    inquiries = db.query(Inquiry).options(
        joinedload(Inquiry.author),
        joinedload(Inquiry.admin)
    ).filter(
        Inquiry.author_id == current_user["id"],
        Inquiry.is_active == True
    ).order_by(
        Inquiry.created_at.desc()
    ).offset(skip).limit(limit).all()
    
    return [inquiry.to_dict() for inquiry in inquiries]

# 문의 상세 조회
@router.get("/{inquiry_id}", response_model=InquiryResponse)
async def get_inquiry(
    inquiry_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """문의 상세 조회"""
    inquiry = db.query(Inquiry).options(
        joinedload(Inquiry.author),
        joinedload(Inquiry.admin)
    ).filter(
        Inquiry.id == inquiry_id,
        Inquiry.is_active == True
    ).first()
    
    if not inquiry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="문의를 찾을 수 없습니다."
        )
    
    # 작성자 또는 관리자만 조회 가능
    if inquiry.author_id != current_user["id"] and not current_user.get("is_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="문의를 조회할 권한이 없습니다."
        )
    
    return inquiry.to_dict()

# 문의 작성
@router.post("/", response_model=InquiryResponse)
async def create_inquiry(
    inquiry_data: InquiryCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """문의 작성"""
    inquiry = Inquiry(
        title=inquiry_data.title,
        content=inquiry_data.content,
        author_id=current_user["id"]
    )
    
    db.add(inquiry)
    db.commit()
    db.refresh(inquiry)
    
    return inquiry.to_dict()

# 문의 수정 (작성자만)
@router.put("/{inquiry_id}", response_model=InquiryResponse)
async def update_inquiry(
    inquiry_id: int,
    inquiry_data: InquiryUpdate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """문의 수정 (작성자만)"""
    inquiry = db.query(Inquiry).filter(
        Inquiry.id == inquiry_id,
        Inquiry.is_active == True
    ).first()
    
    if not inquiry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="문의를 찾을 수 없습니다."
        )
    
    # 작성자만 수정 가능
    if inquiry.author_id != current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="문의를 수정할 권한이 없습니다."
        )
    
    # 업데이트할 필드만 수정
    if inquiry_data.title is not None:
        inquiry.title = inquiry_data.title
    if inquiry_data.content is not None:
        inquiry.content = inquiry_data.content
    
    db.commit()
    db.refresh(inquiry)
    
    return inquiry.to_dict()

# 문의 삭제 (작성자만)
@router.delete("/{inquiry_id}")
async def delete_inquiry(
    inquiry_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """문의 삭제 (작성자만)"""
    inquiry = db.query(Inquiry).filter(
        Inquiry.id == inquiry_id,
        Inquiry.is_active == True
    ).first()
    
    if not inquiry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="문의를 찾을 수 없습니다."
        )
    
    # 작성자만 삭제 가능
    if inquiry.author_id != current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="문의를 삭제할 권한이 없습니다."
        )
    
    # 실제 삭제 대신 비활성화
    inquiry.is_active = False
    db.commit()
    
    return {"message": "문의가 삭제되었습니다."}

# 관리자용 문의 목록 조회
@router.get("/admin/all", response_model=List[InquiryResponse])
async def get_all_inquiries_admin(
    skip: int = 0,
    limit: int = 50,
    status_filter: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """관리자용 문의 목록 조회"""
    # 관리자 권한 체크
    if not current_user.get("is_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="관리자만 접근할 수 있습니다."
        )
    
    query = db.query(Inquiry).options(
        joinedload(Inquiry.author),
        joinedload(Inquiry.admin)
    ).filter(
        Inquiry.is_active == True
    )
    
    # 상태 필터 적용
    if status_filter:
        try:
            status_enum = InquiryStatus(status_filter)
            query = query.filter(Inquiry.status == status_enum)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="유효하지 않은 상태 필터입니다."
            )
    
    inquiries = query.order_by(
        Inquiry.created_at.desc()
    ).offset(skip).limit(limit).all()
    
    return [inquiry.to_dict() for inquiry in inquiries]

# 관리자 답변
@router.post("/{inquiry_id}/reply")
async def reply_to_inquiry(
    inquiry_id: int,
    reply_data: InquiryAdminReply,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """관리자 답변"""
    # 관리자 권한 체크
    if not current_user.get("is_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="관리자만 답변할 수 있습니다."
        )
    
    inquiry = db.query(Inquiry).filter(
        Inquiry.id == inquiry_id,
        Inquiry.is_active == True
    ).first()
    
    if not inquiry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="문의를 찾을 수 없습니다."
        )
    
    # 답변 정보 업데이트
    inquiry.admin_reply = reply_data.admin_reply
    inquiry.admin_reply_at = datetime.now()
    inquiry.admin_id = current_user["id"]
    
    # 상태 업데이트
    if reply_data.status:
        try:
            inquiry.status = InquiryStatus(reply_data.status)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="유효하지 않은 상태입니다."
            )
    
    db.commit()
    db.refresh(inquiry)
    
    return {"message": "답변이 등록되었습니다.", "inquiry": inquiry.to_dict()}
