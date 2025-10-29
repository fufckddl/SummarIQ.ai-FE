"""
문의하기 스키마
"""
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class InquiryCreate(BaseModel):
    title: str
    content: str

class InquiryUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None

class InquiryResponse(BaseModel):
    id: int
    title: str
    content: str
    status: str
    status_display: str
    author_id: int
    author_name: Optional[str] = None
    admin_reply: Optional[str] = None
    admin_reply_at: Optional[str] = None
    admin_id: Optional[int] = None
    admin_name: Optional[str] = None
    is_active: bool
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

class InquiryAdminReply(BaseModel):
    admin_reply: str
    status: Optional[str] = None

class InquiryStatsResponse(BaseModel):
    total: int
    pending: int
    in_progress: int
    completed: int
