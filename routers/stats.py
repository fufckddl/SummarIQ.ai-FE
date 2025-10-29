"""
통계 및 대시보드 API 라우터
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import json

from database.connection import get_db
from utils.auth_dependency import get_current_user
from models.recording import Recording
from models.tag import Tag, recording_tags
from models.user import User
from models.subscription import Subscription
from models.team import Team, TeamMember

router = APIRouter(prefix="/api/stats", tags=["stats"])

# ==================== API 엔드포인트 ====================

@router.get("/dashboard")
async def get_dashboard_stats(
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db),
    period: str = "week"  # week, month, all
):
    """
    대시보드 통계 조회
    """
    user_id = current_user["id"]
    
    # 구독 정보 확인
    user = db.query(User).filter(User.id == user_id).first()
    subscription = db.query(Subscription).filter(Subscription.user_id == user_id).first()
    
    # plan은 Enum이므로 .value로 문자열 추출 후 소문자 변환
    if subscription and subscription.plan:
        plan_type = subscription.plan.value.lower() if hasattr(subscription.plan, 'value') else str(subscription.plan).lower()
    else:
        plan_type = "free"
    
    # 기간 계산
    now = datetime.utcnow()
    if period == "week":
        start_date = now - timedelta(days=7)
    elif period == "month":
        start_date = now - timedelta(days=30)
    else:
        start_date = None
    
    # 1️⃣ 회의 통계
    query = db.query(Recording).filter(Recording.user_id == user_id)
    if start_date:
        query = query.filter(Recording.created_at >= start_date)
    
    recordings = query.all()
    
    total_meetings = len(recordings)
    total_duration = sum([r.duration or 0 for r in recordings]) if recordings else 0
    avg_duration = total_duration / total_meetings if total_meetings > 0 else 0
    
    # 상태별 카운트
    ready_count = len([r for r in recordings if r.status == 'ready'])
    processing_count = len([r for r in recordings if r.status in ['processing', 'stt_started']])
    
    # 2️⃣ 태그 통계 (TOP 5)
    tag_stats = db.query(
        Tag.name,
        Tag.color,
        func.count(recording_tags.c.recording_id).label('count')
    ).join(
        recording_tags, Tag.id == recording_tags.c.tag_id
    ).join(
        Recording, Recording.id == recording_tags.c.recording_id
    ).filter(
        Recording.user_id == user_id
    )
    
    if start_date:
        tag_stats = tag_stats.filter(Recording.created_at >= start_date)
    
    tag_stats = tag_stats.group_by(Tag.id).order_by(func.count(recording_tags.c.recording_id).desc()).limit(5).all()
    
    top_tags = [{"name": tag[0], "color": tag[1], "count": tag[2]} for tag in tag_stats]
    
    # 3️⃣ 액션 아이템 통계
    total_actions = 0
    completed_actions = 0
    
    for recording in recordings:
        if recording.actions:
            actions_list = recording.actions if isinstance(recording.actions, list) else json.loads(recording.actions)
            total_actions += len(actions_list)
            completed_actions += len([a for a in actions_list if isinstance(a, dict) and a.get('completed')])
    
    action_completion_rate = (completed_actions / total_actions * 100) if total_actions > 0 else 0
    
    # 4️⃣ 즐겨찾기 통계
    favorite_count = len([r for r in recordings if r.is_favorite])
    
    # 5️⃣ 팀 통계 (Plus/Pro만, BASIC은 제외)
    team_stats = None
    if plan_type in ["plus", "pro"]:
        # 사용자가 속한 팀 조회
        team_memberships = db.query(TeamMember).filter(TeamMember.user_id == user_id).all()
        team_ids = [tm.team_id for tm in team_memberships]
        
        if team_ids:
            teams = db.query(Team).filter(Team.id.in_(team_ids)).all()
            
            team_stats = []
            for team in teams:
                # 팀의 공유된 회의록 개수
                team_recordings = db.query(Recording).filter(Recording.team_id == team.id)
                if start_date:
                    team_recordings = team_recordings.filter(Recording.created_at >= start_date)
                
                team_meeting_count = team_recordings.count()
                
                team_stats.append({
                    "team_id": team.id,
                    "team_name": team.name,
                    "meeting_count": team_meeting_count,
                    "member_count": db.query(TeamMember).filter(TeamMember.team_id == team.id).count()
                })
    
    # 6️⃣ 최근 활동 (최근 7일)
    recent_start = now - timedelta(days=7)
    recent_recordings = db.query(Recording).filter(
        Recording.user_id == user_id,
        Recording.created_at >= recent_start
    ).order_by(Recording.created_at.desc()).limit(10).all()
    
    recent_activities = [{
        "id": r.id,
        "title": r.title,
        "created_at": r.created_at.isoformat() if r.created_at else None,
        "status": r.status,
        "duration": r.duration
    } for r in recent_recordings]
    
    # 7️⃣ 일별 회의 수 (최근 7일)
    daily_stats = []
    for i in range(7):
        day_start = now - timedelta(days=6-i)
        day_start = day_start.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        
        day_count = db.query(Recording).filter(
            Recording.user_id == user_id,
            Recording.created_at >= day_start,
            Recording.created_at < day_end
        ).count()
        
        daily_stats.append({
            "date": day_start.strftime("%Y-%m-%d"),
            "count": day_count
        })
    
    return {
        "period": period,
        "plan_type": plan_type,
        "meeting_stats": {
            "total": total_meetings,
            "ready": ready_count,
            "processing": processing_count,
            "total_duration_ms": total_duration,
            "avg_duration_ms": int(avg_duration)
        },
        "tag_stats": {
            "top_tags": top_tags
        },
        "action_stats": {
            "total": total_actions,
            "completed": completed_actions,
            "completion_rate": round(action_completion_rate, 1)
        },
        "favorite_count": favorite_count,
        "team_stats": team_stats,  # Plus/Pro만 제공
        "recent_activities": recent_activities,
        "daily_stats": daily_stats
    }

@router.get("/summary")
async def get_quick_summary(
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    빠른 요약 통계 (홈 화면용)
    """
    user_id = current_user["id"]
    
    # 전체 회의 수
    total_meetings = db.query(Recording).filter(Recording.user_id == user_id).count()
    
    # 🇰🇷 한국 시간 기준 이번 주 계산 (월요일 00:00 ~ 현재)
    from pytz import timezone
    kst = timezone('Asia/Seoul')
    now_kst = datetime.now(kst)
    
    # 이번 주 월요일 00:00 계산
    days_since_monday = now_kst.weekday()  # 0=월요일, 6=일요일
    week_start_kst = now_kst.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=days_since_monday)
    
    # UTC로 변환 (DB에 저장된 시간은 UTC)
    week_start_utc = week_start_kst.astimezone(timezone('UTC')).replace(tzinfo=None)
    
    # 이번 주 녹음 조회
    week_recordings = db.query(Recording).filter(
        Recording.user_id == user_id,
        Recording.created_at >= week_start_utc
    ).all()
    
    # 이번 주 총 녹음 시간 계산 (밀리초 → 시간)
    week_duration_ms = sum([r.duration or 0 for r in week_recordings])
    week_duration_hours = week_duration_ms / 1000 / 3600  # ms → 초 → 시간
    
    # 처리 중인 회의
    processing = db.query(Recording).filter(
        Recording.user_id == user_id,
        Recording.status.in_(['processing', 'stt_started'])
    ).count()
    
    print(f"📊 통계 조회 (user_id={user_id}):")
    print(f"   - 전체 회의: {total_meetings}개")
    print(f"   - 이번 주 녹음: {len(week_recordings)}개")
    print(f"   - 이번 주 시간: {week_duration_hours:.1f}시간 ({week_duration_ms}ms)")
    print(f"   - 주 시작: {week_start_kst} (KST)")
    
    return {
        "total_meetings": total_meetings,
        "week_meetings": len(week_recordings),
        "week_duration_hours": round(week_duration_hours, 1),  # 소수점 1자리
        "processing": processing
    }

