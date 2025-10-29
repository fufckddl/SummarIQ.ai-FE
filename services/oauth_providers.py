"""
OAuth 프로바이더 어댑터
"""
import httpx
from typing import Dict, Optional
from abc import ABC, abstractmethod


class OAuthProfile:
    """OAuth 프로필 데이터"""
    def __init__(
        self,
        issuer: str,
        subject: str,
        email: Optional[str] = None,
        email_verified: Optional[bool] = None,
        name: Optional[str] = None,
        picture: Optional[str] = None,
        locale: Optional[str] = None,
        raw_profile: Optional[Dict] = None
    ):
        self.issuer = issuer
        self.subject = subject
        self.email = email
        self.email_verified = email_verified
        self.name = name
        self.picture = picture
        self.locale = locale
        self.raw_profile = raw_profile or {}


class OAuthProvider(ABC):
    """OAuth 프로바이더 베이스 클래스"""
    
    @abstractmethod
    async def verify_and_get_profile(self, access_token: str, id_token: Optional[str] = None) -> OAuthProfile:
        """토큰 검증 및 프로필 조회"""
        pass


class KakaoProvider(OAuthProvider):
    """카카오 OAuth 프로바이더"""
    
    async def verify_and_get_profile(self, access_token: str, id_token: Optional[str] = None) -> OAuthProfile:
        """카카오 토큰 검증 및 프로필 조회"""
        async with httpx.AsyncClient() as client:
            # 카카오 사용자 정보 조회
            response = await client.get(
                "https://kapi.kakao.com/v2/user/me",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            
            if response.status_code != 200:
                raise Exception(f"카카오 토큰 검증 실패: {response.status_code}")
            
            data = response.json()
            kakao_account = data.get("kakao_account", {})
            profile = kakao_account.get("profile", {})
            
            # 카카오에서 받은 데이터 상세 로깅
            print(f"🔍 카카오 프로필 데이터:")
            print(f"   - ID: {data.get('id')}")
            print(f"   - 이메일: {kakao_account.get('email')}")
            print(f"   - 이메일 검증: {kakao_account.get('is_email_verified')}")
            print(f"   - 닉네임: {profile.get('nickname')}")
            print(f"   - 프로필 이미지: {profile.get('profile_image_url')}")
            
            # 이메일 추출
            email = kakao_account.get("email")
            
            # 닉네임 추출
            nickname = profile.get("nickname")
            if not nickname:
                # 이메일이 있으면 @ 앞부분을 사용, 없으면 "카카오 사용자" 사용
                if email and "@" in email:
                    nickname = email.split("@")[0]
                else:
                    nickname = "카카오 사용자"
            
            oauth_profile = OAuthProfile(
                issuer="kakao",
                subject=str(data["id"]),
                email=email,
                email_verified=kakao_account.get("is_email_verified", False),
                name=nickname,
                picture=profile.get("profile_image_url"),
                locale="ko-KR",
                raw_profile=data
            )
            
            print(f"📦 생성된 OAuth 프로필:")
            print(f"   - email: {oauth_profile.email}")
            print(f"   - name: {oauth_profile.name}")
            print(f"   - email_verified: {oauth_profile.email_verified}")
            
            return oauth_profile


class GoogleProvider(OAuthProvider):
    """구글 OAuth 프로바이더"""
    
    async def verify_and_get_profile(self, access_token: str, id_token: Optional[str] = None) -> OAuthProfile:
        """구글 토큰 검증 및 프로필 조회"""
        async with httpx.AsyncClient() as client:
            # 구글 사용자 정보 조회
            response = await client.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            
            if response.status_code != 200:
                raise Exception(f"구글 토큰 검증 실패: {response.status_code}")
            
            data = response.json()
            
            return OAuthProfile(
                issuer="google",
                subject=data["id"],
                email=data.get("email"),
                email_verified=data.get("verified_email", False),
                name=data.get("name"),
                picture=data.get("picture"),
                locale=data.get("locale", "ko-KR"),
                raw_profile=data
            )


class NaverProvider(OAuthProvider):
    """네이버 OAuth 프로바이더"""
    
    async def verify_and_get_profile(self, access_token: str, id_token: Optional[str] = None) -> OAuthProfile:
        """네이버 토큰 검증 및 프로필 조회"""
        async with httpx.AsyncClient() as client:
            # 네이버 사용자 정보 조회
            response = await client.get(
                "https://openapi.naver.com/v1/nid/me",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            
            if response.status_code != 200:
                raise Exception(f"네이버 토큰 검증 실패: {response.status_code}")
            
            data = response.json()
            
            if data.get("resultcode") != "00":
                raise Exception(f"네이버 API 오류: {data.get('message')}")
            
            profile = data.get("response", {})
            
            return OAuthProfile(
                issuer="naver",
                subject=profile["id"],
                email=profile.get("email"),
                email_verified=True,  # 네이버는 기본적으로 이메일 검증됨
                name=profile.get("name") or profile.get("nickname"),
                picture=profile.get("profile_image"),
                locale="ko-KR",
                raw_profile=data
            )


class AppleProvider(OAuthProvider):
    """애플 OAuth 프로바이더"""
    
    async def verify_and_get_profile(self, access_token: str, id_token: Optional[str] = None) -> OAuthProfile:
        """애플 ID 토큰 검증 및 프로필 조회"""
        import jwt as pyjwt
        
        if not id_token:
            raise Exception("애플 로그인은 id_token이 필요합니다")
        
        # ID 토큰 디코딩 (검증 없이 - 실제 프로덕션에서는 애플 공개키로 검증 필요)
        try:
            # 실제 프로덕션에서는 애플 공개키로 검증해야 함
            decoded = pyjwt.decode(id_token, options={"verify_signature": False})
            
            return OAuthProfile(
                issuer="apple",
                subject=decoded["sub"],
                email=decoded.get("email"),
                email_verified=decoded.get("email_verified") == "true" if "email_verified" in decoded else None,
                name=None,  # 애플은 이름을 제공하지 않음
                picture=None,
                locale="ko-KR",
                raw_profile=decoded
            )
            
        except Exception as e:
            raise Exception(f"애플 ID 토큰 검증 실패: {str(e)}")


# 프로바이더 팩토리
def get_oauth_provider(provider: str) -> OAuthProvider:
    """프로바이더 인스턴스 반환"""
    providers = {
        "kakao": KakaoProvider(),
        "google": GoogleProvider(),
        "naver": NaverProvider(),
        "apple": AppleProvider(),
    }
    
    provider_instance = providers.get(provider.lower())
    if not provider_instance:
        raise ValueError(f"지원하지 않는 프로바이더: {provider}")
    
    return provider_instance

