"""
SQLAlchemy 모델
"""
from sqlalchemy.ext.declarative import declarative_base

# Base 클래스 생성 (먼저 정의하여 다른 모델에서 import 가능하도록)
Base = declarative_base()

# 모든 모델 import (순서 중요: 의존성 순서대로)
# 1. User 관련 (User가 먼저)
from models.user import User
from models.identity import Identity
from models.credential import Credential
from models.refresh_token import RefreshToken

# 2. Recording 관련 (User를 참조하므로 나중에)
from models.recording import Recording
from models.segment import Segment
from models.decision import Decision
from models.action import Action

# 3. Notion 연동
from models.user_notion import UserNotion, NotionUpload

# 4. 팀 관련
from models.team import Team, TeamMember, TeamRole
from models.team_meeting import TeamMeeting
from models.team_meeting_data import TeamAction, TeamDecision, TeamTag
from models.team_meeting_comment import TeamMeetingComment, TeamMeetingLike

# 5. 구독 관련
from models.subscription import Subscription

# 6. 알림 관련
from models.notification import Notification, NotificationType, NotificationStatus

# 7. 공지사항 관련
from models.announcement import Announcement

# 8. 문의하기 관련
from models.inquiry import Inquiry, InquiryStatus

__all__ = [
    "Base",
    "User",
    "Identity",
    "Credential",
    "RefreshToken",
    "Recording",
    "Segment",
    "Decision",
    "Action",
    "UserNotion",
    "NotionUpload",
    "Team",
    "TeamMember",
    "TeamRole",
    "TeamMeeting",
    "TeamAction",
    "TeamDecision",
    "TeamTag",
    "TeamMeetingComment",
    "TeamMeetingLike",
    "Subscription",
    "Notification",
    "NotificationType",
    "NotificationStatus",
    "Announcement",
    "Inquiry",
    "InquiryStatus",
]

