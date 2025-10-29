"""
Notion 연동 CRUD
"""
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime

from models.user_notion import UserNotion, NotionUpload


# ==================== UserNotion CRUD ====================

def create_or_update_notion_connection(
    db: Session,
    user_id: int,
    access_token_enc: str,
    workspace_id: str = None,
    workspace_name: str = None,
    bot_id: str = None
) -> UserNotion:
    """Notion 연동 정보 생성 또는 업데이트"""
    
    existing = db.query(UserNotion).filter(UserNotion.user_id == user_id).first()
    
    if existing:
        # 업데이트
        existing.access_token_enc = access_token_enc
        existing.workspace_id = workspace_id
        existing.workspace_name = workspace_name
        existing.bot_id = bot_id
        existing.updated_at = datetime.now()
        existing.last_sync_at = datetime.now()
        db.commit()
        db.refresh(existing)
        return existing
    else:
        # 새로 생성
        connection = UserNotion(
            user_id=user_id,
            access_token_enc=access_token_enc,
            workspace_id=workspace_id,
            workspace_name=workspace_name,
            bot_id=bot_id,
            last_sync_at=datetime.now()
        )
        db.add(connection)
        db.commit()
        db.refresh(connection)
        return connection


def update_notion_default_target(
    db: Session,
    user_id: int,
    default_target_type: str,
    default_target_id: str,
    default_target_name: str
) -> UserNotion:
    """Notion 기본 대상 업데이트"""
    
    connection = db.query(UserNotion).filter(UserNotion.user_id == user_id).first()
    if not connection:
        raise ValueError(f"User {user_id}의 Notion 연결 정보를 찾을 수 없습니다")
    
    connection.default_target_type = default_target_type
    connection.default_target_id = default_target_id
    connection.default_target_name = default_target_name
    
    db.commit()
    db.refresh(connection)
    
    return connection


def get_notion_connection(db: Session, user_id: int) -> Optional[UserNotion]:
    """Notion 연동 정보 조회"""
    return db.query(UserNotion).filter(UserNotion.user_id == user_id).first()


def update_default_target(
    db: Session,
    user_id: int,
    target_type: str,
    target_id: str,
    target_name: str = None
) -> bool:
    """기본 업로드 대상 설정"""
    connection = get_notion_connection(db, user_id)
    if not connection:
        return False
    
    connection.default_target_type = target_type
    connection.default_target_id = target_id
    connection.default_target_name = target_name
    connection.updated_at = datetime.now()
    
    db.commit()
    return True


def delete_notion_connection(db: Session, user_id: int) -> bool:
    """Notion 연동 해제"""
    connection = get_notion_connection(db, user_id)
    if not connection:
        return False
    
    db.delete(connection)
    db.commit()
    return True


# ==================== NotionUpload CRUD ====================

def create_notion_upload(
    db: Session,
    user_id: int,
    recording_id: str,
    target_type: str,
    target_id: str,
    notion_page_id: str = None,
    notion_page_url: str = None,
    status: str = 'pending'
) -> NotionUpload:
    """Notion 업로드 이력 생성"""
    upload = NotionUpload(
        user_id=user_id,
        recording_id=recording_id,
        target_type=target_type,
        target_id=target_id,
        notion_page_id=notion_page_id,
        notion_page_url=notion_page_url,
        status=status
    )
    
    db.add(upload)
    db.commit()
    db.refresh(upload)
    
    return upload


def update_notion_upload_status(
    db: Session,
    upload_id: int,
    status: str,
    notion_page_id: str = None,
    notion_page_url: str = None,
    error_message: str = None
) -> bool:
    """업로드 상태 업데이트"""
    upload = db.query(NotionUpload).filter(NotionUpload.id == upload_id).first()
    if not upload:
        return False
    
    upload.status = status
    if notion_page_id:
        upload.notion_page_id = notion_page_id
    if notion_page_url:
        upload.notion_page_url = notion_page_url
    if error_message:
        upload.error_message = error_message
    upload.updated_at = datetime.now()
    
    db.commit()
    return True


def get_recording_notion_upload(db: Session, recording_id: str) -> Optional[NotionUpload]:
    """녹음의 Notion 업로드 이력 조회"""
    return db.query(NotionUpload).filter(
        NotionUpload.recording_id == recording_id
    ).order_by(NotionUpload.created_at.desc()).first()

