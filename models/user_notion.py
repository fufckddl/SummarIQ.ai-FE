"""
Notion 연동 모델
"""
from sqlalchemy import Column, String, Integer, Text, DateTime, Enum, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from models import Base


class UserNotion(Base):
    """사용자별 Notion 연동 정보"""
    __tablename__ = "user_notion"
    
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    
    # OAuth 정보
    access_token_enc = Column(Text, nullable=False)
    workspace_id = Column(String(255))
    workspace_name = Column(String(255))
    bot_id = Column(String(255))
    
    # 기본 대상
    default_target_type = Column(Enum('database', 'page'), default='database')
    default_target_id = Column(String(255))
    default_target_name = Column(String(255))
    
    # 메타데이터
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)
    last_sync_at = Column(DateTime)
    
    # 관계
    user = relationship("User", back_populates="notion_connection")
    
    def to_dict(self):
        """딕셔너리로 변환 (토큰 제외)"""
        return {
            "userId": self.user_id,
            "workspaceId": self.workspace_id,
            "workspaceName": self.workspace_name,
            "defaultTargetType": self.default_target_type,
            "defaultTargetId": self.default_target_id,
            "defaultTargetName": self.default_target_name,
            "lastSyncAt": self.last_sync_at.isoformat() if self.last_sync_at else None,
            "connected": True
        }


class NotionUpload(Base):
    """Notion 업로드 이력"""
    __tablename__ = "notion_uploads"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    recording_id = Column(String(255), ForeignKey("recordings.id", ondelete="CASCADE"), nullable=False)
    
    # Notion 정보
    target_type = Column(Enum('database', 'page'), nullable=False)
    target_id = Column(String(255), nullable=False)
    notion_page_id = Column(String(255))
    notion_page_url = Column(Text)
    
    # 상태
    status = Column(Enum('pending', 'success', 'failed'), default='pending')
    error_message = Column(Text)
    
    # 메타데이터
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)
    
    def to_dict(self):
        """딕셔너리로 변환"""
        return {
            "id": self.id,
            "userId": self.user_id,
            "recordingId": self.recording_id,
            "targetType": self.target_type,
            "targetId": self.target_id,
            "notionPageId": self.notion_page_id,
            "notionPageUrl": self.notion_page_url,
            "status": self.status,
            "errorMessage": self.error_message,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
        }

