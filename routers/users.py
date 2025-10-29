"""
사용자 정보 API 라우터
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Optional
from datetime import datetime
from pydantic import BaseModel

from database.connection import get_db
from utils.auth_dependency import get_current_user
from models.user import User
from models.subscription import Subscription
from models.identity import Identity
from models.credential import Credential

router = APIRouter(prefix="/api/users", tags=["users"])


# ==================== Pydantic 모델 ====================

class UpdateProfileRequest(BaseModel):
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None


class UpdatePasswordRequest(BaseModel):
    current_password: str
    new_password: str

# ==================== 사용자 정보 조회 ====================

@router.get("/me")
async def get_current_user_info(
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """현재 로그인한 사용자의 상세 정보 조회"""
    try:
        user_id = current_user["id"]
        
        # 사용자 기본 정보 조회
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다")
        
        # 구독 정보 조회
        subscription = db.query(Subscription).filter(Subscription.user_id == user_id).first()
        
        # Identity 정보 조회
        identities = db.query(Identity).filter(Identity.user_id == user_id).all()
        
        # Credential 정보 조회
        credential = db.query(Credential).filter(Credential.user_id == user_id).first()
        
        return {
            "id": user.id,
            "email": user.email,
            "display_name": user.display_name,
            "avatar_url": user.avatar_url,
            "email_verified": user.email_verified,
            "locale": user.locale,
            "created_via": user.created_via,
            "push_enabled": user.push_enabled,
            "audio_quality_enabled": user.audio_quality_enabled,
            "audio_quality_settings": user.audio_quality_settings,
            "is_admin": user.is_admin,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "updated_at": user.updated_at.isoformat() if user.updated_at else None,
            "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
            "subscription": {
                "id": subscription.id,
                "plan": subscription.plan.value if subscription else "FREE",
                "status": subscription.status.value if subscription else "ACTIVE",
                "started_at": subscription.started_at.isoformat() if subscription and subscription.started_at else None,
                "expires_at": subscription.expires_at.isoformat() if subscription and subscription.expires_at else None,
                "created_at": subscription.created_at.isoformat() if subscription else None
            } if subscription else {
                "plan": "FREE",
                "status": "ACTIVE",
                "started_at": None,
                "expires_at": None,
                "created_at": None
            },
            "identities": [{
                "id": identity.id,
                "provider": identity.provider,
                "subject": identity.subject,
                "email_verified": identity.email_verified,
                "profile_name": identity.profile_name,
                "profile_picture": identity.profile_picture,
                "created_at": identity.created_at.isoformat() if identity.created_at else None
            } for identity in identities],
            "has_password": credential is not None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 사용자 정보 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"사용자 정보 조회 실패: {str(e)}")


@router.get("/profile")
async def get_user_profile(
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """사용자 프로필 정보 조회 (간단한 정보만)"""
    try:
        user_id = current_user["id"]
        
        # 사용자 기본 정보 조회
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다")
        
        # 구독 정보 조회
        subscription = db.query(Subscription).filter(Subscription.user_id == user_id).first()
        
        return {
            "id": user.id,
            "email": user.email,
            "display_name": user.display_name,
            "avatar_url": user.avatar_url,
            "plan": subscription.plan.value if subscription else "FREE",
            "created_at": user.created_at.isoformat() if user.created_at else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 사용자 프로필 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"사용자 프로필 조회 실패: {str(e)}")


@router.get("/subscription")
async def get_user_subscription(
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """사용자 구독 정보 조회"""
    try:
        user_id = current_user["id"]
        
        # 구독 정보 조회
        subscription = db.query(Subscription).filter(Subscription.user_id == user_id).first()
        
        if not subscription:
            return {
                "plan": "FREE",
                "status": "ACTIVE",
                "started_at": None,
                "expires_at": None,
                "created_at": None
            }
        
        return {
            "id": subscription.id,
            "user_id": subscription.user_id,
            "plan": subscription.plan.value,
            "status": subscription.status.value,
            "started_at": subscription.started_at.isoformat() if subscription.started_at else None,
            "expires_at": subscription.expires_at.isoformat() if subscription.expires_at else None,
            "cancelled_at": subscription.cancelled_at.isoformat() if subscription.cancelled_at else None,
            "payment_provider": subscription.payment_provider,
            "created_at": subscription.created_at.isoformat() if subscription.created_at else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 구독 정보 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"구독 정보 조회 실패: {str(e)}")


@router.put("/profile")
async def update_user_profile(
    request: UpdateProfileRequest,
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """사용자 프로필 정보 업데이트"""
    try:
        user_id = current_user["id"]
        
        # 사용자 조회
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다")
        
        # 업데이트할 필드만 수정
        if request.display_name is not None:
            # 닉네임 검증
            if len(request.display_name.strip()) == 0:
                raise HTTPException(status_code=400, detail="닉네임은 공백일 수 없습니다")
            user.display_name = request.display_name.strip()
        
        if request.avatar_url is not None:
            user.avatar_url = request.avatar_url
        
        user.updated_at = datetime.now()
        
        db.commit()
        db.refresh(user)
        
        return {
            "id": user.id,
            "email": user.email,
            "display_name": user.display_name,
            "avatar_url": user.avatar_url,
            "updated_at": user.updated_at.isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 프로필 업데이트 실패: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"프로필 업데이트 실패: {str(e)}")


@router.put("/password")
async def update_password(
    request: UpdatePasswordRequest,
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """사용자 비밀번호 변경"""
    try:
        import bcrypt
        
        user_id = current_user["id"]
        
        # 사용자 조회
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다")
        
        # Credential 조회
        credential = db.query(Credential).filter(Credential.user_id == user_id).first()
        if not credential:
            raise HTTPException(status_code=400, detail="비밀번호가 설정되지 않았습니다")
        
        # 현재 비밀번호 확인
        if not bcrypt.checkpw(request.current_password.encode('utf-8'), credential.hashed_password.encode('utf-8')):
            raise HTTPException(status_code=400, detail="현재 비밀번호가 일치하지 않습니다")
        
        # 새 비밀번호 검증
        if len(request.new_password) < 8:
            raise HTTPException(status_code=400, detail="비밀번호는 8자 이상이어야 합니다")
        
        # 새 비밀번호 해싱
        hashed_password = bcrypt.hashpw(request.new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        # 비밀번호 업데이트
        credential.hashed_password = hashed_password
        credential.updated_at = datetime.now()
        
        user.updated_at = datetime.now()
        
        db.commit()
        
        return {
            "message": "비밀번호가 변경되었습니다"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 비밀번호 변경 실패: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"비밀번호 변경 실패: {str(e)}")


# ==================== 관리자 엔드포인트 ====================

@router.get("/admin/{user_id}")
async def get_user_info_admin(
    user_id: int,
    db: Session = Depends(get_db)
):
    """관리자용 사용자 정보 조회 (개발/디버깅용)"""
    try:
        # 사용자 정보 조회
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail=f"User ID {user_id}를 찾을 수 없습니다")
        
        # 구독 정보 조회
        subscription = db.query(Subscription).filter(Subscription.user_id == user_id).first()
        
        # Identity 정보 조회
        identities = db.query(Identity).filter(Identity.user_id == user_id).all()
        
        return {
            "user": {
                "id": user.id,
                "email": user.email,
                "display_name": user.display_name,
                "avatar_url": user.avatar_url,
                "email_verified": user.email_verified,
                "locale": user.locale,
                "created_via": user.created_via,
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None
            },
            "subscription": {
                "id": subscription.id,
                "plan": subscription.plan.value,
                "status": subscription.status.value,
                "started_at": subscription.started_at.isoformat() if subscription.started_at else None,
                "expires_at": subscription.expires_at.isoformat() if subscription.expires_at else None,
                "created_at": subscription.created_at.isoformat() if subscription else None
            } if subscription else None,
            "identities": [{
                "id": identity.id,
                "provider": identity.provider,
                "subject": identity.subject,
                "profile_name": identity.profile_name,
                "created_at": identity.created_at.isoformat() if identity.created_at else None
            } for identity in identities]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 관리자 사용자 정보 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"사용자 정보 조회 실패: {str(e)}")
