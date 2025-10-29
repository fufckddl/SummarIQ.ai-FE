"""
팀 모델
"""
from sqlalchemy import Column, String, Integer, DateTime, Boolean, ForeignKey, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
from models import Base
import enum


class TeamRole(str, enum.Enum):
    """팀 역할"""
    OWNER = "OWNER"      # 팀 소유자
    ADMIN = "ADMIN"      # 관리자
    MEMBER = "MEMBER"    # 일반 멤버
    VIEWER = "VIEWER"    # 뷰어 (읽기 전용)


class Team(Base):
    """팀 테이블"""
    __tablename__ = "teams"
    
    # 기본 정보
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    description = Column(String(500), nullable=True)
    
    # 소유자
    owner_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    
    # 메타데이터
    is_active = Column(Boolean, default=True, nullable=False)
    is_invite = Column(Boolean, default=True, nullable=False)  # 초대 허용 여부
    
    # 타임스탬프
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)
    
    # 관계
    owner = relationship("User", foreign_keys=[owner_id], backref="owned_teams")
    members = relationship("TeamMember", back_populates="team", cascade="all, delete-orphan")
    recordings = relationship("Recording", back_populates="team")
    team_meetings = relationship("TeamMeeting", back_populates="team", cascade="all, delete-orphan")
    
    def to_dict(self, include_members=False):
        """딕셔너리 변환"""
        result = {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "owner_id": self.owner_id,
            "is_active": self.is_active,
            "is_invite": self.is_invite,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        
        if include_members:
            result["members"] = [m.to_dict() for m in self.members]
            result["member_count"] = len(self.members)
        
        return result


class TeamMember(Base):
    """팀 멤버 테이블 (중간 테이블)"""
    __tablename__ = "team_members"
    
    # 기본 정보
    id = Column(Integer, primary_key=True, autoincrement=True)
    team_id = Column(Integer, ForeignKey('teams.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    
    # 역할
    role = Column(Enum(TeamRole), default=TeamRole.MEMBER, nullable=False)
    
    # 타임스탬프
    joined_at = Column(DateTime, default=datetime.now, nullable=False)
    
    # 관계
    team = relationship("Team", back_populates="members")
    user = relationship("User", backref="team_memberships")
    
    def to_dict(self):
        """딕셔너리 변환"""
        return {
            "id": self.id,
            "team_id": self.team_id,
            "user_id": self.user_id,
            "role": self.role.value if isinstance(self.role, TeamRole) else self.role,
            "joined_at": self.joined_at.isoformat() if self.joined_at else None,
            "user": self.user.to_dict() if self.user else None,
        }

