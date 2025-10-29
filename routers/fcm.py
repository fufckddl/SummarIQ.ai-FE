"""
🚀 FCM (Firebase Cloud Messaging) API 라우터
Expo Push Notifications와 연동하여 사용
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

from database.connection import get_db
from routers.auth import get_current_user
from services.fcm_service import fcm_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/fcm", tags=["fcm"])

# Pydantic 모델들
class FCMTokenRequest(BaseModel):
    fcm_token: str
    platform: str

class NotificationRequest(BaseModel):
    title: str
    body: str
    data: Optional[Dict[str, Any]] = None
    tokens: Optional[List[str]] = None
    topic: Optional[str] = None

class TestNotificationRequest(BaseModel):
    title: str
    message: str

@router.post("/register-token")
async def register_fcm_token(
    request: FCMTokenRequest,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """
    FCM 토큰 등록
    """
    try:
        user_id = current_user["user_id"]
        
        # 사용자의 FCM 토큰 업데이트
        db.execute(
            "UPDATE users SET fcm_token = %s, platform = %s WHERE id = %s",
            (request.fcm_token, request.platform, user_id)
        )
        db.commit()
        
        logger.info(f"FCM 토큰 등록 완료: 사용자 {user_id}")
        return {"success": True, "message": "FCM 토큰이 등록되었습니다"}
        
    except Exception as e:
        logger.error(f"FCM 토큰 등록 실패: {str(e)}")
        raise HTTPException(status_code=500, detail="FCM 토큰 등록에 실패했습니다")

@router.delete("/unregister-token")
async def unregister_fcm_token(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """
    FCM 토큰 제거
    """
    try:
        user_id = current_user["user_id"]
        
        # 사용자의 FCM 토큰 제거
        db.execute(
            "UPDATE users SET fcm_token = NULL WHERE id = %s",
            (user_id,)
        )
        db.commit()
        
        logger.info(f"FCM 토큰 제거 완료: 사용자 {user_id}")
        return {"success": True, "message": "FCM 토큰이 제거되었습니다"}
        
    except Exception as e:
        logger.error(f"FCM 토큰 제거 실패: {str(e)}")
        raise HTTPException(status_code=500, detail="FCM 토큰 제거에 실패했습니다")

@router.post("/send")
async def send_notification(
    request: NotificationRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    알림 전송
    """
    try:
        if request.tokens:
            # 다중 사용자에게 전송
            result = await fcm_service.send_multicast_notification(
                tokens=request.tokens,
                title=request.title,
                body=request.body,
                data=request.data
            )
            return {"success": True, "result": result}
        
        elif request.topic:
            # 토픽 구독자들에게 전송
            success = await fcm_service.send_to_topic(
                topic=request.topic,
                title=request.title,
                body=request.body,
                data=request.data
            )
            return {"success": success}
        
        else:
            raise HTTPException(status_code=400, detail="tokens 또는 topic이 필요합니다")
    
    except Exception as e:
        logger.error(f"알림 전송 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/test")
async def send_test_notification(
    request: TestNotificationRequest,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """
    테스트 알림 전송
    """
    try:
        user_id = current_user["user_id"]
        
        # 사용자의 FCM 토큰 조회
        result = db.execute(
            "SELECT fcm_token FROM users WHERE id = %s",
            (user_id,)
        ).fetchone()
        
        if not result or not result[0]:
            raise HTTPException(status_code=400, detail="FCM 토큰이 등록되지 않았습니다")
        
        fcm_token = result[0]
        
        # 테스트 알림 전송
        success = await fcm_service.send_notification(
            token=fcm_token,
            title=request.title,
            body=request.message,
            data={
                "type": "test",
                "timestamp": datetime.now().isoformat(),
                "user_id": user_id
            }
        )
        
        if success:
            logger.info(f"테스트 알림 전송 성공: 사용자 {user_id}")
            return {"success": True, "message": "테스트 알림이 전송되었습니다"}
        else:
            logger.warning(f"테스트 알림 전송 실패: 사용자 {user_id}")
            return {"success": False, "message": "테스트 알림 전송에 실패했습니다"}
        
    except Exception as e:
        logger.error(f"테스트 알림 전송 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status")
async def get_fcm_status(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """
    FCM 상태 조회
    """
    try:
        user_id = current_user["user_id"]
        
        # 사용자의 FCM 토큰 조회
        result = db.execute(
            "SELECT fcm_token, platform FROM users WHERE id = %s",
            (user_id,)
        ).fetchone()
        
        if result:
            fcm_token, platform = result
            return {
                "has_token": fcm_token is not None,
                "token": fcm_token[:20] + "..." if fcm_token else None,
                "platform": platform
            }
        else:
            return {
                "has_token": False,
                "token": None,
                "platform": None
            }
        
    except Exception as e:
        logger.error(f"FCM 상태 조회 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
