"""
인증 시스템 CRUD 작업
"""
from sqlalchemy.orm import Session
from typing import Optional, List, Dict
from datetime import datetime, timedelta
import uuid
import hashlib

from models.user import User
from models.identity import Identity
from models.credential import Credential
from models.refresh_token import RefreshToken


# ==================== User CRUD ====================

def create_user(
    db: Session,
    email: Optional[str] = None,
    email_verified: bool = False,
    display_name: Optional[str] = None,
    avatar_url: Optional[str] = None,
    locale: str = "ko-KR",
    created_via: str = "local"
) -> User:
    """사용자 생성"""
    user = User(
        email=email,
        email_verified=email_verified,
        display_name=display_name,
        avatar_url=avatar_url,
        locale=locale,
        created_via=created_via,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return user


def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    """ID로 사용자 조회"""
    return db.query(User).filter(User.id == user_id).first()


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """이메일로 사용자 조회"""
    return db.query(User).filter(User.email == email).first()


def update_user(db: Session, user_id: int, **kwargs) -> Optional[User]:
    """사용자 정보 업데이트"""
    user = get_user_by_id(db, user_id)
    if not user:
        return None
    
    for key, value in kwargs.items():
        if hasattr(user, key):
            setattr(user, key, value)
    
    user.updated_at = datetime.now()
    db.commit()
    db.refresh(user)
    
    return user


def update_last_login(db: Session, user_id: int):
    """마지막 로그인 시간 업데이트"""
    user = get_user_by_id(db, user_id)
    if user:
        user.last_login_at = datetime.now()
        db.commit()


# ==================== Identity CRUD ====================

def create_identity(
    db: Session,
    user_id: int,
    provider: str,
    subject: str,
    email_verified: Optional[bool] = None,
    profile_name: Optional[str] = None,
    profile_picture: Optional[str] = None,
    raw_profile: Optional[Dict] = None
) -> Identity:
    """외부 인증 연동 생성"""
    identity = Identity(
        user_id=user_id,
        provider=provider,
        subject=subject,
        email_verified=email_verified,
        profile_name=profile_name,
        profile_picture=profile_picture,
        raw_profile=raw_profile,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    
    db.add(identity)
    db.commit()
    db.refresh(identity)
    
    return identity


def get_identity(db: Session, provider: str, subject: str) -> Optional[Identity]:
    """provider + subject로 Identity 조회"""
    return db.query(Identity).filter(
        Identity.provider == provider,
        Identity.subject == subject
    ).first()


def get_user_identities(db: Session, user_id: int) -> List[Identity]:
    """사용자의 모든 Identity 조회"""
    return db.query(Identity).filter(Identity.user_id == user_id).all()


def delete_identity(db: Session, provider: str, subject: str) -> bool:
    """Identity 삭제 (연동 해제)"""
    identity = get_identity(db, provider, subject)
    if not identity:
        return False
    
    db.delete(identity)
    db.commit()
    return True


# ==================== Credential CRUD ====================

def create_credential(db: Session, user_id: int, password: str) -> Credential:
    """비밀번호 인증 정보 생성"""
    import bcrypt
    
    password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    credential = Credential(
        user_id=user_id,
        password_hash=password_hash,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    
    db.add(credential)
    db.commit()
    db.refresh(credential)
    
    return credential


def get_credential(db: Session, user_id: int) -> Optional[Credential]:
    """사용자의 비밀번호 인증 정보 조회"""
    return db.query(Credential).filter(Credential.user_id == user_id).first()


def verify_password(db: Session, user_id: int, password: str) -> bool:
    """비밀번호 검증"""
    import bcrypt
    
    credential = get_credential(db, user_id)
    if not credential:
        return False
    
    return bcrypt.checkpw(password.encode('utf-8'), credential.password_hash.encode('utf-8'))


def update_password(db: Session, user_id: int, new_password: str) -> bool:
    """비밀번호 업데이트"""
    import bcrypt
    
    credential = get_credential(db, user_id)
    if not credential:
        return False
    
    password_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    credential.password_hash = password_hash
    credential.updated_at = datetime.now()
    
    db.commit()
    return True


# ==================== RefreshToken CRUD ====================

def create_refresh_token(
    db: Session,
    user_id: int,
    token: str,
    family_id: str,
    device_info: Optional[str] = None,
    ip_address: Optional[str] = None,
    expires_days: int = 30
) -> RefreshToken:
    """리프레시 토큰 생성"""
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    
    refresh_token = RefreshToken(
        user_id=user_id,
        token_hash=token_hash,
        family_id=family_id,
        device_info=device_info,
        ip_address=ip_address,
        expires_at=datetime.now() + timedelta(days=expires_days),
        revoked=False,
        created_at=datetime.now()
    )
    
    db.add(refresh_token)
    db.commit()
    db.refresh(refresh_token)
    
    return refresh_token


def get_refresh_token(db: Session, token: str) -> Optional[RefreshToken]:
    """토큰으로 리프레시 토큰 조회"""
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    return db.query(RefreshToken).filter(
        RefreshToken.token_hash == token_hash,
        RefreshToken.revoked == False,
        RefreshToken.expires_at > datetime.now()
    ).first()


def revoke_refresh_token(db: Session, token: str) -> bool:
    """리프레시 토큰 폐기"""
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    refresh_token = db.query(RefreshToken).filter(
        RefreshToken.token_hash == token_hash
    ).first()
    
    if not refresh_token:
        return False
    
    refresh_token.revoked = True
    db.commit()
    return True


def revoke_user_tokens(db: Session, user_id: int):
    """사용자의 모든 토큰 폐기"""
    db.query(RefreshToken).filter(RefreshToken.user_id == user_id).update({"revoked": True})
    db.commit()


def cleanup_expired_tokens(db: Session):
    """만료된 토큰 정리"""
    db.query(RefreshToken).filter(RefreshToken.expires_at < datetime.now()).delete()
    db.commit()

