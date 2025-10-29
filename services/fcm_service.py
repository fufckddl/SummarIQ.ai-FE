"""
🚀 FCM (Firebase Cloud Messaging) 서비스
Expo Push Notifications와 연동하여 사용

사용법:
1. FCM_SERVER_KEY를 환경변수로 설정
2. FCMService 인스턴스 생성
3. send_notification, send_multicast_notification 등 메서드 사용
"""

from typing import List, Optional, Dict, Any
from pyfcm import FCMNotification
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor
import os

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FCMService:
    """
    Firebase Cloud Messaging 서비스 클래스
    Expo Push Notifications와 연동하여 사용
    """
    
    def __init__(self, server_key: Optional[str] = None):
        """
        FCM 서비스 초기화
        
        Args:
            server_key (str): Firebase 서버 키 (환경변수에서 자동 로드)
        """
        self.server_key = server_key or os.getenv('FCM_SERVER_KEY')
        if not self.server_key:
            logger.warning("FCM_SERVER_KEY가 설정되지 않았습니다. FCM 기능이 비활성화됩니다.")
            self.push_service = None
        else:
            try:
                # pyfcm 2.x 버전용 초기화
                self.push_service = FCMNotification(service_account_file=None, server_key=self.server_key)
                logger.info("FCM 서비스 초기화 완료")
            except TypeError:
                # 구버전 호환성
                try:
                    self.push_service = FCMNotification(api_key=self.server_key)
                    logger.info("FCM 서비스 초기화 완료 (legacy)")
                except:
                    logger.warning("FCM 초기화 실패. FCM 기능이 비활성화됩니다.")
                    self.push_service = None
        
        self.executor = ThreadPoolExecutor(max_workers=5)
    
    async def send_notification(
        self,
        token: str,
        title: str,
        body: str,
        data: Optional[Dict[str, Any]] = None,
        sound: str = "default",
        badge: Optional[int] = None
    ) -> bool:
        """
        단일 사용자에게 알림 전송
        
        Args:
            token (str): FCM 토큰 (Expo Push Token)
            title (str): 알림 제목
            body (str): 알림 내용
            data (Optional[Dict]): 추가 데이터
            sound (str): 알림 소리
            badge (Optional[int]): 배지 숫자
            
        Returns:
            bool: 전송 성공 여부
        """
        try:
            if not self.push_service:
                logger.error("FCM 서비스가 초기화되지 않았습니다")
                return False
                
            logger.info(f"알림 전송 시작: {title[:20]}...")
            
            # 알림 데이터 구성
            message_data = {
                "title": title,
                "body": body,
                "sound": sound,
                "data": data or {},
            }
            
            if badge is not None:
                message_data["badge"] = badge
            
            # FCM을 통한 알림 전송 (비동기 처리)
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.executor,
                self._send_sync_notification,
                token,
                message_data
            )
            
            if result:
                logger.info(f"✅ 알림 전송 성공: {title[:20]}...")
                return True
            else:
                logger.warning(f"❌ 알림 전송 실패: {title[:20]}...")
                return False
                
        except Exception as e:
            logger.error(f"❌ 알림 전송 오류: {str(e)}")
            return False
    
    async def send_multicast_notification(
        self,
        tokens: List[str],
        title: str,
        body: str,
        data: Optional[Dict[str, Any]] = None,
        sound: str = "default",
        badge: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        다중 사용자에게 알림 전송
        
        Args:
            tokens (List[str]): FCM 토큰 리스트
            title (str): 알림 제목
            body (str): 알림 내용
            data (Optional[Dict]): 추가 데이터
            sound (str): 알림 소리
            badge (Optional[int]): 배지 숫자
            
        Returns:
            Dict: 전송 결과 (성공/실패 개수)
        """
        try:
            if not self.push_service:
                logger.error("FCM 서비스가 초기화되지 않았습니다")
                return {"success": 0, "failure": len(tokens), "invalid_tokens": []}
                
            logger.info(f"다중 알림 전송 시작: {len(tokens)}개 토큰, {title[:20]}...")
            
            if not tokens:
                logger.warning("토큰 리스트가 비어있음")
                return {"success": 0, "failure": 0, "invalid_tokens": []}
            
            # 알림 데이터 구성
            message_data = {
                "title": title,
                "body": body,
                "sound": sound,
                "data": data or {},
            }
            
            if badge is not None:
                message_data["badge"] = badge
            
            # FCM을 통한 다중 알림 전송 (비동기 처리)
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.executor,
                self._send_sync_multicast,
                tokens,
                message_data
            )
            
            logger.info(f"✅ 다중 알림 전송 완료: {result}")
            return result
                
        except Exception as e:
            logger.error(f"❌ 다중 알림 전송 오류: {str(e)}")
            return {"success": 0, "failure": len(tokens), "invalid_tokens": []}
    
    def _send_sync_notification(self, token: str, message_data: Dict[str, Any]) -> bool:
        """
        동기 방식으로 단일 알림 전송
        
        Args:
            token (str): FCM 토큰
            message_data (Dict): 알림 데이터
            
        Returns:
            bool: 전송 성공 여부
        """
        try:
            result = self.push_service.notify_single_device(
                registration_id=token,
                message_title=message_data["title"],
                message_body=message_data["body"],
                data_message=message_data["data"],
                sound=message_data.get("sound", "default"),
                badge=message_data.get("badge"),
                click_action="FLUTTER_NOTIFICATION_CLICK"
            )
            
            return result.get('success', 0) > 0
            
        except Exception as e:
            logger.error(f"동기 알림 전송 오류: {str(e)}")
            return False
    
    def _send_sync_multicast(self, tokens: List[str], message_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        동기 방식으로 다중 알림 전송
        
        Args:
            tokens (List[str]): FCM 토큰 리스트
            message_data (Dict): 알림 데이터
            
        Returns:
            Dict: 전송 결과
        """
        try:
            result = self.push_service.notify_multiple_devices(
                registration_ids=tokens,
                message_title=message_data["title"],
                message_body=message_data["body"],
                data_message=message_data["data"],
                sound=message_data.get("sound", "default"),
                badge=message_data.get("badge"),
                click_action="FLUTTER_NOTIFICATION_CLICK"
            )
            
            # 결과 파싱
            success = result.get('success', 0)
            failure = result.get('failure', 0)
            invalid_tokens = result.get('results', [])
            
            return {
                "success": success,
                "failure": failure,
                "invalid_tokens": [token for i, token in enumerate(tokens) 
                                 if i < len(invalid_tokens) and 
                                 invalid_tokens[i].get('error')]
            }
            
        except Exception as e:
            logger.error(f"동기 다중 알림 전송 오류: {str(e)}")
            return {"success": 0, "failure": len(tokens), "invalid_tokens": []}
    
    async def send_to_topic(
        self,
        topic: str,
        title: str,
        body: str,
        data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        토픽 구독자들에게 알림 전송
        
        Args:
            topic (str): 토픽 이름
            title (str): 알림 제목
            body (str): 알림 내용
            data (Optional[Dict]): 추가 데이터
            
        Returns:
            bool: 전송 성공 여부
        """
        try:
            if not self.push_service:
                logger.error("FCM 서비스가 초기화되지 않았습니다")
                return False
                
            logger.info(f"토픽 알림 전송 시작: {topic}")
            
            message_data = {
                "title": title,
                "body": body,
                "data": data or {},
            }
            
            # FCM을 통한 토픽 알림 전송 (비동기 처리)
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.executor,
                self._send_sync_topic,
                topic,
                message_data
            )
            
            if result:
                logger.info(f"✅ 토픽 알림 전송 성공: {topic}")
                return True
            else:
                logger.warning(f"❌ 토픽 알림 전송 실패: {topic}")
                return False
                
        except Exception as e:
            logger.error(f"❌ 토픽 알림 전송 오류: {str(e)}")
            return False
    
    def _send_sync_topic(self, topic: str, message_data: Dict[str, Any]) -> bool:
        """
        동기 방식으로 토픽 알림 전송
        
        Args:
            topic (str): 토픽 이름
            message_data (Dict): 알림 데이터
            
        Returns:
            bool: 전송 성공 여부
        """
        try:
            result = self.push_service.notify_topic_subscribers(
                topic_name=topic,
                message_title=message_data["title"],
                message_body=message_data["body"],
                data_message=message_data["data"],
                click_action="FLUTTER_NOTIFICATION_CLICK"
            )
            
            return result.get('success', 0) > 0
            
        except Exception as e:
            logger.error(f"토픽 알림 전송 오류: {str(e)}")
            return False
    
    async def validate_token(self, token: str) -> bool:
        """
        FCM 토큰 유효성 검증
        
        Args:
            token (str): FCM 토큰
            
        Returns:
            bool: 토큰 유효성
        """
        try:
            # 간단한 테스트 알림으로 토큰 유효성 검증
            result = await self.send_notification(
                token=token,
                title="토큰 검증",
                body="이 메시지는 토큰 검증을 위한 테스트입니다.",
                data={"type": "token_validation"}
            )
            
            return result
            
        except Exception as e:
            logger.error(f"토큰 유효성 검증 오류: {str(e)}")
            return False
    
    def cleanup(self):
        """
        리소스 정리
        """
        self.executor.shutdown(wait=True)
        logger.info("FCM 서비스 리소스 정리 완료")


# FCM 서비스 인스턴스 생성
fcm_service = FCMService()
