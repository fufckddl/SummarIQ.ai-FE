"""
인증 라우터 (OAuth 즉시 가입 지원)
"""
from fastapi import APIRouter, HTTPException, Depends, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import uuid

from database.connection import get_db
from database import auth_crud
from services.jwt_service import JWTService
from services.oauth_providers import get_oauth_provider, OAuthProfile


router = APIRouter(prefix="/auth", tags=["Auth"])

# 서비스 초기화
jwt_service = JWTService()


# ==================== Request Models ====================

class OAuthLoginRequest(BaseModel):
    access_token: Optional[str] = None
    id_token: Optional[str] = None
    prompt_merge: bool = False


class LocalSignupRequest(BaseModel):
    email: str
    password: str
    display_name: Optional[str] = None


class LocalLoginRequest(BaseModel):
    email: str
    password: str


class LinkIdentityRequest(BaseModel):
    provider: str
    access_token: Optional[str] = None
    id_token: Optional[str] = None


class SetPasswordRequest(BaseModel):
    password: str


class SetNicknameRequest(BaseModel):
    user_id: int
    nickname: str


class LogoutRequest(BaseModel):
    refresh_token: Optional[str] = None


# ==================== Helper Functions ====================

def create_user_from_oauth(
    db: Session,
    profile: OAuthProfile,
    provider: str
) -> tuple[any, any]:
    """
    OAuth 프로필에서 사용자 생성 + Identity 연결
    
    Returns:
        (user, identity)
    """
    print(f"👤 새 사용자 생성 시작:")
    print(f"   - email: {profile.email}")
    print(f"   - display_name: {profile.name}")
    print(f"   - email_verified: {profile.email_verified}")
    print(f"   - avatar_url: {profile.picture}")
    print(f"   - provider: {provider}")
    
    # 사용자 생성
    user = auth_crud.create_user(
        db,
        email=profile.email,
        email_verified=profile.email_verified or False,
        display_name=profile.name,
        avatar_url=profile.picture,
        locale=profile.locale or "ko-KR",
        created_via=provider
    )
    
    print(f"✅ 사용자 생성 완료: ID={user.id}, email={user.email}, display_name={user.display_name}")
    
    # Identity 생성
    identity = auth_crud.create_identity(
        db,
        user_id=user.id,
        provider=provider,
        subject=profile.subject,
        email_verified=profile.email_verified,
        profile_name=profile.name,
        profile_picture=profile.picture,
        raw_profile=profile.raw_profile
    )
    
    return user, identity


def issue_tokens(db: Session, user: any, request: Request) -> dict:
    """토큰 발급"""
    # Access Token 생성
    access_token = jwt_service.create_access_token(user.id, user.email)
    
    # Refresh Token 생성
    family_id = str(uuid.uuid4())
    refresh_token, _ = jwt_service.create_refresh_token(user.id, family_id)
    
    # Refresh Token DB에 저장
    auth_crud.create_refresh_token(
        db,
        user_id=user.id,
        token=refresh_token,
        family_id=family_id,
        device_info=request.headers.get("User-Agent"),
        ip_address=request.client.host if request.client else None
    )
    
    # 마지막 로그인 시간 업데이트
    auth_crud.update_last_login(db, user.id)
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": jwt_service.access_token_expire_minutes * 60,
        "user": user.to_dict()
    }


# ==================== OAuth 로그인 ====================

@router.post("/oauth/{provider}")
async def oauth_login(
    provider: str,
    body: OAuthLoginRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    OAuth 로그인/즉시 가입
    
    Args:
        provider: kakao|google|naver|apple
        body: { access_token?, id_token?, prompt_merge? }
        
    Returns:
        200: { access_token, refresh_token, user }
        409: { action: 'confirm_link', existing_user_id, reason, email }
    """
    try:
        # 1. 프로바이더 어댑터로 프로필 조회
        oauth_provider = get_oauth_provider(provider)
        profile = await oauth_provider.verify_and_get_profile(
            access_token=body.access_token,
            id_token=body.id_token
        )
        
        print(f"🔐 OAuth 로그인: {provider}")
        print(f"   - subject: {profile.subject}")
        print(f"   - email: {profile.email}")
        print(f"   - name: {profile.name}")
        
        # 2. Identity 확인
        existing_identity = auth_crud.get_identity(db, provider, profile.subject)
        
        if existing_identity:
            # 기존 Identity가 있으면 로그인
            user = auth_crud.get_user_by_id(db, existing_identity.user_id)
            print(f"✅ 기존 사용자 로그인: {user.id}")
            
            return issue_tokens(db, user, request)
        
        # 3. 이메일 충돌 확인
        if profile.email:
            existing_user = auth_crud.get_user_by_email(db, profile.email)
            
            if existing_user:
                # 이메일이 이미 존재
                print(f"⚠️  이메일 충돌: {profile.email} (기존 사용자 {existing_user.id})")
                
                # 자동 병합 정책 (email_verified가 모두 true인 경우)
                if existing_user.email_verified and profile.email_verified:
                    print(f"🔗 자동 병합: 검증된 이메일")
                    
                    # Identity 연결
                    identity = auth_crud.create_identity(
                        db,
                        user_id=existing_user.id,
                        provider=provider,
                        subject=profile.subject,
                        email_verified=profile.email_verified,
                        profile_name=profile.name,
                        profile_picture=profile.picture,
                        raw_profile=profile.raw_profile
                    )
                    
                    return issue_tokens(db, existing_user, request)
                else:
                    # 이메일 소유 증명 필요
                    return {
                        "action": "confirm_link",
                        "existing_user_id": existing_user.id,
                        "reason": "email_conflict",
                        "email": profile.email,
                        "message": "이 이메일로 가입된 계정이 있습니다. 연결하시겠습니까?"
                    }, 409
        
        # 4. 새 사용자 생성
        print(f"✅ 새 사용자 생성: {provider}")
        
        # 닉네임이 없는 경우 (사용자가 동의하지 않음)
        if not profile.name or profile.name == "카카오 사용자":
            print(f"⚠️  닉네임 미제공: 닉네임 설정 필요")
            
            # 임시 사용자 생성 (닉네임 없이)
            user, identity = create_user_from_oauth(db, profile, provider)
            
            # 닉네임 설정 요청 응답
            return {
                "action": "set_nickname",
                "user_id": user.id,
                "provider": provider,
                "message": "닉네임을 설정해주세요"
            }, 202  # 202 Accepted
        
        # 닉네임이 있는 경우 정상 가입
        user, identity = create_user_from_oauth(db, profile, provider)
        
        return issue_tokens(db, user, request)
        
    except Exception as e:
        print(f"❌ OAuth 로그인 실패: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"OAuth 로그인 실패: {str(e)}")


# ==================== 로컬 회원가입 ====================

@router.post("/signup")
async def local_signup(
    body: LocalSignupRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    로컬 회원가입 (이메일 + 비밀번호)
    """
    try:
        # 이메일 중복 확인
        existing_user = auth_crud.get_user_by_email(db, body.email)
        if existing_user:
            raise HTTPException(status_code=409, detail="이미 가입된 이메일입니다")
        
        # 사용자 생성
        user = auth_crud.create_user(
            db,
            email=body.email,
            email_verified=False,  # 이메일 인증 필요
            display_name=body.display_name,
            created_via="local"
        )
        
        # 비밀번호 저장
        auth_crud.create_credential(db, user.id, body.password)
        
        print(f"✅ 로컬 회원가입: {user.email}")
        
        return issue_tokens(db, user, request)
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 회원가입 실패: {e}")
        raise HTTPException(status_code=500, detail=f"회원가입 실패: {str(e)}")


# ==================== 로컬 로그인 ====================

@router.post("/login")
async def local_login(
    body: LocalLoginRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    로컬 로그인 (이메일 + 비밀번호)
    """
    try:
        # 이메일로 사용자 조회
        user = auth_crud.get_user_by_email(db, body.email)
        if not user:
            raise HTTPException(status_code=401, detail="이메일 또는 비밀번호가 올바르지 않습니다")
        
        # 비밀번호 검증
        if not auth_crud.verify_password(db, user.id, body.password):
            raise HTTPException(status_code=401, detail="이메일 또는 비밀번호가 올바르지 않습니다")
        
        print(f"✅ 로컬 로그인: {user.email}")
        
        return issue_tokens(db, user, request)
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 로그인 실패: {e}")
        raise HTTPException(status_code=500, detail=f"로그인 실패: {str(e)}")


# ==================== 외부 계정 연결 ====================

@router.post("/link")
async def link_identity(
    body: LinkIdentityRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    로그인 상태에서 외부 계정 연결
    
    Headers:
        Authorization: Bearer {access_token}
    """
    try:
        # Authorization 헤더에서 토큰 추출
        authorization = request.headers.get("Authorization")
        if not authorization:
            raise HTTPException(status_code=401, detail="Authorization 헤더가 필요합니다")
        
        token = authorization.replace("Bearer ", "")
        user_id = jwt_service.get_user_id_from_token(token)
        
        if not user_id:
            raise HTTPException(status_code=401, detail="유효하지 않은 토큰입니다")
        
        # 사용자 확인
        user = auth_crud.get_user_by_id(db, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다")
        
        # OAuth 프로필 조회
        oauth_provider = get_oauth_provider(body.provider)
        profile = await oauth_provider.verify_and_get_profile(
            access_token=body.access_token,
            id_token=body.id_token
        )
        
        # Identity 생성 (이미 있으면 업데이트)
        existing_identity = auth_crud.get_identity(db, body.provider, profile.subject)
        if existing_identity:
            if existing_identity.user_id != user_id:
                raise HTTPException(status_code=409, detail="이 계정은 다른 사용자와 연결되어 있습니다")
            print(f"✅ 이미 연결된 계정: {body.provider}")
        else:
            auth_crud.create_identity(
                db,
                user_id=user_id,
                provider=body.provider,
                subject=profile.subject,
                email_verified=profile.email_verified,
                profile_name=profile.name,
                profile_picture=profile.picture,
                raw_profile=profile.raw_profile
            )
            print(f"✅ 외부 계정 연결: {body.provider}")
        
        # 사용자 정보 업데이트 (프로필 이미지 등)
        if not user.avatar_url and profile.picture:
            auth_crud.update_user(db, user_id, avatar_url=profile.picture)
        
        return {"status": "success", "message": f"{body.provider} 계정이 연결되었습니다"}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 계정 연결 실패: {e}")
        raise HTTPException(status_code=500, detail=f"계정 연결 실패: {str(e)}")


# ==================== 외부 계정 연결 해제 ====================

@router.post("/unlink")
async def unlink_identity(
    provider: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    외부 계정 연결 해제
    
    Headers:
        Authorization: Bearer {access_token}
    """
    try:
        # Authorization 헤더에서 토큰 추출
        authorization = request.headers.get("Authorization")
        if not authorization:
            raise HTTPException(status_code=401, detail="Authorization 헤더가 필요합니다")
        
        token = authorization.replace("Bearer ", "")
        user_id = jwt_service.get_user_id_from_token(token)
        
        if not user_id:
            raise HTTPException(status_code=401, detail="유효하지 않은 토큰입니다")
        
        # 사용자 확인
        user = auth_crud.get_user_by_id(db, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다")
        
        # 마지막 인증 수단 확인
        identities = auth_crud.get_user_identities(db, user_id)
        credential = auth_crud.get_credential(db, user_id)
        
        total_auth_methods = len(identities) + (1 if credential else 0)
        
        if total_auth_methods <= 1:
            raise HTTPException(
                status_code=400,
                detail="마지막 인증 수단은 해제할 수 없습니다. 먼저 비밀번호를 설정하세요."
            )
        
        # Identity 찾기
        identity_to_delete = None
        for identity in identities:
            if identity.provider == provider:
                identity_to_delete = identity
                break
        
        if not identity_to_delete:
            raise HTTPException(status_code=404, detail="연결된 계정을 찾을 수 없습니다")
        
        # Identity 삭제
        auth_crud.delete_identity(db, provider, identity_to_delete.subject)
        print(f"✅ 외부 계정 연결 해제: {provider}")
        
        return {"status": "success", "message": f"{provider} 계정 연결이 해제되었습니다"}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 계정 연결 해제 실패: {e}")
        raise HTTPException(status_code=500, detail=f"계정 연결 해제 실패: {str(e)}")


# ==================== 닉네임 설정 ====================
@router.post("/set-nickname")
async def set_nickname(
    body: SetNicknameRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    OAuth 가입 시 닉네임 미제공 사용자의 닉네임 설정
    
    Args:
        body: { user_id, nickname }
        
    Returns:
        200: { access_token, refresh_token, user }
    """
    try:
        # 사용자 확인
        user = auth_crud.get_user_by_id(db, body.user_id)
        if not user:
            raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다")
        
        # 닉네임 유효성 검사
        if not body.nickname or len(body.nickname.strip()) == 0:
            raise HTTPException(status_code=400, detail="닉네임을 입력해주세요")
        
        if len(body.nickname) > 20:
            raise HTTPException(status_code=400, detail="닉네임은 20자 이하로 입력해주세요")
        
        # 닉네임 업데이트
        user = auth_crud.update_user(
            db,
            user_id=body.user_id,
            display_name=body.nickname.strip()
        )
        
        print(f"✅ 닉네임 설정 완료: user_id={body.user_id}, nickname={body.nickname}")
        
        # 토큰 발급
        return issue_tokens(db, user, request)
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 닉네임 설정 실패: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"닉네임 설정 실패: {str(e)}")


# ==================== 비밀번호 설정 ====================

@router.post("/set-password")
async def set_password(
    body: SetPasswordRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    비밀번호 설정 (외부 로그인 사용자용)
    
    Headers:
        Authorization: Bearer {access_token}
    """
    try:
        # Authorization 헤더에서 토큰 추출
        authorization = request.headers.get("Authorization")
        if not authorization:
            raise HTTPException(status_code=401, detail="Authorization 헤더가 필요합니다")
        
        token = authorization.replace("Bearer ", "")
        user_id = jwt_service.get_user_id_from_token(token)
        
        if not user_id:
            raise HTTPException(status_code=401, detail="유효하지 않은 토큰입니다")
        
        # 사용자 확인
        user = auth_crud.get_user_by_id(db, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다")
        
        # 기존 비밀번호 확인
        existing_credential = auth_crud.get_credential(db, user_id)
        
        if existing_credential:
            # 비밀번호 업데이트
            auth_crud.update_password(db, user_id, body.password)
            print(f"✅ 비밀번호 업데이트: {user.email}")
            return {"status": "success", "message": "비밀번호가 변경되었습니다"}
        else:
            # 새 비밀번호 생성
            auth_crud.create_credential(db, user_id, body.password)
            print(f"✅ 비밀번호 설정: {user.email}")
            return {"status": "success", "message": "비밀번호가 설정되었습니다"}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 비밀번호 설정 실패: {e}")
        raise HTTPException(status_code=500, detail=f"비밀번호 설정 실패: {str(e)}")


# ==================== 토큰 갱신 ====================

@router.post("/refresh")
async def refresh_token_endpoint(
    refresh_token: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """리프레시 토큰으로 액세스 토큰 갱신"""
    try:
        # 토큰 검증
        payload = jwt_service.verify_token(refresh_token, token_type="refresh")
        if not payload:
            raise HTTPException(status_code=401, detail="유효하지 않은 리프레시 토큰입니다")
        
        user_id = payload.get("sub")
        
        # DB에서 토큰 확인
        token_record = auth_crud.get_refresh_token(db, refresh_token)
        if not token_record:
            raise HTTPException(status_code=401, detail="폐기되거나 만료된 토큰입니다")
        
        # 사용자 조회
        user = auth_crud.get_user_by_id(db, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다")
        
        # 기존 토큰 폐기
        auth_crud.revoke_refresh_token(db, refresh_token)
        
        # 새 토큰 발급
        return issue_tokens(db, user, request)
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 토큰 갱신 실패: {e}")
        raise HTTPException(status_code=500, detail=f"토큰 갱신 실패: {str(e)}")


# ==================== 로그아웃 ====================

@router.post("/logout")
async def logout_endpoint(
    body: LogoutRequest,
    db: Session = Depends(get_db)
):
    """로그아웃 (리프레시 토큰 폐기)"""
    try:
        if body.refresh_token:
            auth_crud.revoke_refresh_token(db, body.refresh_token)
            print(f"✅ 리프레시 토큰 폐기 완료")
        return {"status": "success", "message": "로그아웃되었습니다"}
    except Exception as e:
        print(f"❌ 로그아웃 실패: {e}")
        # 토큰 폐기 실패해도 로그아웃은 성공으로 처리
        return {"status": "success", "message": "로그아웃되었습니다"}


# ==================== 사용자 정보 조회 ====================

@router.get("/me")
async def get_current_user(
    request: Request,
    db: Session = Depends(get_db)
):
    """현재 로그인한 사용자 정보 조회"""
    try:
        # Authorization 헤더에서 토큰 추출
        authorization = request.headers.get("Authorization")
        if not authorization:
            raise HTTPException(status_code=401, detail="Authorization 헤더가 필요합니다")
        
        token = authorization.replace("Bearer ", "")
        user_id = jwt_service.get_user_id_from_token(token)
        
        if not user_id:
            raise HTTPException(status_code=401, detail="유효하지 않은 토큰입니다")
        
        # 사용자 조회
        user = auth_crud.get_user_by_id(db, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다")
        
        # 연결된 Identity 조회
        identities = auth_crud.get_user_identities(db, user_id)
        credential = auth_crud.get_credential(db, user_id)
        
        return {
            "user": user.to_dict(),
            "identities": [identity.to_dict() for identity in identities],
            "has_password": credential is not None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 사용자 정보 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"사용자 정보 조회 실패: {str(e)}")


# ==================== 관리자 엔드포인트 ====================

@router.get("/admin/user/{user_id}")
async def get_user_info_admin(
    user_id: int,
    db: Session = Depends(get_db)
):
    """관리자용 사용자 정보 조회 (개발/디버깅용)"""
    try:
        # 사용자 정보 조회
        user = auth_crud.get_user_by_id(db, user_id)
        if not user:
            raise HTTPException(status_code=404, detail=f"User ID {user_id}를 찾을 수 없습니다")
        
        # 구독 정보 조회
        from models.subscription import Subscription
        subscription = db.query(Subscription).filter(Subscription.user_id == user_id).first()
        
        result = {
            "user": user.to_dict(),
            "subscription": subscription.to_dict() if subscription else None
        }
        
        print(f"📋 관리자 조회 - User ID {user_id}:")
        print(f"   - 이메일: {user.email}")
        print(f"   - 이름: {user.display_name}")
        print(f"   - 플랜: {subscription.plan if subscription else 'None'}")
        print(f"   - 상태: {subscription.status if subscription else 'None'}")
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 관리자 사용자 정보 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"사용자 정보 조회 실패: {str(e)}")

