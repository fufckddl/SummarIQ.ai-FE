"""
Push Notification API Router
푸시 알림 관련 API 엔드포인트
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional
import logging

from database.connection import get_db
from routers.auth import get_current_user
from models.user import User
from services.push_notification_service import PushNotificationService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/notifications", tags=["notifications"])


# Request/Response 모델
class RegisterTokenRequest(BaseModel):
    """Push Token 등록 요청"""
    push_token: str


class UpdateNotificationSettingsRequest(BaseModel):
    """알림 설정 업데이트 요청"""
    push_enabled: bool


class TestNotificationRequest(BaseModel):
    """테스트 알림 요청"""
    title: str
    body: str
    data: Optional[dict] = None


# API 엔드포인트
@router.post("/register-token", status_code=status.HTTP_200_OK)
async def register_push_token(
    request: RegisterTokenRequest,
    current_user_data: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Push Token 등록/업데이트
    
    프론트엔드에서 Expo push token을 받아 사용자 정보에 저장
    """
    try:
        user_id = current_user_data["user"]["id"]
        user = db.query(User).filter(User.id == user_id).first()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        logger.info(f"📲 Registering push token for user {user.id}")
        logger.info(f"   Token: {request.push_token[:30]}...")
        
        # 토큰 형식 검증
        if not request.push_token.startswith('ExponentPushToken['):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid Expo push token format"
            )
        
        # 사용자 push_token 업데이트
        user.push_token = request.push_token
        user.push_enabled = True
        
        db.commit()
        db.refresh(user)
        
        logger.info(f"✅ Push token registered successfully for user {user.id}")
        
        return {
            "message": "Push token registered successfully",
            "push_enabled": user.push_enabled
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error registering push token: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to register push token: {str(e)}"
        )


@router.delete("/unregister-token", status_code=status.HTTP_200_OK)
async def unregister_push_token(
    current_user_data: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Push Token 제거
    
    로그아웃 시 또는 알림을 완전히 비활성화할 때 사용
    """
    try:
        user_id = current_user_data["user"]["id"]
        user = db.query(User).filter(User.id == user_id).first()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        logger.info(f"🔕 Unregistering push token for user {user.id}")
        
        user.push_token = None
        user.push_enabled = False
        
        db.commit()
        db.refresh(user)
        
        logger.info(f"✅ Push token unregistered for user {user.id}")
        
        return {
            "message": "Push token unregistered successfully"
        }
        
    except Exception as e:
        logger.error(f"❌ Error unregistering push token: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to unregister push token: {str(e)}"
        )


@router.put("/settings", status_code=status.HTTP_200_OK)
async def update_notification_settings(
    request: UpdateNotificationSettingsRequest,
    current_user_data: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    알림 설정 업데이트
    
    알림 활성화/비활성화 토글
    """
    try:
        user_id = current_user_data["user"]["id"]
        user = db.query(User).filter(User.id == user_id).first()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        logger.info(f"⚙️ Updating notification settings for user {user.id}")
        logger.info(f"   Push enabled: {request.push_enabled}")
        
        user.push_enabled = request.push_enabled
        
        db.commit()
        db.refresh(user)
        
        logger.info(f"✅ Notification settings updated for user {user.id}")
        
        return {
            "message": "Notification settings updated successfully",
            "push_enabled": user.push_enabled
        }
        
    except Exception as e:
        logger.error(f"❌ Error updating notification settings: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update notification settings: {str(e)}"
        )


@router.get("/settings", status_code=status.HTTP_200_OK)
async def get_notification_settings(
    current_user_data: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    알림 설정 조회
    """
    user_id = current_user_data["user"]["id"]
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {
        "push_enabled": user.push_enabled if user.push_enabled is not None else False,
        "has_push_token": bool(user.push_token)
    }


@router.post("/test", status_code=status.HTTP_200_OK)
async def send_test_notification(
    request: TestNotificationRequest,
    current_user_data: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    테스트 알림 전송
    
    디버깅 및 테스트 목적
    """
    try:
        user_id = current_user_data["user"]["id"]
        user = db.query(User).filter(User.id == user_id).first()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        if not user.push_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No push token registered for this user"
            )
        
        if not user.push_enabled:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Push notifications are disabled for this user"
            )
        
        logger.info(f"🧪 Sending test notification to user {user.id}")
        
        result = await PushNotificationService.send_notification(
            push_token=user.push_token,
            title=request.title,
            body=request.body,
            data=request.data or {"test": True}
        )
        
        if result.get("status") == "success":
            return {
                "message": "Test notification sent successfully",
                "result": result
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to send test notification: {result.get('message')}"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error sending test notification: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send test notification: {str(e)}"
        )

