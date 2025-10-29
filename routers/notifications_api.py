"""
알림 API 라우터
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel
import json

from database.connection import get_db
from utils.auth_dependency import get_current_user
from models.notification import Notification, NotificationType, NotificationStatus
from models.user import User

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


class NotificationCreateRequest(BaseModel):
    """알림 생성 요청"""
    type: str
    title: str
    message: str
    data: Optional[dict] = None
    expires_at: Optional[datetime] = None


class NotificationUpdateRequest(BaseModel):
    """알림 업데이트 요청"""
    is_read: Optional[bool] = None
    status: Optional[str] = None


@router.get("/")
async def get_notifications(
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    type: Optional[str] = Query(None),
    is_read: Optional[bool] = Query(None)
):
    """사용자의 알림 목록 조회"""
    try:
        user_id = current_user["id"]
        
        # 쿼리 빌드
        query = db.query(Notification).filter(Notification.user_id == user_id)
        
        # 필터 적용
        if type:
            try:
                notification_type = NotificationType(type)
                query = query.filter(Notification.type == notification_type)
            except ValueError:
                raise HTTPException(status_code=400, detail="유효하지 않은 알림 타입입니다")
        
        if is_read is not None:
            query = query.filter(Notification.is_read == is_read)
        
        # 정렬 (최신순)
        query = query.order_by(Notification.created_at.desc())
        
        # 페이징
        offset = (page - 1) * limit
        notifications = query.offset(offset).limit(limit).all()
        total = query.count()
        
        # 응답 데이터 변환
        notifications_data = []
        for notification in notifications:
            notification_dict = notification.to_dict()
            # data 필드가 JSON 문자열인 경우 파싱
            if notification.data:
                try:
                    notification_dict["data"] = json.loads(notification.data)
                except json.JSONDecodeError:
                    notification_dict["data"] = notification.data
            notifications_data.append(notification_dict)
        
        return {
            "notifications": notifications_data,
            "total": total,
            "page": page,
            "limit": limit,
            "has_more": offset + limit < total
        }
        
    except Exception as e:
        print(f"알림 목록 조회 오류: {e}")
        raise HTTPException(status_code=500, detail="알림 목록 조회에 실패했습니다")


@router.get("/unread-count")
async def get_unread_count(
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """읽지 않은 알림 개수 조회"""
    try:
        user_id = current_user["id"]
        unread_count = db.query(Notification).filter(
            Notification.user_id == user_id,
            Notification.is_read == False
        ).count()
        
        return {"unread_count": unread_count}
        
    except Exception as e:
        print(f"읽지 않은 알림 개수 조회 오류: {e}")
        raise HTTPException(status_code=500, detail="읽지 않은 알림 개수 조회에 실패했습니다")


@router.post("/")
async def create_notification(
    request: NotificationCreateRequest,
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """새 알림 생성"""
    try:
        # 알림 타입 검증
        try:
            notification_type = NotificationType(request.type)
        except ValueError:
            raise HTTPException(status_code=400, detail="유효하지 않은 알림 타입입니다")
        
        # 알림 생성
        notification = Notification(
            user_id=current_user["id"],
            type=notification_type,
            title=request.title,
            message=request.message,
            data=json.dumps(request.data) if request.data else None,
            expires_at=request.expires_at,
            status=NotificationStatus.UNREAD
        )
        
        db.add(notification)
        db.commit()
        db.refresh(notification)
        
        # 응답 데이터 변환
        notification_dict = notification.to_dict()
        if notification.data:
            try:
                notification_dict["data"] = json.loads(notification.data)
            except json.JSONDecodeError:
                notification_dict["data"] = notification.data
        
        return notification_dict
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"알림 생성 오류: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="알림 생성에 실패했습니다")


@router.put("/{notification_id}")
async def update_notification(
    notification_id: int,
    request: NotificationUpdateRequest,
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """알림 업데이트"""
    try:
        # 알림 조회
        notification = db.query(Notification).filter(
            Notification.id == notification_id,
            Notification.user_id == current_user["id"]
        ).first()
        
        if not notification:
            raise HTTPException(status_code=404, detail="알림을 찾을 수 없습니다")
        
        # 업데이트
        if request.is_read is not None:
            notification.is_read = request.is_read
        
        if request.status:
            try:
                notification.status = NotificationStatus(request.status)
            except ValueError:
                raise HTTPException(status_code=400, detail="유효하지 않은 알림 상태입니다")
        
        db.commit()
        db.refresh(notification)
        
        # 응답 데이터 변환
        notification_dict = notification.to_dict()
        if notification.data:
            try:
                notification_dict["data"] = json.loads(notification.data)
            except json.JSONDecodeError:
                notification_dict["data"] = notification.data
        
        return notification_dict
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"알림 업데이트 오류: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="알림 업데이트에 실패했습니다")


@router.delete("/{notification_id}")
async def delete_notification(
    notification_id: int,
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """알림 삭제"""
    try:
        # 알림 조회
        notification = db.query(Notification).filter(
            Notification.id == notification_id,
            Notification.user_id == current_user["id"]
        ).first()
        
        if not notification:
            raise HTTPException(status_code=404, detail="알림을 찾을 수 없습니다")
        
        db.delete(notification)
        db.commit()
        
        return {"message": "알림이 삭제되었습니다"}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"알림 삭제 오류: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="알림 삭제에 실패했습니다")


@router.put("/mark-all-read")
async def mark_all_as_read(
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """모든 알림을 읽음으로 표시"""
    try:
        user_id = current_user["id"]
        
        # 모든 읽지 않은 알림을 읽음으로 표시
        db.query(Notification).filter(
            Notification.user_id == user_id,
            Notification.is_read == False
        ).update({"is_read": True})
        
        db.commit()
        
        return {"message": "모든 알림이 읽음으로 표시되었습니다"}
        
    except Exception as e:
        print(f"모든 알림 읽음 처리 오류: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="알림 읽음 처리에 실패했습니다")


@router.post("/team-invite")
async def create_team_invite_notification(
    team_id: int,
    invitee_email: str,
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """팀 초대 알림 생성"""
    try:
        # 초대받을 사용자 조회
        invitee = db.query(User).filter(User.email == invitee_email).first()
        if not invitee:
            raise HTTPException(status_code=404, detail="해당 이메일의 사용자를 찾을 수 없습니다")
        
        # 팀 정보 조회
        from models.team import Team
        team = db.query(Team).filter(Team.id == team_id).first()
        if not team:
            raise HTTPException(status_code=404, detail="팀을 찾을 수 없습니다")
        
        # 초대자 정보 조회
        inviter = db.query(User).filter(User.id == current_user["id"]).first()
        
        # 팀 초대 알림 생성
        notification = Notification(
            user_id=invitee.id,
            type=NotificationType.TEAM_INVITE,
            title="팀 초대",
            message=f"{team.name}에서 초대 요청을 보냈습니다.",
            data=json.dumps({
                "team_id": team_id,
                "team_name": team.name,
                "inviter_id": current_user["id"],
                "inviter_name": inviter.display_name or inviter.email,
                "invitee_email": invitee_email
            }),
            status=NotificationStatus.PENDING
        )
        
        db.add(notification)
        db.commit()
        db.refresh(notification)
        
        # 응답 데이터 변환
        notification_dict = notification.to_dict()
        notification_dict["data"] = json.loads(notification.data)
        
        return notification_dict
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"팀 초대 알림 생성 오류: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="팀 초대 알림 생성에 실패했습니다")
