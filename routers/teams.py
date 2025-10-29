"""
팀 관리 API 라우터
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import List, Optional, Dict
from datetime import datetime, timedelta

from database.connection import get_db
from utils.auth_dependency import get_current_user
from models.team import Team, TeamMember, TeamRole
from models.user import User
from models.recording import Recording

router = APIRouter(prefix="/api/teams", tags=["teams"])

# ==================== Pydantic 모델 ====================

class TeamCreate(BaseModel):
    name: str
    description: Optional[str] = None
    is_invite: Optional[bool] = True  # 초대 허용 여부

class TeamUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_invite: Optional[bool] = None

class MemberAdd(BaseModel):
    user_email: str
    role: str = "member"  # owner, admin, member, viewer

class MemberRoleUpdate(BaseModel):
    role: str  # owner, admin, member, viewer

class RecordingShare(BaseModel):
    recording_id: str
    team_id: int

# ==================== API 엔드포인트 ====================

@router.post("/")
async def create_team(
    team_data: TeamCreate,
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    새 팀 생성 (구독 플랜 확인)
    """
    user_id = current_user["id"]
    
    # 구독 플랜 확인
    from services.subscription_service import subscription_service
    can_create = subscription_service.check_can_create_team(db, user_id)
    
    if not can_create["allowed"]:
        raise HTTPException(
            status_code=403, 
            detail=can_create["reason"],
            headers={"X-Required-Plan": can_create.get("required_plan", "")}
        )
    
    # 팀 생성
    team = Team(
        name=team_data.name,
        description=team_data.description,
        owner_id=user_id,
        is_invite=team_data.is_invite if team_data.is_invite is not None else True
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
    
    return {
        "message": "Team created successfully",
        "team": team.to_dict(include_members=True)
    }

@router.get("/")
async def list_teams(
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    사용자가 속한 팀 목록 조회
    """
    user_id = current_user["id"]
    
    # 사용자가 멤버인 팀 조회
    team_members = db.query(TeamMember).filter(TeamMember.user_id == user_id).all()
    teams = []
    
    for tm in team_members:
        team = db.query(Team).filter(Team.id == tm.team_id, Team.is_active == True).first()
        if team:
            team_dict = team.to_dict(include_members=True)
            team_dict["my_role"] = tm.role.value if isinstance(tm.role, TeamRole) else tm.role
            teams.append(team_dict)
    
    return {"teams": teams}

@router.get("/{team_id}")
async def get_team(
    team_id: int,
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    팀 상세 정보 조회
    """
    user_id = current_user["id"]
    
    # 팀 존재 확인
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    # 멤버 권한 확인
    team_member = db.query(TeamMember).filter(
        TeamMember.team_id == team_id,
        TeamMember.user_id == user_id
    ).first()
    
    if not team_member:
        raise HTTPException(status_code=403, detail="You are not a member of this team")
    
    team_dict = team.to_dict(include_members=True)
    team_dict["my_role"] = team_member.role.value if isinstance(team_member.role, TeamRole) else team_member.role
    
    return {"team": team_dict}

@router.put("/{team_id}")
async def update_team(
    team_id: int,
    team_update: TeamUpdate,
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    팀 정보 수정 (관리자 이상만 가능)
    """
    user_id = current_user["id"]
    
    # 팀 존재 확인
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    # 권한 확인 (owner 또는 admin)
    team_member = db.query(TeamMember).filter(
        TeamMember.team_id == team_id,
        TeamMember.user_id == user_id
    ).first()
    
    if not team_member or team_member.role not in [TeamRole.OWNER, TeamRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Only team owners/admins can update team info")
    
    # 업데이트
    print(f"📝 팀 업데이트 요청 - ID: {team_id}")
    print(f"📝 전달된 값 - name: {team_update.name}, description: {team_update.description}")
    print(f"📝 전달된 값 - is_invite: {team_update.is_invite}")
    
    if team_update.name:
        team.name = team_update.name
    if team_update.description is not None:
        team.description = team_update.description
    if team_update.is_invite is not None:
        team.is_invite = team_update.is_invite
        print(f"✅ is_invite 업데이트: {team.is_invite}")
    
    db.commit()
    db.refresh(team)
    
    print(f"✅ 업데이트 완료 - 최종 is_invite: {team.is_invite}")
    
    return {
        "message": "Team updated successfully",
        "team": team.to_dict(include_members=True)
    }

@router.delete("/{team_id}")
async def delete_team(
    team_id: int,
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    팀 삭제 (소유자만 가능)
    """
    user_id = current_user["id"]
    
    # 팀 존재 확인
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    # 소유자 확인
    if team.owner_id != user_id:
        raise HTTPException(status_code=403, detail="Only team owner can delete the team")
    
    # 팀 삭제 (cascade로 team_members도 자동 삭제)
    db.delete(team)
    db.commit()
    
    return {"message": "Team deleted successfully"}

# ==================== 팀 멤버 관리 ====================

@router.post("/{team_id}/members")
async def add_team_member(
    team_id: int,
    member_data: MemberAdd,
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    팀에 멤버 추가 (관리자 이상만 가능)
    """
    user_id = current_user["id"]
    
    # 팀 존재 확인
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    # 권한 확인 (owner 또는 admin)
    team_member = db.query(TeamMember).filter(
        TeamMember.team_id == team_id,
        TeamMember.user_id == user_id
    ).first()
    
    if not team_member or team_member.role not in [TeamRole.OWNER, TeamRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Only team owners/admins can add members")
    
    # 구독 플랜 확인 (팀 소유자의 플랜)
    from services.subscription_service import subscription_service
    current_member_count = db.query(TeamMember).filter(TeamMember.team_id == team_id).count()
    can_add = subscription_service.check_can_add_team_member(db, team.owner_id, current_member_count)
    
    if not can_add["allowed"]:
        raise HTTPException(
            status_code=403,
            detail=can_add["reason"],
            headers={"X-Required-Plan": can_add.get("required_plan", "")}
        )
    
    # 추가할 사용자 찾기
    new_user = db.query(User).filter(User.email == member_data.user_email).first()
    if not new_user:
        raise HTTPException(status_code=404, detail=f"User not found: {member_data.user_email}")
    
    # 이미 멤버인지 확인
    existing = db.query(TeamMember).filter(
        TeamMember.team_id == team_id,
        TeamMember.user_id == new_user.id
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="User is already a team member")
    
    # 역할 검증
    try:
        role = TeamRole(member_data.role)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid role: {member_data.role}")
    
    # 멤버 추가
    new_member = TeamMember(
        team_id=team_id,
        user_id=new_user.id,
        role=role
    )
    db.add(new_member)
    db.commit()
    db.refresh(new_member)
    
    return {
        "message": "Member added successfully",
        "member": new_member.to_dict()
    }

@router.delete("/{team_id}/members/{user_id}")
async def remove_team_member(
    team_id: int,
    user_id: int,
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    팀에서 멤버 제거 (관리자 이상만 가능, 소유자는 제거 불가)
    """
    current_user_id = current_user["id"]
    
    # 팀 존재 확인
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    # 권한 확인
    requester = db.query(TeamMember).filter(
        TeamMember.team_id == team_id,
        TeamMember.user_id == current_user_id
    ).first()
    
    if not requester or requester.role not in [TeamRole.OWNER, TeamRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Only team owners/admins can remove members")
    
    # 소유자는 제거 불가
    if team.owner_id == user_id:
        raise HTTPException(status_code=400, detail="Cannot remove team owner")
    
    # 멤버 찾기
    member = db.query(TeamMember).filter(
        TeamMember.team_id == team_id,
        TeamMember.user_id == user_id
    ).first()
    
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    
    # 멤버 제거
    db.delete(member)
    db.commit()
    
    return {"message": "Member removed successfully"}

@router.put("/{team_id}/members/{user_id}/role")
async def update_member_role(
    team_id: int,
    user_id: int,
    role_update: MemberRoleUpdate,
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    팀 멤버 역할 변경 (소유자만 가능)
    """
    current_user_id = current_user["id"]
    
    # 팀 존재 확인
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    # 소유자 확인
    if team.owner_id != current_user_id:
        raise HTTPException(status_code=403, detail="Only team owner can change member roles")
    
    # 역할 검증
    try:
        new_role = TeamRole(role_update.role)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid role: {role_update.role}")
    
    # 멤버 찾기
    member = db.query(TeamMember).filter(
        TeamMember.team_id == team_id,
        TeamMember.user_id == user_id
    ).first()
    
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    
    # 소유자 역할은 변경 불가
    if member.role == TeamRole.OWNER:
        raise HTTPException(status_code=400, detail="Cannot change owner role")
    
    # 역할 업데이트
    member.role = new_role
    db.commit()
    db.refresh(member)
    
    return {
        "message": "Member role updated successfully",
        "member": member.to_dict()
    }

# ==================== 회의록 공유 ====================

@router.post("/{team_id}/recordings/{recording_id}/share")
async def share_recording_with_team(
    team_id: int,
    recording_id: str,
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    회의록을 팀에 공유
    """
    user_id = current_user["id"]
    
    # 팀 멤버 확인
    team_member = db.query(TeamMember).filter(
        TeamMember.team_id == team_id,
        TeamMember.user_id == user_id
    ).first()
    
    if not team_member:
        raise HTTPException(status_code=403, detail="You are not a member of this team")
    
    # 녹음 존재 확인
    recording = db.query(Recording).filter(Recording.id == recording_id).first()
    if not recording:
        raise HTTPException(status_code=404, detail="Recording not found")
    
    # 소유자 확인 (자기 회의록만 공유 가능)
    if recording.user_id != user_id:
        raise HTTPException(status_code=403, detail="You can only share your own recordings")
    
    # 공유 설정
    recording.team_id = team_id
    recording.is_shared = True
    recording.shared_at = datetime.now()
    
    db.commit()
    db.refresh(recording)
    
    # 안전한 to_dict 호출
    try:
        recording_dict = recording.to_dict(include_segments=False)
    except Exception as e:
        print(f"❌ recording.to_dict() 실패: {e}")
        recording_dict = {
            "id": recording.id if hasattr(recording, 'id') else getattr(recording, 'id', ''),
            "title": recording.title if hasattr(recording, 'title') else getattr(recording, 'title', ''),
            "status": recording.status,
            "createdAt": recording.created_at.isoformat() if recording.created_at else None,
            "duration": recording.duration,
            "userId": recording.user_id,
            "teamId": recording.team_id,
            "isShared": recording.is_shared,
            "sharedAt": recording.shared_at.isoformat() if recording.shared_at else None,
            "isFavorite": recording.is_favorite,
            "favoritedAt": recording.favorited_at.isoformat() if recording.favorited_at else None,
            "participants": recording.participants if recording.participants else [],
            "tags": [],
            "meetingStatus": recording.meeting_status,
            "questionsAnswers": recording.questions_answers if recording.questions_answers else [],
            "openIssues": recording.open_issues if recording.open_issues else [],
            "keyInsights": recording.key_insights if recording.key_insights else [],
            "verifiedNumbers": recording.verified_numbers if recording.verified_numbers else [],
            "transcript": recording.transcript,
            "summary": recording.summary,
            "audioUrl": recording.audio_url,
            "localAudioPath": recording.local_audio_path,
            "langAuto": recording.lang_auto
        }
    
    return {
        "message": "Recording shared with team successfully",
        "recording": recording_dict
    }

@router.delete("/{team_id}/recordings/{recording_id}/share")
async def unshare_recording_from_team(
    team_id: int,
    recording_id: str,
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    팀에서 회의록 공유 해제
    """
    user_id = current_user["id"]
    
    # 녹음 존재 확인
    recording = db.query(Recording).filter(Recording.id == recording_id).first()
    if not recording:
        raise HTTPException(status_code=404, detail="Recording not found")
    
    # 소유자 확인
    if recording.user_id != user_id:
        raise HTTPException(status_code=403, detail="You can only unshare your own recordings")
    
    # 공유 해제
    recording.team_id = None
    recording.is_shared = False
    recording.shared_at = None
    
    db.commit()
    db.refresh(recording)
    
    # 안전한 to_dict 호출
    try:
        recording_dict = recording.to_dict(include_segments=False)
    except Exception as e:
        print(f"❌ recording.to_dict() 실패: {e}")
        recording_dict = {
            "id": recording.id if hasattr(recording, 'id') else getattr(recording, 'id', ''),
            "title": recording.title if hasattr(recording, 'title') else getattr(recording, 'title', ''),
            "status": recording.status,
            "createdAt": recording.created_at.isoformat() if recording.created_at else None,
            "duration": recording.duration,
            "userId": recording.user_id,
            "teamId": recording.team_id,
            "isShared": recording.is_shared,
            "sharedAt": recording.shared_at.isoformat() if recording.shared_at else None,
            "isFavorite": recording.is_favorite,
            "favoritedAt": recording.favorited_at.isoformat() if recording.favorited_at else None,
            "participants": recording.participants if recording.participants else [],
            "tags": [],
            "meetingStatus": recording.meeting_status,
            "questionsAnswers": recording.questions_answers if recording.questions_answers else [],
            "openIssues": recording.open_issues if recording.open_issues else [],
            "keyInsights": recording.key_insights if recording.key_insights else [],
            "verifiedNumbers": recording.verified_numbers if recording.verified_numbers else [],
            "transcript": recording.transcript,
            "summary": recording.summary,
            "audioUrl": recording.audio_url,
            "localAudioPath": recording.local_audio_path,
            "langAuto": recording.lang_auto
        }
    
    return {
        "message": "Recording unshared from team successfully",
        "recording": recording_dict
    }

@router.get("/{team_id}/recordings")
async def get_team_recordings(
    team_id: int,
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 50
):
    """
    팀에 공유된 회의록 목록 조회
    """
    user_id = current_user["id"]
    
    # 팀 멤버 확인
    team_member = db.query(TeamMember).filter(
        TeamMember.team_id == team_id,
        TeamMember.user_id == user_id
    ).first()
    
    if not team_member:
        raise HTTPException(status_code=403, detail="You are not a member of this team")
    
    # 팀에 공유된 회의록 조회
    recordings = db.query(Recording).filter(
        Recording.team_id == team_id,
        Recording.is_shared == True
    ).order_by(Recording.created_at.desc()).offset(skip).limit(limit).all()
    
    # 안전한 to_dict 호출
    recordings_list = []
    for rec in recordings:
        try:
            recordings_list.append(rec.to_dict(include_segments=False))
        except Exception as e:
            print(f"❌ recording.to_dict() 실패: {e}")
            recordings_list.append({
                "id": rec.id,
                "title": rec.title,
                "status": rec.status,
                "createdAt": rec.created_at.isoformat() if rec.created_at else None,
                "duration": rec.duration,
                "userId": rec.user_id,
                "teamId": rec.team_id,
                "isShared": rec.is_shared,
                "sharedAt": rec.shared_at.isoformat() if rec.shared_at else None,
                "isFavorite": rec.is_favorite,
                "favoritedAt": rec.favorited_at.isoformat() if rec.favorited_at else None,
                "participants": rec.participants if rec.participants else [],
                "tags": [],
                "meetingStatus": rec.meeting_status,
                "questionsAnswers": rec.questions_answers if rec.questions_answers else [],
                "openIssues": rec.open_issues if rec.open_issues else [],
                "keyInsights": rec.key_insights if rec.key_insights else [],
                "verifiedNumbers": rec.verified_numbers if rec.verified_numbers else [],
                "transcript": rec.transcript,
                "summary": rec.summary,
                "audioUrl": rec.audio_url,
                "localAudioPath": rec.local_audio_path,
                "langAuto": rec.lang_auto
            })
    
    return {
        "recordings": recordings_list,
        "total": len(recordings)
    }

