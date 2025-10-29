"""
JWT 토큰 서비스
"""
import jwt
import uuid
from datetime import datetime, timedelta
from typing import Dict, Optional
import os


class JWTService:
    """JWT 토큰 생성 및 검증"""
    
    def __init__(self):
        self.secret_key = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
        self.algorithm = "HS256"
        # 모바일 앱: 더 긴 유효기간 사용 (자동 갱신 구현 권장)
        self.access_token_expire_minutes = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))  # 24시간 (1일)
        self.refresh_token_expire_days = int(os.getenv("JWT_REFRESH_TOKEN_EXPIRE_DAYS", "30"))  # 30일
    
    def create_access_token(self, user_id: int, email: Optional[str] = None) -> str:
        """액세스 토큰 생성 (기본 24시간, 환경변수로 변경 가능)"""
        import time
        
        # UTC 타임스탬프 사용 (시간대 문제 방지)
        now_timestamp = int(time.time())
        exp_timestamp = now_timestamp + (self.access_token_expire_minutes * 60)
        
        payload = {
            "sub": user_id,
            "email": email,
            "type": "access",
            "exp": exp_timestamp,
            "iat": now_timestamp,
        }
        
        print(f"🔑 액세스 토큰 생성: user_id={user_id}, 만료={self.access_token_expire_minutes}분 후")
        print(f"   발급 시각 (timestamp): {now_timestamp}")
        print(f"   만료 시각 (timestamp): {exp_timestamp}")
        
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    def create_refresh_token(self, user_id: int, family_id: Optional[str] = None) -> tuple[str, str]:
        """
        리프레시 토큰 생성 (30일)
        
        Returns:
            (token, family_id)
        """
        import time
        
        if not family_id:
            family_id = str(uuid.uuid4())
        
        # UTC 타임스탬프 사용 (시간대 문제 방지)
        now_timestamp = int(time.time())
        exp_timestamp = now_timestamp + (self.refresh_token_expire_days * 24 * 60 * 60)
        
        payload = {
            "sub": user_id,
            "type": "refresh",
            "family_id": family_id,
            "exp": exp_timestamp,
            "iat": now_timestamp,
        }
        
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        return token, family_id
    
    def verify_token(self, token: str, token_type: str = "access") -> Optional[Dict]:
        """
        토큰 검증
        
        Args:
            token: JWT 토큰
            token_type: 'access' 또는 'refresh'
            
        Returns:
            페이로드 딕셔너리 또는 None (검증 실패)
        """
        try:
            print(f"🔍 verify_token 호출됨: token_type={token_type}, 토큰={token[:50]}...")
            
            # JWT는 자동으로 만료 시간 검증 (타임스탬프 기준)
            # leeway 추가로 시간 오차 허용 (10초)
            payload = jwt.decode(
                token, 
                self.secret_key, 
                algorithms=[self.algorithm],
                options={"verify_exp": True},
                leeway=10
            )
            
            print(f"✅ jwt.decode 성공!")
            
            # 디버깅: 토큰 정보 출력
            import time
            now_timestamp = int(time.time())
            exp_timestamp = payload.get("exp", 0)
            iat_timestamp = payload.get("iat", 0)
            
            print(f"🔍 토큰 검증:")
            print(f"   현재 시각 (timestamp): {now_timestamp} ({datetime.fromtimestamp(now_timestamp)})")
            print(f"   발급 시각 (timestamp): {iat_timestamp} ({datetime.fromtimestamp(iat_timestamp)})")
            print(f"   만료 시각 (timestamp): {exp_timestamp} ({datetime.fromtimestamp(exp_timestamp)})")
            print(f"   남은 시간: {(exp_timestamp - now_timestamp) / 60:.1f}분")
            
            # 토큰 타입 검증
            if payload.get("type") != token_type:
                print(f"❌ 토큰 타입 불일치: {payload.get('type')} != {token_type}")
                return None
            
            return payload
            
        except jwt.ExpiredSignatureError:
            print("❌ Token expired")
            return None
        except jwt.InvalidTokenError as e:
            print(f"❌ Invalid token: {e}")
            return None
    
    def get_user_id_from_token(self, token: str) -> Optional[int]:
        """토큰에서 user_id 추출"""
        payload = self.verify_token(token, token_type="access")
        return payload.get("sub") if payload else None

