"""
팀 API 라우터
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel
import json

from database.connection import get_db
from utils.auth_dependency import get_current_user
from models.team import Team, TeamMember, TeamRole
from models.user import User
from models.notification import Notification, NotificationType, NotificationStatus
from models.team_meeting import TeamMeeting
from models.team_meeting_data import TeamAction, TeamDecision, TeamTag
from models.team_meeting_comment import TeamMeetingComment, TeamMeetingLike
from models.recording import Recording

router = APIRouter(prefix="/api/teams", tags=["teams"])

# ==================== Request Models ====================

class CreateTeamRequest(BaseModel):
    name: str
    description: Optional[str] = None
    is_public: bool = True
    allow_invites: bool = True

class UpdateTeamRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None

class AddMemberRequest(BaseModel):
    user_email: str
    role: str = "MEMBER"

# ==================== 팀 목록 조회 ====================

@router.get("/")
async def list_teams(
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """사용자가 속한 팀 목록 조회"""
    try:
        user_id = current_user["id"]
        
        # 사용자가 멤버인 팀 조회
        team_members = db.query(TeamMember).filter(TeamMember.user_id == user_id).all()
        team_ids = [tm.team_id for tm in team_members]
        
        if not team_ids:
            return {
                "teams": [],
                "message": "참여한 팀이 없습니다"
            }
        
        # 팀 정보 조회
        teams = db.query(Team).filter(Team.id.in_(team_ids)).all()
        
        result = []
        for team in teams:
            # 사용자의 역할 찾기
            user_member = next((tm for tm in team_members if tm.team_id == team.id), None)
            user_role = user_member.role.value if user_member else "MEMBER"
            
            print(f"🔍 팀 {team.name} - 사용자 역할: {user_role}")
            print(f"🔍 팀 {team.name} - user_member: {user_member}")
            if user_member:
                print(f"🔍 팀 {team.name} - user_member.role: {user_member.role}")
                print(f"🔍 팀 {team.name} - user_member.role.value: {user_member.role.value}")
            
            # 팀 멤버 수 조회
            member_count = db.query(TeamMember).filter(TeamMember.team_id == team.id).count()
            
            # 팀 멤버 정보 조회
            team_members = db.query(TeamMember).filter(TeamMember.team_id == team.id).all()
            print(f"🔍 팀 {team.id}의 멤버 수: {len(team_members)}")
            members = []
            for member in team_members:
                user = db.query(User).filter(User.id == member.user_id).first()
                print(f"🔍 멤버 {member.user_id}의 사용자 정보: {user}")
                if user:
                    print(f"🔍 사용자 이메일: {user.email}")
                    print(f"🔍 사용자 display_name: {user.display_name}")
                    members.append({
                        "id": user.id,
                        "email": user.email,
                        "display_name": user.display_name,
                        "avatar_url": user.avatar_url,
                        "role": member.role.value
                    })
            
            # 팀 회의 수 조회
            meeting_count = db.query(TeamMeeting).filter(
                TeamMeeting.team_id == team.id,
                TeamMeeting.is_active == True
            ).count()
            
            # 이번주 회의 수 조회 (이번주 월요일부터 현재까지)
            from datetime import datetime, timedelta
            today = datetime.now()
            # 이번주 월요일 구하기 (월요일이 0, 일요일이 6)
            days_since_monday = today.weekday()
            this_week_monday = today - timedelta(days=days_since_monday)
            this_week_monday = this_week_monday.replace(hour=0, minute=0, second=0, microsecond=0)
            
            weekly_meetings = db.query(TeamMeeting).filter(
                TeamMeeting.team_id == team.id,
                TeamMeeting.is_active == True,
                TeamMeeting.shared_at >= this_week_monday
            ).count()
            
            print(f"📊 팀 목록 - {team.name} 통계:")
            print(f"  - 멤버 수: {member_count}")
            print(f"  - 회의 수: {meeting_count}")
            print(f"  - 이번주 회의 수: {weekly_meetings}")
            
            result.append({
                "id": team.id,
                "name": team.name,
                "description": team.description,
                "role": user_role,
                "member_count": member_count,
                "meeting_count": meeting_count,
                "weekly_meetings": weekly_meetings,
                "members": members,
                "created_at": team.created_at.isoformat() if team.created_at else None,
                "updated_at": team.updated_at.isoformat() if team.updated_at else None
            })
        
        return {
            "teams": result,
            "total": len(result)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 팀 목록 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"팀 목록 조회 실패: {str(e)}")


@router.get("/{team_id}")
async def get_team_detail(
    team_id: int,
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """팀 상세 정보 조회"""
    try:
        user_id = current_user["id"]
        
        print(f"🔍 팀 상세 - 사용자 ID: {user_id}")
        print(f"🔍 팀 상세 - 팀 ID: {team_id}")
        
        # 팀 존재 여부 확인
        team = db.query(Team).filter(Team.id == team_id).first()
        if not team:
            raise HTTPException(status_code=404, detail="팀을 찾을 수 없습니다")
        
        # 사용자가 팀 멤버인지 확인
        user_member = db.query(TeamMember).filter(
            TeamMember.team_id == team_id,
            TeamMember.user_id == user_id
        ).first()
        
        print(f"🔍 팀 상세 - user_member: {user_member}")
        if user_member:
            print(f"🔍 팀 상세 - user_member.role: {user_member.role}")
            print(f"🔍 팀 상세 - user_member.role.value: {user_member.role.value}")
        
        if not user_member:
            raise HTTPException(status_code=403, detail="팀에 접근할 권한이 없습니다")
        
        # 팀 멤버 목록 조회
        team_members = db.query(TeamMember).filter(TeamMember.team_id == team_id).all()
        members = []
        
        for member in team_members:
            user = db.query(User).filter(User.id == member.user_id).first()
            if user:
                members.append({
                    "id": user.id,
                    "email": user.email,
                    "display_name": user.display_name,
                    "avatar_url": user.avatar_url,
                    "role": member.role.value,
                    "joined_at": member.joined_at.isoformat() if member.joined_at else None
                })
        
        # 팀 회의 목록 조회 (임시로 빈 배열)
        meetings = []
        
        # 사용자의 역할
        user_role = user_member.role.value
        print(f"🔍 팀 상세 - 최종 user_role: {user_role}")
        
        # 팀 통계 계산
        member_count = len(members)
        
        # 팀에 공유된 회의록 개수
        team_meetings = db.query(TeamMeeting).filter(
            TeamMeeting.team_id == team_id,
            TeamMeeting.is_active == True
        ).all()
        meeting_count = len(team_meetings)
        
        # 이번주 회의 개수 (이번주 월요일부터 현재까지)
        from datetime import datetime, timedelta
        today = datetime.now()
        # 이번주 월요일 구하기 (월요일이 0, 일요일이 6)
        days_since_monday = today.weekday()
        this_week_monday = today - timedelta(days=days_since_monday)
        this_week_monday = this_week_monday.replace(hour=0, minute=0, second=0, microsecond=0)
        
        weekly_meetings = db.query(TeamMeeting).filter(
            TeamMeeting.team_id == team_id,
            TeamMeeting.is_active == True,
            TeamMeeting.shared_at >= this_week_monday
        ).count()
        
        print(f"📊 팀 {team.name} 통계:")
        print(f"  - 멤버 수: {member_count}")
        print(f"  - 회의 수: {meeting_count}")
        print(f"  - 이번주 회의 수: {weekly_meetings}")
        print(f"  - 팀 회의록 레코드 수: {len(team_meetings)}")
        print(f"  - 이번주 월요일: {this_week_monday}")
        print(f"  - 현재 시간: {today}")
        
        response_data = {
            "id": team.id,
            "name": team.name,
            "description": team.description,
            "role": user_role,
            "member_count": member_count,
            "meeting_count": meeting_count,
            "weekly_meetings": weekly_meetings,
            "max_members": 5,  # 임시로 5명
            "members": members,
            "meetings": meetings,
            "created_at": team.created_at.isoformat() if team.created_at else None,
            "updated_at": team.updated_at.isoformat() if team.updated_at else None
        }
        
        print(f"🔍 팀 상세 - API 응답 데이터:")
        print(f"  - role: {response_data['role']}")
        print(f"  - user_role: {user_role}")
        
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 팀 상세 정보 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"팀 상세 정보 조회 실패: {str(e)}")


@router.post("/")
async def create_team(
    request: CreateTeamRequest,
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """새 팀 생성"""
    try:
        user_id = current_user["id"]
        
        # 팀 생성
        team = Team(
            name=request.name,
            description=request.description or "",
            owner_id=user_id,
            is_public=request.is_public,
            allow_invites=request.allow_invites
        )
        db.add(team)
        db.flush()  # ID 생성
        
        # 소유자를 팀 멤버로 추가
        team_member = TeamMember(
            team_id=team.id,
            user_id=user_id,
            role=TeamRole.OWNER
        )
        db.add(team_member)
        db.commit()
        db.refresh(team)
        
        print(f"✅ 팀 생성 성공: {team.name} (ID: {team.id})")
        
        return {
            "message": "팀이 성공적으로 생성되었습니다",
            "team": {
                "id": team.id,
                "name": team.name,
                "description": team.description,
                "role": "OWNER",
                "member_count": 1,
                "meeting_count": 0,
                "weekly_meetings": 0,
                "created_at": team.created_at.isoformat() if team.created_at else None
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 팀 생성 실패: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        raise HTTPException(status_code=500, detail=f"팀 생성 실패: {str(e)}")


@router.put("/{team_id}")
async def update_team(
    team_id: int,
    request: UpdateTeamRequest,
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """팀 정보 수정"""
    try:
        user_id = current_user["id"]
        
        # 팀 존재 여부 확인
        team = db.query(Team).filter(Team.id == team_id).first()
        if not team:
            raise HTTPException(status_code=404, detail="팀을 찾을 수 없습니다")
        
        # 사용자가 팀 소유자인지 확인
        if team.owner_id != user_id:
            raise HTTPException(status_code=403, detail="팀 정보를 수정할 권한이 없습니다")
        
        # 팀 정보 업데이트
        if request.name is not None:
            team.name = request.name
        if request.description is not None:
            team.description = request.description
        
        team.updated_at = datetime.now()
        db.commit()
        db.refresh(team)
        
        return {
            "message": "팀 정보가 성공적으로 수정되었습니다",
            "team": {
                "id": team.id,
                "name": team.name,
                "description": team.description,
                "updated_at": team.updated_at.isoformat()
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 팀 정보 수정 실패: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"팀 정보 수정 실패: {str(e)}")


@router.delete("/{team_id}")
async def delete_team(
    team_id: int,
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """팀 삭제"""
    try:
        user_id = current_user["id"]
        
        # 팀 존재 여부 확인
        team = db.query(Team).filter(Team.id == team_id).first()
        if not team:
            raise HTTPException(status_code=404, detail="팀을 찾을 수 없습니다")
        
        # 사용자가 팀 소유자인지 확인
        if team.owner_id != user_id:
            raise HTTPException(status_code=403, detail="팀을 삭제할 권한이 없습니다")
        
        # 팀 멤버 삭제
        db.query(TeamMember).filter(TeamMember.team_id == team_id).delete()
        
        # 팀 삭제
        db.delete(team)
        db.commit()
        
        return {
            "message": "팀이 성공적으로 삭제되었습니다"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 팀 삭제 실패: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"팀 삭제 실패: {str(e)}")


# ==================== 팀 멤버 관리 ====================

@router.get("/{team_id}/members")
async def get_team_members(
    team_id: int,
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """팀 멤버 목록 조회"""
    try:
        user_id = current_user["id"]
        
        # 팀 존재 여부 확인
        team = db.query(Team).filter(Team.id == team_id).first()
        if not team:
            raise HTTPException(status_code=404, detail="팀을 찾을 수 없습니다")
        
        # 사용자가 팀 멤버인지 확인
        user_member = db.query(TeamMember).filter(
            TeamMember.team_id == team_id,
            TeamMember.user_id == user_id
        ).first()
        
        if not user_member:
            raise HTTPException(status_code=403, detail="팀에 접근할 권한이 없습니다")
        
        # 팀 멤버 목록 조회
        team_members = db.query(TeamMember).filter(TeamMember.team_id == team_id).all()
        members = []
        
        for member in team_members:
            user = db.query(User).filter(User.id == member.user_id).first()
            if user:
                members.append({
                    "id": user.id,
                    "email": user.email,
                    "display_name": user.display_name,
                    "avatar_url": user.avatar_url,
                    "role": member.role.value,
                    "joined_at": member.joined_at.isoformat() if member.joined_at else None
                })
        
        return {
            "members": members,
            "total": len(members)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 팀 멤버 목록 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"팀 멤버 목록 조회 실패: {str(e)}")


@router.post("/{team_id}/members")
async def add_team_member(
    team_id: int,
    request: AddMemberRequest,
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """팀 멤버 추가"""
    try:
        user_id = current_user["id"]
        
        # 팀 존재 여부 확인
        team = db.query(Team).filter(Team.id == team_id).first()
        if not team:
            raise HTTPException(status_code=404, detail="팀을 찾을 수 없습니다")
        
        # 사용자가 팀 관리자인지 확인
        user_member = db.query(TeamMember).filter(
            TeamMember.team_id == team_id,
            TeamMember.user_id == user_id
        ).first()
        
        if not user_member or user_member.role not in [TeamRole.OWNER, TeamRole.ADMIN]:
            raise HTTPException(status_code=403, detail="팀 멤버를 추가할 권한이 없습니다")
        
        # 초대할 사용자 찾기
        invite_user = db.query(User).filter(User.email == request.user_email).first()
        if not invite_user:
            raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다")
        
        # 이미 팀 멤버인지 확인
        existing_member = db.query(TeamMember).filter(
            TeamMember.team_id == team_id,
            TeamMember.user_id == invite_user.id
        ).first()
        
        if existing_member:
            raise HTTPException(status_code=400, detail="이미 팀 멤버입니다")
        
        # 팀 멤버 추가
        team_member = TeamMember(
            team_id=team_id,
            user_id=invite_user.id,
            role=TeamRole(request.role)
        )
        db.add(team_member)
        db.commit()
        
        return {
            "message": "팀 멤버가 성공적으로 추가되었습니다",
            "member": {
                "id": invite_user.id,
                "email": invite_user.email,
                "display_name": invite_user.display_name,
                "role": request.role
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 팀 멤버 추가 실패: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"팀 멤버 추가 실패: {str(e)}")


@router.delete("/{team_id}/members/{member_id}")
async def remove_team_member(
    team_id: int,
    member_id: int,
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """팀 멤버 제거"""
    try:
        user_id = current_user["id"]
        
        # 팀 존재 여부 확인
        team = db.query(Team).filter(Team.id == team_id).first()
        if not team:
            raise HTTPException(status_code=404, detail="팀을 찾을 수 없습니다")
        
        # 사용자가 팀 관리자인지 확인
        user_member = db.query(TeamMember).filter(
            TeamMember.team_id == team_id,
            TeamMember.user_id == user_id
        ).first()
        
        if not user_member or user_member.role not in [TeamRole.OWNER, TeamRole.ADMIN]:
            raise HTTPException(status_code=403, detail="팀 멤버를 제거할 권한이 없습니다")
        
        # 제거할 멤버 확인
        target_member = db.query(TeamMember).filter(
            TeamMember.team_id == team_id,
            TeamMember.user_id == member_id
        ).first()
        
        if not target_member:
            raise HTTPException(status_code=404, detail="팀 멤버를 찾을 수 없습니다")
        
        # 소유자는 제거할 수 없음
        if target_member.role == TeamRole.OWNER:
            raise HTTPException(status_code=400, detail="팀 소유자는 제거할 수 없습니다")
        
        # 팀 멤버 제거
        db.delete(target_member)
        db.commit()
        
        return {
            "message": "팀 멤버가 성공적으로 제거되었습니다"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 팀 멤버 제거 실패: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"팀 멤버 제거 실패: {str(e)}")


class InviteTeamMemberRequest(BaseModel):
    invitee_email: str

@router.post("/{team_id}/invite")
async def invite_team_member(
    team_id: int,
    request: InviteTeamMemberRequest,
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """팀 멤버 초대"""
    try:
        user_id = current_user["id"]
        
        # 팀 존재 확인
        team = db.query(Team).filter(Team.id == team_id).first()
        if not team:
            raise HTTPException(status_code=404, detail="팀을 찾을 수 없습니다")
        
        # 팀 권한 확인 (팀 소유자 또는 관리자만 초대 가능)
        user_member = db.query(TeamMember).filter(
            TeamMember.team_id == team_id,
            TeamMember.user_id == user_id
        ).first()
        
        if not user_member or user_member.role not in [TeamRole.OWNER, TeamRole.ADMIN]:
            raise HTTPException(status_code=403, detail="팀 초대 권한이 없습니다")
        
        # 초대받을 사용자 확인
        invitee = db.query(User).filter(User.email == request.invitee_email).first()
        if not invitee:
            raise HTTPException(status_code=404, detail="해당 이메일의 사용자를 찾을 수 없습니다")
        
        # 이미 팀 멤버인지 확인
        existing_member = db.query(TeamMember).filter(
            TeamMember.team_id == team_id,
            TeamMember.user_id == invitee.id
        ).first()
        
        if existing_member:
            raise HTTPException(status_code=400, detail="이미 팀 멤버입니다")
        
        # 플랜별 팀 멤버 수 제한 확인
        from services.subscription_service import subscription_service
        current_member_count = db.query(TeamMember).filter(TeamMember.team_id == team_id).count()
        can_add = subscription_service.check_can_add_team_member(db, team.owner_id, current_member_count)
        
        if not can_add["allowed"]:
            raise HTTPException(
                status_code=403,
                detail=f"팀 초대 불가: {can_add['reason']}",
                headers={"X-Required-Plan": can_add.get("required_plan", "")}
            )
        
        # 초대자 정보
        inviter = db.query(User).filter(User.id == user_id).first()
        
        # 팀 초대 알림 생성
        notification = Notification(
            user_id=invitee.id,
            type=NotificationType.TEAM_INVITE,
            title="팀 초대",
            message=f"{team.name}에서 초대 요청을 보냈습니다.",
            data=json.dumps({
                "team_id": team_id,
                "team_name": team.name,
                "inviter_id": user_id,
                "inviter_name": inviter.display_name or inviter.email,
                "invitee_email": request.invitee_email
            }),
            status=NotificationStatus.PENDING
        )
        
        db.add(notification)
        db.commit()
        db.refresh(notification)
        
        print(f"✅ 팀 초대 알림 생성 완료: 팀 {team.name} -> {request.invitee_email}")
        
        return {
            "message": f"{request.invitee_email}에게 팀 초대 요청을 보냈습니다",
            "notification_id": notification.id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 팀 초대 실패: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"팀 초대 실패: {str(e)}")


class AcceptTeamInviteRequest(BaseModel):
    notification_id: int

@router.post("/{team_id}/accept-invite")
async def accept_team_invite(
    team_id: int,
    request: AcceptTeamInviteRequest,
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """팀 초대 수락"""
    try:
        user_id = current_user["id"]
        
        # 알림 확인
        notification = db.query(Notification).filter(
            Notification.id == request.notification_id,
            Notification.user_id == user_id,
            Notification.type == NotificationType.TEAM_INVITE
        ).first()
        
        if not notification:
            raise HTTPException(status_code=404, detail="초대 알림을 찾을 수 없습니다")
        
        # 팀 정보 확인
        team = db.query(Team).filter(Team.id == team_id).first()
        if not team:
            raise HTTPException(status_code=404, detail="팀을 찾을 수 없습니다")
        
        # 이미 팀 멤버인지 확인
        existing_member = db.query(TeamMember).filter(
            TeamMember.team_id == team_id,
            TeamMember.user_id == user_id
        ).first()
        
        if existing_member:
            raise HTTPException(status_code=400, detail="이미 팀 멤버입니다")
        
        # 플랜별 팀 멤버 수 제한 확인
        from services.subscription_service import subscription_service
        current_member_count = db.query(TeamMember).filter(TeamMember.team_id == team_id).count()
        can_add = subscription_service.check_can_add_team_member(db, team.owner_id, current_member_count)
        
        if not can_add["allowed"]:
            raise HTTPException(
                status_code=403,
                detail=f"팀 참여 불가: {can_add['reason']}",
                headers={"X-Required-Plan": can_add.get("required_plan", "")}
            )
        
        # 팀 멤버로 추가
        team_member = TeamMember(
            team_id=team_id,
            user_id=user_id,
            role=TeamRole.MEMBER
        )
        
        db.add(team_member)
        
        # 알림 상태 업데이트
        notification.status = NotificationStatus.ACCEPTED
        notification.is_read = True
        
        db.commit()
        
        print(f"✅ 팀 초대 수락 완료: 사용자 {user_id} -> 팀 {team.name}")
        
        return {
            "message": f"{team.name} 팀에 성공적으로 참여했습니다",
            "team": {
                "id": team.id,
                "name": team.name,
                "description": team.description
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 팀 초대 수락 실패: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"팀 초대 수락 실패: {str(e)}")


class RejectTeamInviteRequest(BaseModel):
    notification_id: int

@router.post("/{team_id}/reject-invite")
async def reject_team_invite(
    team_id: int,
    request: RejectTeamInviteRequest,
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """팀 초대 거절"""
    try:
        user_id = current_user["id"]
        
        # 알림 확인
        notification = db.query(Notification).filter(
            Notification.id == request.notification_id,
            Notification.user_id == user_id,
            Notification.type == NotificationType.TEAM_INVITE
        ).first()
        
        if not notification:
            raise HTTPException(status_code=404, detail="초대 알림을 찾을 수 없습니다")
        
        # 팀 정보 확인
        team = db.query(Team).filter(Team.id == team_id).first()
        if not team:
            raise HTTPException(status_code=404, detail="팀을 찾을 수 없습니다")
        
        # 알림 상태 업데이트
        notification.status = NotificationStatus.REJECTED
        notification.is_read = True
        
        db.commit()
        
        print(f"✅ 팀 초대 거절 완료: 사용자 {user_id} -> 팀 {team.name}")
        
        return {
            "message": f"{team.name} 팀 초대를 거절했습니다"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 팀 초대 거절 실패: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"팀 초대 거절 실패: {str(e)}")


class ShareMeetingRequest(BaseModel):
    meeting_id: str  # UUID

@router.post("/{team_id}/share-meeting")
async def share_meeting_to_team(
    team_id: int,
    request: ShareMeetingRequest,
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """팀에 회의록 공유"""
    try:
        user_id = current_user["id"]
        
        # 팀 존재 확인
        team = db.query(Team).filter(Team.id == team_id).first()
        if not team:
            raise HTTPException(status_code=404, detail="팀을 찾을 수 없습니다")
        
        # 팀 멤버 권한 확인
        user_member = db.query(TeamMember).filter(
            TeamMember.team_id == team_id,
            TeamMember.user_id == user_id
        ).first()
        
        if not user_member:
            raise HTTPException(status_code=403, detail="팀 멤버가 아닙니다")
        
        # 중복 공유 확인
        existing_share = db.query(TeamMeeting).filter(
            TeamMeeting.team_id == team_id,
            TeamMeeting.meeting_id == request.meeting_id,
            TeamMeeting.is_active == True
        ).first()
        
        if existing_share:
            raise HTTPException(status_code=400, detail="이미 해당 팀에 공유된 회의록입니다")
        
        # 원본 회의 데이터 조회
        from models.recording import Recording
        recording = db.query(Recording).filter(
            Recording.id == request.meeting_id
        ).first()
        
        if not recording:
            raise HTTPException(status_code=404, detail="회의 정보를 찾을 수 없습니다")
        
        # 팀 회의록 공유 기록 생성
        team_meeting = TeamMeeting(
            team_id=team_id,
            meeting_id=request.meeting_id,
            shared_by=user_id,
            is_active=True
        )
        
        db.add(team_meeting)
        db.commit()
        db.refresh(team_meeting)
        
        # 원본 회의의 액션 아이템과 결정사항 정보 로깅
        actions_data = recording.actions if hasattr(recording, 'actions') else recording.get('actions', []) if isinstance(recording, dict) else []
        summary_data = recording.summary if hasattr(recording, 'summary') else recording.get('summary', '') if isinstance(recording, dict) else ''
        participants_data = recording.participants if hasattr(recording, 'participants') else recording.get('participants', []) if isinstance(recording, dict) else []
        
        print(f"📋 원본 회의 액션 아이템: {actions_data}")
        print(f"📋 원본 회의 요약: {summary_data}")
        print(f"📋 원본 회의 참가자: {participants_data}")
        
        # 팀 회의 데이터 복사
        try:
            print(f"🔄 팀 회의 데이터 복사 시작: team_meeting_id={team_meeting.id}")
            await copy_meeting_data_to_team(team_meeting.id, recording, db)
            print(f"✅ 팀 회의 데이터 복사 완료")
        except Exception as e:
            print(f"❌ 팀 회의 데이터 복사 실패: {e}")
            import traceback
            traceback.print_exc()
        
        print(f"✅ 팀 회의록 공유 완료: 팀 {team.name} <- 회의록 {request.meeting_id}")
        
        return {
            "message": f"{team.name} 팀에 회의록이 공유되었습니다",
            "team_id": team_id,
            "meeting_id": request.meeting_id,
            "team_meeting_id": team_meeting.id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 팀 회의록 공유 실패: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"팀 회의록 공유 실패: {str(e)}")


@router.get("/{team_id}/meetings")
async def get_team_meetings(
    team_id: int,
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """팀에 공유된 회의록 목록 조회"""
    try:
        user_id = current_user["id"]
        
        # 팀 존재 확인
        team = db.query(Team).filter(Team.id == team_id).first()
        if not team:
            raise HTTPException(status_code=404, detail="팀을 찾을 수 없습니다")
        
        # 팀 멤버 권한 확인
        user_member = db.query(TeamMember).filter(
            TeamMember.team_id == team_id,
            TeamMember.user_id == user_id
        ).first()
        
        if not user_member:
            raise HTTPException(status_code=403, detail="팀 멤버가 아닙니다")
        
        # 팀에 공유된 회의록 조회
        team_meetings = db.query(TeamMeeting).filter(
            TeamMeeting.team_id == team_id
        ).all()
        
        print(f"🔍 팀 {team_id}의 회의록 개수: {len(team_meetings)}")
        for tm in team_meetings:
            print(f"🔍 팀 회의록: meeting_id={tm.meeting_id}, shared_by={tm.shared_by}")
        
        # 회의록 정보 구성
        from models.recording import Recording
        from models.tag import Tag, recording_tags
        
        meetings_data = []
        for tm in team_meetings:
            # 실제 회의록 데이터 가져오기 (UUID로 조회)
            recording = db.query(Recording).filter(Recording.id == tm.meeting_id).first()
            
            if not recording:
                print(f"⚠️ 녹음을 찾을 수 없음: recording_id={tm.meeting_id}")
                continue
            
            # 공유자 정보 가져오기
            sharer = db.query(User).filter(User.id == tm.shared_by).first()
            sharer_name = sharer.display_name if sharer and sharer.display_name else (sharer.email if sharer else 'Unknown')
            sharer_initial = sharer_name[0].upper() if sharer_name and sharer_name != 'Unknown' else '?'
            
            # 태그 정보 가져오기 (새로운 방식: recording_tags.tags JSON 필드 사용)
            from sqlalchemy import text as sql_text
            tag_query = sql_text("""
                SELECT tags 
                FROM recording_tags 
                WHERE recording_id = :recording_id
                LIMIT 1
            """)
            
            # recording 객체의 ID 가져오기 (더 안전한 처리)
            print(f"🔍 recording 객체 타입: {type(recording)}")
            if hasattr(recording, 'id'):
                recording_id = recording.id
            elif isinstance(recording, dict):
                recording_id = recording.get('id', '')
            else:
                recording_id = str(recording)
            print(f"🔍 recording_id: {recording_id}")
            
            result = db.execute(tag_query, {"recording_id": recording_id})
            row = result.fetchone()
            
            tags = []
            if row and row[0]:
                import json
                tags_data = json.loads(row[0])
                tags = [{"id": i, "name": tag["name"], "color": tag["color"]} for i, tag in enumerate(tags_data)]
                print(f"🏷️ 회의 {recording_id} 태그 개수: {len(tags)}")
                for tag in tags:
                    print(f"🏷️ 태그: {tag['name']} (색상: {tag['color']})")
            else:
                print(f"🏷️ 회의 {recording_id} 태그 없음")
            
            # 참가자 정보 가져오기
            participants = []
            if hasattr(recording, 'participants') and recording.participants:
                try:
                    participants = json.loads(recording.participants) if isinstance(recording.participants, str) else recording.participants
                except:
                    participants = []
            elif isinstance(recording, dict) and recording.get('participants'):
                try:
                    participants = json.loads(recording['participants']) if isinstance(recording['participants'], str) else recording['participants']
                except:
                    participants = []
            
            # 안전한 속성 접근
            title = recording.title if hasattr(recording, 'title') else recording.get('title', '') if isinstance(recording, dict) else ''
            summary = recording.summary if hasattr(recording, 'summary') else recording.get('summary', '') if isinstance(recording, dict) else ''
            duration = recording.duration if hasattr(recording, 'duration') else recording.get('duration', 0) if isinstance(recording, dict) else 0
            created_at = recording.created_at if hasattr(recording, 'created_at') else recording.get('created_at') if isinstance(recording, dict) else None
            
            meetings_data.append({
                "id": recording_id,  # 실제 UUID 사용
                "title": title or f"회의록 {recording_id[:8]}",
                "summary": summary or "",
                "duration": duration,  # 밀리초
                "date": created_at.isoformat() if created_at else "",
                "created_at": created_at.isoformat() if created_at else "",
                "participants": participants,
                "tags": tags,  # 이미 딕셔너리 형태로 구성됨
                "shared_by": tm.shared_by,
                "shared_by_name": sharer_name,
                "shared_by_initial": sharer_initial,
                "shared_at": tm.shared_at.isoformat()
            })
        
        print(f"✅ 팀 회의록 목록 조회 완료: 팀 {team.name} - {len(meetings_data)}개")
        
        return {
            "meetings": meetings_data,
            "total_count": len(meetings_data)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 팀 회의록 목록 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"팀 회의록 목록 조회 실패: {str(e)}")


# ==================== Helper Functions ====================

def get_team_meetings_by_recording_id(db: Session, recording_id: str) -> List[TeamMeeting]:
    """
    특정 회의 ID로 팀 회의록 조회
    
    Args:
        db: 데이터베이스 세션
        recording_id: 회의 ID (UUID 또는 정수)
        
    Returns:
        팀 회의록 목록
    """
    print(f"🔍 팀 회의록 조회: meeting_id={recording_id}")
    
    # 팀 회의록 테이블의 meeting_id를 UUID로 직접 조회
    # 현재 팀 회의록 테이블에는 정수 ID가 저장되어 있지만, 
    # 실제로는 UUID로 조회해야 함
    meeting_id_to_search = recording_id
    
    # 모든 팀 회의록 조회 (디버깅용)
    all_team_meetings = db.query(TeamMeeting).all()
    print(f"🔍 전체 팀 회의록 개수: {len(all_team_meetings)}")
    for tm in all_team_meetings:
        print(f"🔍 팀 회의록: team_id={tm.team_id}, meeting_id={tm.meeting_id}, is_active={tm.is_active}")
    
    # 조건에 맞는 팀 회의록 조회
    team_meetings = db.query(TeamMeeting).filter(
        TeamMeeting.meeting_id == meeting_id_to_search
    ).all()
    
    print(f"🔍 조건에 맞는 팀 회의록 개수: {len(team_meetings)}")
    return team_meetings


async def copy_meeting_data_to_team(team_meeting_id: int, recording, db: Session):
    """원본 회의 데이터를 팀 회의 테이블로 복사"""
    try:
        print(f"📋 팀 회의 데이터 복사 시작: team_meeting_id={team_meeting_id}")
        
        # 1. 액션 아이템 복사
        actions_data = recording.actions if hasattr(recording, 'actions') else recording.get('actions', []) if isinstance(recording, dict) else []
        print(f"📋 원본 회의 액션 데이터: {actions_data}")
        if actions_data:
            try:
                # Action 객체들을 직접 처리
                if isinstance(actions_data, list):
                    for i, action in enumerate(actions_data):
                        print(f"📋 액션 {i+1}: {action}")
                        # Action 객체의 속성에 직접 접근
                        content = action.task or ''
                        completed = action.completed or False
                        
                        team_action = TeamAction(
                            team_meeting_id=team_meeting_id,
                            content=content,
                            completed=completed
                        )
                        db.add(team_action)
                        print(f"📋 액션 아이템 {i+1} 추가됨: {content}")
                    print(f"📋 액션 아이템 {len(actions_data)}개 복사 완료")
                else:
                    print(f"📋 액션 데이터가 리스트가 아님: {type(actions_data)}")
            except Exception as e:
                print(f"📋 액션 아이템 복사 실패: {e}")
                import traceback
                traceback.print_exc()
        else:
            print("📋 원본 회의에 액션 아이템이 없음")
        
        # 2. 결정사항 복사 (액션 아이템과 동일하게 처리)
        if actions_data:
            try:
                if isinstance(actions_data, list):
                    for i, action in enumerate(actions_data):
                        # Action 객체의 속성에 직접 접근
                        content = action.task or ''
                        completed = action.completed or False
                        
                        team_decision = TeamDecision(
                            team_meeting_id=team_meeting_id,
                            content=content,
                            completed=completed
                        )
                        db.add(team_decision)
                    print(f"📋 결정사항 {len(actions_data)}개 복사 완료")
            except Exception as e:
                print(f"📋 결정사항 복사 실패: {e}")
                import traceback
                traceback.print_exc()
        
        # 3. 태그 복사 (새로운 방식)
        try:
            # recording 객체의 ID 가져오기
            recording_id = recording.id if hasattr(recording, 'id') else recording.get('id') if isinstance(recording, dict) else str(recording)
            print(f"📋 태그 복사 시작: recording.id = {recording_id}")
            
            # recording_tags 테이블에서 tags JSON 필드 조회
            from sqlalchemy import text as sql_text
            tag_query = sql_text("""
                SELECT tags 
                FROM recording_tags 
                WHERE recording_id = :recording_id
                LIMIT 1
            """)
            
            result = db.execute(tag_query, {"recording_id": recording_id})
            row = result.fetchone()
            
            if row and row[0]:
                import json
                tags_data = json.loads(row[0])
                print(f"📋 조회된 태그 개수: {len(tags_data)}")
                
                for i, tag in enumerate(tags_data):
                    print(f"📋 태그 {i+1}: {tag['name']} (색상: {tag['color']})")
                    team_tag = TeamTag(
                        team_meeting_id=team_meeting_id,
                        name=tag['name'],
                        color=tag['color']
                    )
                    db.add(team_tag)
                    print(f"📋 팀 태그 추가됨: {tag['name']}")
                
                print(f"📋 태그 {len(tags_data)}개 복사 완료")
            else:
                print("📋 원본 회의에 태그가 없음")
            
        except Exception as e:
            print(f"📋 태그 복사 실패: {e}")
            import traceback
            traceback.print_exc()
        
        db.commit()
        print(f"✅ 팀 회의 데이터 복사 완료")
        
    except Exception as e:
        print(f"❌ 팀 회의 데이터 복사 실패: {e}")
        db.rollback()
        raise

def get_team_members(db: Session, team_id: int) -> List[TeamMember]:
    """
    팀 멤버 목록 조회
    
    Args:
        db: 데이터베이스 세션
        team_id: 팀 ID
        
    Returns:
        팀 멤버 목록
    """
    print(f"🔍 팀 멤버 조회: team_id={team_id}")
    
    # TeamMember 모델의 실제 필드 확인
    team_members = db.query(TeamMember).filter(
        TeamMember.team_id == team_id
    ).all()
    
    print(f"🔍 조회된 팀 멤버 수: {len(team_members)}")
    for member in team_members:
        print(f"🔍 멤버 정보: id={member.id}, team_id={member.team_id}, user_id={member.user_id}, role={member.role}")
    
    return team_members


# 팀 회의 상세 조회 API
@router.get("/meetings/{meeting_id}")
async def get_team_meeting_detail(
    meeting_id: str,
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """팀 회의 상세 조회"""
    try:
        # 팀 회의 존재 확인
        team_meeting = db.query(TeamMeeting).filter(
            TeamMeeting.meeting_id == meeting_id
        ).first()
        
        if not team_meeting:
            raise HTTPException(status_code=404, detail="팀 회의를 찾을 수 없습니다")
        
        # 팀 멤버 권한 확인
        team_members = get_team_members(db, team_meeting.team_id)
        user_id = current_user.get("id")
        
        if not any(member.user_id == user_id for member in team_members):
            raise HTTPException(status_code=403, detail="팀 멤버만 조회할 수 있습니다")
        
        # 회의 정보 조회
        from models.recording import Recording
        recording = db.query(Recording).filter(
            Recording.id == meeting_id
        ).first()
        
        if not recording:
            raise HTTPException(status_code=404, detail="회의 정보를 찾을 수 없습니다")
        
        # 좋아요 수 조회
        from models.team_meeting_comment import TeamMeetingLike
        likes_count = db.query(TeamMeetingLike).filter(
            TeamMeetingLike.team_meeting_id == team_meeting.id
        ).count()
        
        # 현재 사용자의 좋아요 여부 확인
        is_liked = db.query(TeamMeetingLike).filter(
            TeamMeetingLike.team_meeting_id == team_meeting.id,
            TeamMeetingLike.user_id == user_id
        ).first() is not None
        
        # 팀 정보 조회
        team = db.query(Team).filter(Team.id == team_meeting.team_id).first()
        
        # 팀 회의 액션 아이템 조회
        team_actions = db.query(TeamAction).filter(
            TeamAction.team_meeting_id == team_meeting.id
        ).all()
        
        actions = [action.to_dict() for action in team_actions]
        print(f"📋 팀 회의 액션 아이템 {len(actions)}개 로드됨")
        
        # 팀 회의 결정사항 조회
        team_decisions = db.query(TeamDecision).filter(
            TeamDecision.team_meeting_id == team_meeting.id
        ).all()
        
        decisions = [decision.to_dict() for decision in team_decisions]
        print(f"📋 팀 회의 결정사항 {len(decisions)}개 로드됨")
        
        # 팀 회의 태그 조회
        team_tags = db.query(TeamTag).filter(
            TeamTag.team_meeting_id == team_meeting.id
        ).all()
        
        tags = [tag.to_dict() for tag in team_tags]
        print(f"📋 팀 회의 태그 {len(tags)}개 로드됨")
        
        # 안전한 속성 접근
        title = recording.title if hasattr(recording, 'title') else recording.get('title', '') if isinstance(recording, dict) else ''
        created_at = recording.created_at if hasattr(recording, 'created_at') else recording.get('created_at') if isinstance(recording, dict) else None
        duration = recording.duration if hasattr(recording, 'duration') else recording.get('duration', 0) if isinstance(recording, dict) else 0
        participants = recording.participants if hasattr(recording, 'participants') else recording.get('participants', []) if isinstance(recording, dict) else []
        summary = recording.summary if hasattr(recording, 'summary') else recording.get('summary', '') if isinstance(recording, dict) else ''
        transcript = recording.transcript if hasattr(recording, 'transcript') else recording.get('transcript', '') if isinstance(recording, dict) else ''
        audio_url = recording.audio_url if hasattr(recording, 'audio_url') else recording.get('audio_url', '') if isinstance(recording, dict) else ''
        
        print(f"🎵 팀 회의 상세 조회 - 오디오 정보:")
        print(f"   duration: {duration}ms")
        print(f"   audio_url: {audio_url}")
        print(f"   title: {title}")
        print(f"   recording 객체 타입: {type(recording)}")
        print(f"   recording.id: {recording.id if hasattr(recording, 'id') else 'N/A'}")
        
        # 오디오 URL이 없으면 기본 URL 생성
        if not audio_url:
            print("⚠️ audio_url이 비어있음, 기본 URL 생성 시도")
            # 기본 오디오 URL 생성 (실제 서버 URL 사용)
            import os
            server_base_url = os.getenv("SERVER_BASE_URL", "http://192.168.0.166:8000")
            audio_url = f"{server_base_url}/stt/audio/{recording.id if hasattr(recording, 'id') else meeting_id}"
            print(f"🔧 생성된 기본 audio_url: {audio_url}")
        
        return {
            "id": meeting_id,
            "title": title or "제목 없음",
            "date": created_at.strftime("%Y.%m.%d") if created_at else "",
            "duration": f"{duration // 60}분 {duration % 60}초" if duration else "0분",
            "participants": len(participants) if participants else 0,
            "status": "completed",
            "team": team.name if team else "알 수 없음",
            "teamColor": "#8B5CF6",
            "isShared": True,
            "isEditable": team_meeting.shared_by == user_id,
            "isSynchronized": True,
            "sharedBy": {
                "name": team_meeting.sharer.display_name if team_meeting.sharer else "알 수 없음",
                "initial": (team_meeting.sharer.display_name[0] if team_meeting.sharer and team_meeting.sharer.display_name else "?")[:1].upper(),
                "role": "소유자" if team_meeting.shared_by == user_id else "멤버",
                "timeAgo": f"{team_meeting.shared_at.strftime('%m월 %d일')}" if team_meeting.shared_at else "",
            },
            "viewers": {
                "count": len(team_members),
                "initials": [member.user.display_name[0] if member.user and member.user.display_name else "?" for member in team_members[:5]]
            },
            "likes": likes_count,
            "isLiked": is_liked,
            "listeners": len(team_members),
            "currentTime": "00:00",
            "totalTime": f"{duration // 60:02d}:{duration % 60:02d}" if duration else "00:00",
            "playbackSpeed": "1x",
            "audioUrl": audio_url,
            "durationMs": duration,
            "summary": summary or "회의 요약이 없습니다.",
            "transcript": transcript or "전체 텍스트가 없습니다.",
            "actions": actions,
            "decisions": decisions,
            "tags": tags,
            "comments": [],  # 댓글은 별도 API로 조회
            "alert": {
                "numbersToVerify": 2,
                "membersToVerify": 3,
            },
        }
        
    except Exception as e:
        print(f"❌ 팀 회의 상세 조회 실패: {e}")
        raise HTTPException(status_code=500, detail="팀 회의 상세 조회에 실패했습니다")


# 팀 회의 댓글 관련 API
@router.get("/meetings/{meeting_id}/comments")
async def get_team_meeting_comments(
    meeting_id: str,
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """팀 회의 댓글 조회"""
    try:
        # 팀 회의 존재 확인
        team_meeting = db.query(TeamMeeting).filter(
            TeamMeeting.meeting_id == meeting_id
        ).first()
        
        if not team_meeting:
            raise HTTPException(status_code=404, detail="팀 회의를 찾을 수 없습니다")
        
        # 팀 멤버 권한 확인
        team_members = get_team_members(db, team_meeting.team_id)
        user_id = current_user.get("id")
        
        if not any(member.user_id == user_id for member in team_members):
            raise HTTPException(status_code=403, detail="팀 멤버만 댓글을 조회할 수 있습니다")
        
        # 댓글 조회 (대댓글 포함)
        from models.team_meeting_comment import TeamMeetingComment
        comments = db.query(TeamMeetingComment).filter(
            TeamMeetingComment.team_meeting_id == team_meeting.id,
            TeamMeetingComment.parent_id.is_(None),  # 부모 댓글만
            TeamMeetingComment.is_deleted == False
        ).all()
        
        result = []
        for comment in comments:
            # 대댓글 조회
            replies = db.query(TeamMeetingComment).filter(
                TeamMeetingComment.parent_id == comment.id,
                TeamMeetingComment.is_deleted == False
            ).all()
            
            # 현재 사용자의 좋아요 상태 확인
            user_like = db.query(TeamMeetingLike).filter(
                TeamMeetingLike.team_meeting_id == team_meeting.id,
                TeamMeetingLike.user_id == user_id,
                TeamMeetingLike.comment_id == comment.id
            ).first()
            
            # 좋아요 수 조회
            likes_count = db.query(TeamMeetingLike).filter(
                TeamMeetingLike.team_meeting_id == team_meeting.id,
                TeamMeetingLike.comment_id == comment.id
            ).count()
            
            comment_data = {
                "id": comment.id,
                "user_id": comment.user_id,
                "user_name": comment.user.display_name if comment.user else "알 수 없음",
                "user_initial": (comment.user.display_name[0] if comment.user and comment.user.display_name else "?")[:1].upper(),
                "content": comment.content,
                "created_at": comment.created_at.isoformat(),
                "is_liked": user_like is not None,
                "likes_count": likes_count,
                "replies": [
                    {
                        "id": reply.id,
                        "user_id": reply.user_id,
                        "user_name": reply.user.display_name if reply.user else "알 수 없음",
                        "user_initial": (reply.user.display_name[0] if reply.user and reply.user.display_name else "?")[:1].upper(),
                        "content": reply.content,
                        "created_at": reply.created_at.isoformat(),
                    }
                    for reply in replies
                ]
            }
            result.append(comment_data)
        
        # 더미 데이터 제거 - 실제 댓글만 반환
        
        return result
        
    except Exception as e:
        print(f"❌ 댓글 조회 실패: {e}")
        raise HTTPException(status_code=500, detail="댓글 조회에 실패했습니다")


# 팀 회의 액션 아이템/결정사항/태그 수정 API
@router.put("/meetings/{meeting_id}/actions/{action_id}")
async def update_team_action(
    meeting_id: str,
    action_id: int,
    request: dict,
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """팀 회의 액션 아이템 수정"""
    try:
        # 팀 회의 존재 확인
        team_meeting = db.query(TeamMeeting).filter(
            TeamMeeting.meeting_id == meeting_id
        ).first()
        
        if not team_meeting:
            raise HTTPException(status_code=404, detail="팀 회의를 찾을 수 없습니다")
        
        # 팀 멤버 권한 확인
        team_members = get_team_members(db, team_meeting.team_id)
        user_id = current_user.get("id")
        
        if not any(member.user_id == user_id for member in team_members):
            raise HTTPException(status_code=403, detail="팀 멤버만 수정할 수 있습니다")
        
        # 액션 아이템 조회 및 수정
        action = db.query(TeamAction).filter(
            TeamAction.id == action_id,
            TeamAction.team_meeting_id == team_meeting.id
        ).first()
        
        if not action:
            raise HTTPException(status_code=404, detail="액션 아이템을 찾을 수 없습니다")
        
        # 액션 아이템 수정
        if 'content' in request:
            action.content = request['content']
        if 'completed' in request:
            action.completed = request['completed']
        
        action.updated_at = datetime.now()
        db.commit()
        
        return {"message": "액션 아이템이 수정되었습니다", "action": action.to_dict()}
        
    except Exception as e:
        print(f"❌ 액션 아이템 수정 실패: {e}")
        raise HTTPException(status_code=500, detail="액션 아이템 수정에 실패했습니다")


@router.put("/meetings/{meeting_id}/decisions/{decision_id}")
async def update_team_decision(
    meeting_id: str,
    decision_id: int,
    request: dict,
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """팀 회의 결정사항 수정"""
    try:
        # 팀 회의 존재 확인
        team_meeting = db.query(TeamMeeting).filter(
            TeamMeeting.meeting_id == meeting_id
        ).first()
        
        if not team_meeting:
            raise HTTPException(status_code=404, detail="팀 회의를 찾을 수 없습니다")
        
        # 팀 멤버 권한 확인
        team_members = get_team_members(db, team_meeting.team_id)
        user_id = current_user.get("id")
        
        if not any(member.user_id == user_id for member in team_members):
            raise HTTPException(status_code=403, detail="팀 멤버만 수정할 수 있습니다")
        
        # 결정사항 조회 및 수정
        decision = db.query(TeamDecision).filter(
            TeamDecision.id == decision_id,
            TeamDecision.team_meeting_id == team_meeting.id
        ).first()
        
        if not decision:
            raise HTTPException(status_code=404, detail="결정사항을 찾을 수 없습니다")
        
        # 결정사항 수정
        if 'content' in request:
            decision.content = request['content']
        if 'completed' in request:
            decision.completed = request['completed']
        
        decision.updated_at = datetime.now()
        db.commit()
        
        return {"message": "결정사항이 수정되었습니다", "decision": decision.to_dict()}
        
    except Exception as e:
        print(f"❌ 결정사항 수정 실패: {e}")
        raise HTTPException(status_code=500, detail="결정사항 수정에 실패했습니다")


@router.post("/meetings/{meeting_id}/view")
async def record_meeting_view(
    meeting_id: str,
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """회의 조회 기록 저장"""
    try:
        # 팀 회의 존재 확인
        team_meeting = db.query(TeamMeeting).filter(
            TeamMeeting.meeting_id == meeting_id
        ).first()
        
        if not team_meeting:
            raise HTTPException(status_code=404, detail="팀 회의를 찾을 수 없습니다")
        
        # 팀 멤버 권한 확인
        team_members = get_team_members(db, team_meeting.team_id)
        user_id = current_user.get("id")
        
        if not any(member.user_id == user_id for member in team_members):
            raise HTTPException(status_code=403, detail="팀 멤버만 조회할 수 있습니다")
        
        # 조회 기록 저장 (중복 방지)
        from sqlalchemy import text as sql_text
        insert_query = sql_text("""
            INSERT IGNORE INTO meeting_views (meeting_id, user_id, viewed_at)
            VALUES (:meeting_id, :user_id, NOW())
        """)
        
        db.execute(insert_query, {
            "meeting_id": meeting_id,
            "user_id": user_id
        })
        db.commit()
        
        return {"message": "조회 기록이 저장되었습니다"}
        
    except Exception as e:
        print(f"❌ 회의 조회 기록 저장 실패: {e}")
        raise HTTPException(status_code=500, detail="조회 기록 저장에 실패했습니다")


@router.get("/meetings/{meeting_id}/viewers")
async def get_meeting_viewers(
    meeting_id: str,
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """회의 조회자 목록 조회"""
    try:
        # 팀 회의 존재 확인
        team_meeting = db.query(TeamMeeting).filter(
            TeamMeeting.meeting_id == meeting_id
        ).first()
        
        if not team_meeting:
            raise HTTPException(status_code=404, detail="팀 회의를 찾을 수 없습니다")
        
        # 팀 멤버 권한 확인
        team_members = get_team_members(db, team_meeting.team_id)
        user_id = current_user.get("id")
        
        if not any(member.user_id == user_id for member in team_members):
            raise HTTPException(status_code=403, detail="팀 멤버만 조회자 목록을 볼 수 있습니다")
        
        # 조회자 목록 조회
        from sqlalchemy import text as sql_text
        viewers_query = sql_text("""
            SELECT 
                mv.user_id,
                u.display_name as user_name,
                SUBSTRING(u.display_name, 1, 1) as user_initial,
                mv.viewed_at
            FROM meeting_views mv
            JOIN users u ON mv.user_id = u.id
            WHERE mv.meeting_id = :meeting_id
            ORDER BY mv.viewed_at DESC
        """)
        
        result = db.execute(viewers_query, {"meeting_id": meeting_id})
        viewers = result.fetchall()
        
        # 시간 포맷팅
        formatted_viewers = []
        for viewer in viewers:
            from datetime import datetime
            viewed_at = viewer.viewed_at
            now = datetime.now()
            
            # 시간 차이 계산
            if viewed_at:
                diff = now - viewed_at
                diff_minutes = int(diff.total_seconds() / 60)
                diff_hours = int(diff.total_seconds() / 3600)
                diff_days = int(diff.total_seconds() / 86400)
                
                if diff_minutes < 1:
                    time_ago = "방금 전"
                elif diff_minutes < 60:
                    time_ago = f"{diff_minutes}분 전"
                elif diff_hours < 24:
                    time_ago = f"{diff_hours}시간 전"
                elif diff_days < 7:
                    time_ago = f"{diff_days}일 전"
                else:
                    time_ago = viewed_at.strftime("%m월 %d일")
            else:
                time_ago = "알 수 없음"
            
            formatted_viewers.append({
                "user_id": viewer.user_id,
                "user_name": viewer.user_name,
                "user_initial": viewer.user_initial.upper() if viewer.user_initial else "?",
                "viewed_at": time_ago
            })
        
        return {"viewers": formatted_viewers}
        
    except Exception as e:
        print(f"❌ 조회자 목록 조회 실패: {e}")
        raise HTTPException(status_code=500, detail="조회자 목록 조회에 실패했습니다")


@router.post("/meetings/{meeting_id}/comments/{comment_id}/like")
async def toggle_comment_like(
    meeting_id: str,
    comment_id: int,
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """댓글 좋아요 토글"""
    try:
        # 팀 회의 존재 확인
        team_meeting = db.query(TeamMeeting).filter(
            TeamMeeting.meeting_id == meeting_id
        ).first()
        
        if not team_meeting:
            raise HTTPException(status_code=404, detail="팀 회의를 찾을 수 없습니다")
        
        # 팀 멤버 권한 확인
        team_members = get_team_members(db, team_meeting.team_id)
        user_id = current_user.get("id")
        
        if not any(member.user_id == user_id for member in team_members):
            raise HTTPException(status_code=403, detail="팀 멤버만 좋아요를 누를 수 있습니다")
        
        # 댓글 존재 확인
        comment = db.query(TeamMeetingComment).filter(
            TeamMeetingComment.id == comment_id,
            TeamMeetingComment.team_meeting_id == team_meeting.id
        ).first()
        
        if not comment:
            raise HTTPException(status_code=404, detail="댓글을 찾을 수 없습니다")
        
        # 기존 좋아요 확인
        existing_like = db.query(TeamMeetingLike).filter(
            TeamMeetingLike.team_meeting_id == team_meeting.id,
            TeamMeetingLike.user_id == user_id,
            TeamMeetingLike.comment_id == comment_id
        ).first()
        
        if existing_like:
            # 좋아요 취소
            db.delete(existing_like)
            is_liked = False
        else:
            # 좋아요 추가
            new_like = TeamMeetingLike(
                team_meeting_id=team_meeting.id,
                user_id=user_id,
                comment_id=comment_id
            )
            db.add(new_like)
            is_liked = True
        
        db.commit()
        
        # 좋아요 수 조회
        likes_count = db.query(TeamMeetingLike).filter(
            TeamMeetingLike.team_meeting_id == team_meeting.id,
            TeamMeetingLike.comment_id == comment_id
        ).count()
        
        return {
            "is_liked": is_liked,
            "likes_count": likes_count
        }
        
    except Exception as e:
        print(f"❌ 댓글 좋아요 토글 실패: {e}")
        raise HTTPException(status_code=500, detail="댓글 좋아요 토글에 실패했습니다")


@router.post("/meetings/{meeting_id}/tags")
async def add_team_tag(
    meeting_id: str,
    request: dict,
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """팀 회의 태그 추가"""
    try:
        # 팀 회의 존재 확인
        team_meeting = db.query(TeamMeeting).filter(
            TeamMeeting.meeting_id == meeting_id
        ).first()
        
        if not team_meeting:
            raise HTTPException(status_code=404, detail="팀 회의를 찾을 수 없습니다")
        
        # 팀 멤버 권한 확인
        team_members = get_team_members(db, team_meeting.team_id)
        user_id = current_user.get("id")
        
        if not any(member.user_id == user_id for member in team_members):
            raise HTTPException(status_code=403, detail="팀 멤버만 수정할 수 있습니다")
        
        # 태그 추가
        team_tag = TeamTag(
            team_meeting_id=team_meeting.id,
            name=request.get('name', ''),
            color=request.get('color', '#8B5CF6')
        )
        
        db.add(team_tag)
        db.commit()
        db.refresh(team_tag)
        
        return {"message": "태그가 추가되었습니다", "tag": team_tag.to_dict()}
        
    except Exception as e:
        print(f"❌ 태그 추가 실패: {e}")
        raise HTTPException(status_code=500, detail="태그 추가에 실패했습니다")


@router.delete("/meetings/{meeting_id}/tags/{tag_id}")
async def delete_team_tag(
    meeting_id: str,
    tag_id: int,
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """팀 회의 태그 삭제"""
    try:
        # 팀 회의 존재 확인
        team_meeting = db.query(TeamMeeting).filter(
            TeamMeeting.meeting_id == meeting_id
        ).first()
        
        if not team_meeting:
            raise HTTPException(status_code=404, detail="팀 회의를 찾을 수 없습니다")
        
        # 팀 멤버 권한 확인
        team_members = get_team_members(db, team_meeting.team_id)
        user_id = current_user.get("id")
        
        if not any(member.user_id == user_id for member in team_members):
            raise HTTPException(status_code=403, detail="팀 멤버만 수정할 수 있습니다")
        
        # 태그 삭제
        tag = db.query(TeamTag).filter(
            TeamTag.id == tag_id,
            TeamTag.team_meeting_id == team_meeting.id
        ).first()
        
        if not tag:
            raise HTTPException(status_code=404, detail="태그를 찾을 수 없습니다")
        
        db.delete(tag)
        db.commit()
        
        return {"message": "태그가 삭제되었습니다"}
        
    except Exception as e:
        print(f"❌ 태그 삭제 실패: {e}")
        raise HTTPException(status_code=500, detail="태그 삭제에 실패했습니다")


@router.post("/meetings/{meeting_id}/comments")
async def add_team_meeting_comment(
    meeting_id: str,
    request: dict,
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """팀 회의 댓글 추가"""
    try:
        content = request.get("content", "").strip()
        parent_id = request.get("parent_id")
        
        if not content:
            raise HTTPException(status_code=400, detail="댓글 내용을 입력해주세요")
        
        # 팀 회의 존재 확인
        team_meeting = db.query(TeamMeeting).filter(
            TeamMeeting.meeting_id == meeting_id
        ).first()
        
        if not team_meeting:
            raise HTTPException(status_code=404, detail="팀 회의를 찾을 수 없습니다")
        
        # 팀 멤버 권한 확인
        team_members = get_team_members(db, team_meeting.team_id)
        user_id = current_user.get("id")
        
        if not any(member.user_id == user_id for member in team_members):
            raise HTTPException(status_code=403, detail="팀 멤버만 댓글을 작성할 수 있습니다")
        
        # 댓글 생성
        from models.team_meeting_comment import TeamMeetingComment
        comment = TeamMeetingComment(
            team_meeting_id=team_meeting.id,
            user_id=user_id,
            parent_id=parent_id,
            content=content
        )
        
        db.add(comment)
        db.commit()
        db.refresh(comment)
        
        return {
            "id": comment.id,
            "message": "댓글이 추가되었습니다"
        }
        
    except Exception as e:
        print(f"❌ 댓글 추가 실패: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="댓글 추가에 실패했습니다")


@router.post("/meetings/{meeting_id}/like")
async def toggle_team_meeting_like(
    meeting_id: str,
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """팀 회의 좋아요 토글"""
    try:
        user_id = current_user.get("id")
        
        # 팀 회의 존재 확인
        team_meeting = db.query(TeamMeeting).filter(
            TeamMeeting.meeting_id == meeting_id
        ).first()
        
        if not team_meeting:
            raise HTTPException(status_code=404, detail="팀 회의를 찾을 수 없습니다")
        
        # 팀 멤버 권한 확인
        team_members = get_team_members(db, team_meeting.team_id)
        
        if not any(member.user_id == user_id for member in team_members):
            raise HTTPException(status_code=403, detail="팀 멤버만 좋아요를 할 수 있습니다")
        
        # 기존 좋아요 확인
        from models.team_meeting_comment import TeamMeetingLike
        existing_like = db.query(TeamMeetingLike).filter(
            TeamMeetingLike.team_meeting_id == team_meeting.id,
            TeamMeetingLike.user_id == user_id
        ).first()
        
        if existing_like:
            # 좋아요 취소
            db.delete(existing_like)
            is_liked = False
        else:
            # 좋아요 추가
            like = TeamMeetingLike(
                team_meeting_id=team_meeting.id,
                user_id=user_id
            )
            db.add(like)
            is_liked = True
        
        db.commit()
        
        # 현재 좋아요 수 조회
        likes_count = db.query(TeamMeetingLike).filter(
            TeamMeetingLike.team_meeting_id == team_meeting.id
        ).count()
        
        return {
            "is_liked": is_liked,
            "likes_count": likes_count
        }
        
    except Exception as e:
        print(f"❌ 좋아요 토글 실패: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="좋아요 처리에 실패했습니다")
