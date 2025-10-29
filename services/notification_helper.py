"""
알림 헬퍼 서비스
FCM과 Expo Push를 통합하여 알림 전송
"""

import logging
from typing import Optional, Dict, Any
from services.fcm_service import fcm_service
from services.push_notification_service import PushNotificationService

logger = logging.getLogger(__name__)

# Expo Push 서비스 인스턴스
expo_push_service = PushNotificationService()


async def send_notification_to_user(
    user_id: int,
    fcm_token: Optional[str],
    push_token: Optional[str],
    platform: Optional[str],
    title: str,
    body: str,
    data: Optional[Dict[str, Any]] = None
) -> bool:
    """
    사용자에게 알림 전송 (FCM 또는 Expo Push 자동 선택)
    
    Args:
        user_id: 사용자 ID
        fcm_token: FCM 토큰 (Android)
        push_token: Expo Push 토큰 (iOS/Android)
        platform: 플랫폼 ('ios' or 'android')
        title: 알림 제목
        body: 알림 내용
        data: 추가 데이터
        
    Returns:
        bool: 전송 성공 여부
    """
    success = False
    
    try:
        # 1. FCM 토큰이 있고 Android인 경우 FCM 사용
        if fcm_token and platform == 'android':
            logger.info(f"📱 FCM으로 알림 전송 (사용자 {user_id})")
            success = await fcm_service.send_notification(
                token=fcm_token,
                title=title,
                body=body,
                data=data or {}
            )
            
            if success:
                logger.info(f"✅ FCM 알림 전송 성공 (사용자 {user_id})")
                return True
            else:
                logger.warning(f"⚠️ FCM 알림 전송 실패, Expo Push 시도 (사용자 {user_id})")
        
        # 2. Expo Push 토큰이 있는 경우 Expo Push 사용
        if push_token:
            logger.info(f"📱 Expo Push로 알림 전송 (사용자 {user_id})")
            result = await expo_push_service.send_notification(
                push_token=push_token,
                title=title,
                body=body,
                data=data or {}
            )
            success = result.get('status') == 'success'
            
            if success:
                logger.info(f"✅ Expo Push 알림 전송 성공 (사용자 {user_id})")
                return True
            else:
                logger.warning(f"⚠️ Expo Push 알림 전송 실패 (사용자 {user_id})")
        
        # 3. 둘 다 없는 경우
        if not fcm_token and not push_token:
            logger.warning(f"⚠️ 사용자 {user_id}에게 등록된 토큰이 없습니다")
            
        return success
        
    except Exception as e:
        logger.error(f"❌ 알림 전송 오류 (사용자 {user_id}): {str(e)}")
        return False


async def notify_recording_complete(
    user_id: int,
    fcm_token: Optional[str],
    push_token: Optional[str],
    platform: Optional[str],
    recording_id: int,
    recording_title: str
) -> bool:
    """녹음 처리 완료 알림"""
    return await send_notification_to_user(
        user_id=user_id,
        fcm_token=fcm_token,
        push_token=push_token,
        platform=platform,
        title="🎙️ 녹음 처리 완료!",
        body=f"'{recording_title}' 녹음이 처리되었습니다.",
        data={
            "type": "recording_complete",
            "recordingId": str(recording_id),
            "screen": f"/recordings/{recording_id}"
        }
    )


async def notify_summary_complete(
    user_id: int,
    fcm_token: Optional[str],
    push_token: Optional[str],
    platform: Optional[str],
    recording_id: int,
    recording_title: str
) -> bool:
    """AI 요약 완료 알림"""
    return await send_notification_to_user(
        user_id=user_id,
        fcm_token=fcm_token,
        push_token=push_token,
        platform=platform,
        title="✨ AI 요약 완료!",
        body=f"'{recording_title}'의 회의 요약이 준비되었습니다.",
        data={
            "type": "summary_complete",
            "recordingId": str(recording_id),
            "screen": f"/recordings/{recording_id}"
        }
    )


async def notify_notion_upload_complete(
    user_id: int,
    fcm_token: Optional[str],
    push_token: Optional[str],
    platform: Optional[str],
    recording_title: str,
    notion_page_url: Optional[str] = None
) -> bool:
    """Notion 업로드 완료 알림"""
    return await send_notification_to_user(
        user_id=user_id,
        fcm_token=fcm_token,
        push_token=push_token,
        platform=platform,
        title="📓 Notion 업로드 완료!",
        body=f"'{recording_title}'이(가) Notion에 저장되었습니다.",
        data={
            "type": "notion_upload",
            "notionPageUrl": notion_page_url or "",
            "screen": "/settings/notion"
        }
    )


async def notify_processing_error(
    user_id: int,
    fcm_token: Optional[str],
    push_token: Optional[str],
    platform: Optional[str],
    error_message: str
) -> bool:
    """처리 오류 알림"""
    return await send_notification_to_user(
        user_id=user_id,
        fcm_token=fcm_token,
        push_token=push_token,
        platform=platform,
        title="⚠️ 처리 오류",
        body=f"처리 중 오류가 발생했습니다: {error_message}",
        data={
            "type": "error",
            "screen": "/settings"
        }
    )
