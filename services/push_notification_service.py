"""
Expo Push Notification Service
Expo Push Notification API를 사용하여 푸시 알림 전송
"""
import httpx
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"


class PushNotificationService:
    """푸시 알림 전송 서비스"""
    
    @staticmethod
    async def send_notification(
        push_token: str,
        title: str,
        body: str,
        data: Optional[Dict] = None,
        sound: str = "default",
        priority: str = "default",
        channel_id: str = "default"
    ) -> Dict:
        """
        단일 푸시 알림 전송
        
        Args:
            push_token: Expo push token
            title: 알림 제목
            body: 알림 본문
            data: 추가 데이터 (딕셔너리)
            sound: 알림 사운드 ('default' or None)
            priority: 우선순위 ('default', 'normal', 'high')
            channel_id: Android 채널 ID
            
        Returns:
            응답 딕셔너리
        """
        if not push_token or not push_token.startswith('ExponentPushToken['):
            logger.warning(f"⚠️ Invalid push token format: {push_token}")
            return {"status": "error", "message": "Invalid token format"}
        
        # 개발용 토큰 체크 (dev-로 시작하는 토큰)
        if push_token.startswith('ExponentPushToken[dev-'):
            logger.info(f"🔧 Development token detected, simulating notification")
            logger.info(f"   Title: {title}")
            logger.info(f"   Body: {body}")
            logger.info(f"   Data: {data}")
            return {
                "status": "success", 
                "message": "Development mode - notification simulated",
                "dev_mode": True
            }
        
        message = {
            "to": push_token,
            "sound": sound,
            "title": title,
            "body": body,
            "data": data or {},
            "priority": priority,
            "channelId": channel_id
        }
        
        try:
            print(f"\n{'='*60}")
            print(f"📤 Sending push notification to {push_token[:30]}...")
            print(f"   Title: {title}")
            print(f"   Body: {body}")
            print(f"   Data: {data}")
            print(f"   Sending to Expo API: {EXPO_PUSH_URL}")
            print(f"   Full message: {message}")
            print(f"{'='*60}\n")
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    EXPO_PUSH_URL,
                    json=message,
                    headers={"Content-Type": "application/json"}
                )
                
                result = response.json()
                
                print(f"\n{'='*60}")
                print(f"📨 Expo API Response Status: {response.status_code}")
                print(f"📨 Expo API Response Body: {result}")
                print(f"{'='*60}\n")
                
                if response.status_code == 200:
                    # Expo API 응답 확인
                    response_data = result.get('data', {})
                    
                    # APNs 인증서 오류 체크
                    if isinstance(response_data, dict) and response_data.get('status') == 'error':
                        error_msg = response_data.get('message', 'Unknown error')
                        print(f"⚠️ Expo API returned error: {error_msg}")
                        
                        # APNs 인증서 없음 - 개발 모드로 처리
                        if 'APNs credentials' in error_msg or 'InvalidCredentials' in str(response_data):
                            print(f"🔧 APNs credentials missing - treating as development mode")
                            return {
                                "status": "success",
                                "message": "APNs credentials not configured - use local notifications",
                                "dev_mode": True,
                                "apns_error": True
                            }
                        
                        return {"status": "error", "data": result}
                    
                    print(f"✅ Push notification sent successfully")
                    return {"status": "success", "data": result}
                else:
                    print(f"❌ Push notification failed: {result}")
                    return {"status": "error", "data": result}
                    
        except Exception as e:
            logger.error(f"❌ Push notification error: {str(e)}")
            import traceback
            traceback.print_exc()
            return {"status": "error", "message": str(e)}
    
    @staticmethod
    async def send_batch_notifications(messages: List[Dict]) -> Dict:
        """
        여러 푸시 알림 일괄 전송
        
        Args:
            messages: 메시지 딕셔너리 리스트
            
        Returns:
            응답 딕셔너리
        """
        if not messages:
            return {"status": "error", "message": "No messages to send"}
        
        try:
            logger.info(f"📤 Sending {len(messages)} push notifications...")
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    EXPO_PUSH_URL,
                    json=messages,
                    headers={"Content-Type": "application/json"}
                )
                
                result = response.json()
                
                if response.status_code == 200:
                    logger.info(f"✅ Batch push notifications sent successfully")
                    return {"status": "success", "data": result}
                else:
                    logger.error(f"❌ Batch push notifications failed: {result}")
                    return {"status": "error", "data": result}
                    
        except Exception as e:
            logger.error(f"❌ Batch push notification error: {str(e)}")
            return {"status": "error", "message": str(e)}


# 알림 타입별 템플릿
class NotificationTemplates:
    """알림 템플릿"""
    
    @staticmethod
    def stt_complete(recording_title: str, recording_id: str) -> Dict:
        """STT 완료 알림"""
        return {
            "title": "🎤 음성 변환 완료",
            "body": f"{recording_title}의 음성이 텍스트로 변환되었습니다.",
            "data": {
                "type": "stt_complete",
                "recordingId": recording_id,
                "screen": f"/recordings/{recording_id}"
            }
        }
    
    @staticmethod
    def summary_complete(recording_title: str, recording_id: str) -> Dict:
        """요약 생성 완료 알림"""
        return {
            "title": "📝 요약 생성 완료",
            "body": f"{recording_title}의 요약이 준비되었습니다.",
            "data": {
                "type": "summary_complete",
                "recordingId": recording_id,
                "screen": f"/recordings/{recording_id}"
            }
        }
    
    @staticmethod
    def notion_upload_complete(recording_title: str, recording_id: str, notion_url: Optional[str] = None) -> Dict:
        """Notion 업로드 완료 알림"""
        return {
            "title": "📋 Notion 업로드 완료",
            "body": f"{recording_title}이 Notion에 업로드되었습니다.",
            "data": {
                "type": "notion_upload_complete",
                "recordingId": recording_id,
                "notionUrl": notion_url,
                "screen": f"/recordings/{recording_id}"
            }
        }
    
    @staticmethod
    def processing_error(recording_title: str, recording_id: str, error_type: str) -> Dict:
        """처리 오류 알림"""
        error_messages = {
            "stt_failed": "음성 변환에 실패했습니다",
            "notion_failed": "Notion 업로드에 실패했습니다",
            "summary_failed": "요약 생성에 실패했습니다"
        }
        
        message = error_messages.get(error_type, "처리 중 오류가 발생했습니다")
        
        return {
            "title": "⚠️ 처리 오류",
            "body": f"{recording_title} {message}.",
            "data": {
                "type": "error",
                "recordingId": recording_id,
                "errorType": error_type,
                "screen": f"/recordings/{recording_id}"
            }
        }


# 편의 함수들
async def notify_stt_complete(push_token: str, recording_title: str, recording_id: str):
    """STT 완료 알림 전송"""
    template = NotificationTemplates.stt_complete(recording_title, recording_id)
    return await PushNotificationService.send_notification(
        push_token=push_token,
        **template
    )


async def notify_summary_complete(push_token: str, recording_title: str, recording_id: str):
    """요약 완료 알림 전송"""
    template = NotificationTemplates.summary_complete(recording_title, recording_id)
    return await PushNotificationService.send_notification(
        push_token=push_token,
        **template
    )


async def notify_notion_upload_complete(
    push_token: str,
    recording_title: str,
    recording_id: str,
    notion_url: Optional[str] = None
):
    """Notion 업로드 완료 알림 전송"""
    template = NotificationTemplates.notion_upload_complete(
        recording_title, recording_id, notion_url
    )
    return await PushNotificationService.send_notification(
        push_token=push_token,
        **template
    )


async def notify_processing_error(
    push_token: str,
    recording_title: str,
    recording_id: str,
    error_type: str
):
    """처리 오류 알림 전송"""
    template = NotificationTemplates.processing_error(
        recording_title, recording_id, error_type
    )
    return await PushNotificationService.send_notification(
        push_token=push_token,
        priority="high",  # 오류는 높은 우선순위
        **template
    )

