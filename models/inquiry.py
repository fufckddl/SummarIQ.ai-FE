"""
문의하기 모델
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from models import Base
import enum

class InquiryStatus(enum.Enum):
    PENDING = "PENDING"      # 대기
    IN_PROGRESS = "IN_PROGRESS"  # 확인중
    COMPLETED = "COMPLETED"  # 확인완료

class Inquiry(Base):
    __tablename__ = 'inquiries'
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    status = Column(Enum(InquiryStatus), default=InquiryStatus.PENDING, nullable=False)
    
    # 작성자 정보
    author_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    
    # 관리자 답변 정보
    admin_reply = Column(Text, nullable=True)
    admin_reply_at = Column(DateTime(timezone=True), nullable=True)
    admin_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    
    # 메타데이터
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # 관계
    author = relationship("User", foreign_keys=[author_id], back_populates="inquiries")
    admin = relationship("User", foreign_keys=[admin_id])
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'content': self.content,
            'status': self.status.value if self.status else None,
            'status_display': self.get_status_display(),
            'author_id': self.author_id,
            'author_name': self.author.display_name if self.author else None,
            'admin_reply': self.admin_reply,
            'admin_reply_at': self.admin_reply_at.isoformat() if self.admin_reply_at else None,
            'admin_id': self.admin_id,
            'admin_name': self.admin.display_name if self.admin else None,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def get_status_display(self):
        status_map = {
            InquiryStatus.PENDING: '대기',
            InquiryStatus.IN_PROGRESS: '확인중',
            InquiryStatus.COMPLETED: '확인완료'
        }
        return status_map.get(self.status, '대기')
