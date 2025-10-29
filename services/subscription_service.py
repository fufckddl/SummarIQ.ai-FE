"""
구독 관리 서비스
"""
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Dict, Optional
from models.subscription import Subscription, SubscriptionPlan, SubscriptionStatus, UsageStats
from models.user import User


class SubscriptionService:
    """구독 플랜 제한 및 관리"""
    
    # 플랜별 제한
    PLAN_LIMITS = {
        SubscriptionPlan.FREE: {
            "monthly_minutes": 600,  # 10시간
            "team_members": 0,       # 팀 기능 없음
            "storage_days": 30,
            "priority": 0,
        },
        SubscriptionPlan.BASIC: {
            "monthly_minutes": 1500,  # 25시간
            "team_members": 0,        # 팀 기능 없음 (개인용)
            "storage_days": 365,
            "priority": 1,            # 우선 처리
        },
        SubscriptionPlan.PLUS: {
            "monthly_minutes": 3000,  # 50시간
            "team_members": 5,
            "storage_days": 365,
            "priority": 2,
        },
        SubscriptionPlan.PRO: {
            "monthly_minutes": -1,  # 무제한
            "team_members": 10,
            "storage_days": -1,  # 무제한
            "priority": 3,
        },
    }
    
    @staticmethod
    def get_user_subscription(db: Session, user_id: int) -> Optional[Subscription]:
        """사용자의 활성 구독 조회"""
        return db.query(Subscription).filter(
            Subscription.user_id == user_id,
            Subscription.status == SubscriptionStatus.ACTIVE
        ).first()
    
    @staticmethod
    def get_or_create_subscription(db: Session, user_id: int) -> Subscription:
        """구독 조회 또는 FREE 플랜 생성"""
        subscription = SubscriptionService.get_user_subscription(db, user_id)
        
        if not subscription:
            # FREE 플랜 자동 생성
            subscription = Subscription(
                user_id=user_id,
                plan=SubscriptionPlan.FREE,
                status=SubscriptionStatus.ACTIVE,
                started_at=datetime.now()
            )
            db.add(subscription)
            db.commit()
            db.refresh(subscription)
        
        return subscription
    
    @staticmethod
    def check_can_create_team(db: Session, user_id: int) -> Dict:
        """팀 생성 가능 여부 확인"""
        subscription = SubscriptionService.get_or_create_subscription(db, user_id)
        plan_limit = SubscriptionService.PLAN_LIMITS[subscription.plan]
        
        if plan_limit["team_members"] == 0:
            return {
                "allowed": False,
                "reason": "팀 기능은 PLUS 이상 플랜에서 사용 가능합니다.",
                "required_plan": "plus"
            }
        
        return {"allowed": True}
    
    @staticmethod
    def check_can_add_team_member(db: Session, user_id: int, current_members: int) -> Dict:
        """팀 멤버 추가 가능 여부 확인"""
        subscription = SubscriptionService.get_or_create_subscription(db, user_id)
        plan_limit = SubscriptionService.PLAN_LIMITS[subscription.plan]
        max_members = plan_limit["team_members"]
        
        if max_members == 0:
            return {
                "allowed": False,
                "reason": "팀 기능은 PLUS 이상 플랜에서 사용 가능합니다.",
                "required_plan": "plus"
            }
        
        if current_members >= max_members:
            return {
                "allowed": False,
                "reason": f"현재 플랜은 최대 {max_members}명까지 가능합니다.",
                "current": current_members,
                "limit": max_members,
                "required_plan": "pro" if subscription.plan == SubscriptionPlan.PLUS else None
            }
        
        return {"allowed": True}
    
    @staticmethod
    def get_current_month_usage(db: Session, user_id: int) -> UsageStats:
        """현재 월의 사용량 조회 또는 생성"""
        now = datetime.now()
        year = now.year
        month = now.month
        
        usage = db.query(UsageStats).filter(
            UsageStats.user_id == user_id,
            UsageStats.year == year,
            UsageStats.month == month
        ).first()
        
        if not usage:
            usage = UsageStats(
                user_id=user_id,
                year=year,
                month=month,
                recording_minutes=0,
                recording_count=0,
                ai_summary_count=0
            )
            db.add(usage)
            db.commit()
            db.refresh(usage)
        
        return usage
    
    @staticmethod
    def check_can_record(db: Session, user_id: int, duration_minutes: int = 0) -> Dict:
        """녹음 가능 여부 확인"""
        subscription = SubscriptionService.get_or_create_subscription(db, user_id)
        usage = SubscriptionService.get_current_month_usage(db, user_id)
        plan_limit = SubscriptionService.PLAN_LIMITS[subscription.plan]
        
        monthly_limit = plan_limit["monthly_minutes"]
        
        # 무제한 플랜
        if monthly_limit == -1:
            return {"allowed": True, "unlimited": True}
        
        # 제한 확인
        used = usage.recording_minutes
        remaining = monthly_limit - used
        
        if used + duration_minutes > monthly_limit:
            return {
                "allowed": False,
                "reason": f"이번 달 녹음 시간을 모두 사용했습니다 ({used}/{monthly_limit}분).",
                "used": used,
                "limit": monthly_limit,
                "remaining": remaining,
                "required_plan": "plus" if subscription.plan == SubscriptionPlan.FREE else "pro"
            }
        
        return {
            "allowed": True,
            "used": used,
            "limit": monthly_limit,
            "remaining": remaining
        }
    
    @staticmethod
    def record_usage(db: Session, user_id: int, duration_minutes: int):
        """녹음 사용량 기록"""
        usage = SubscriptionService.get_current_month_usage(db, user_id)
        usage.recording_minutes += duration_minutes
        usage.recording_count += 1
        db.commit()
    
    @staticmethod
    def record_summary_usage(db: Session, user_id: int):
        """AI 요약 사용량 기록"""
        usage = SubscriptionService.get_current_month_usage(db, user_id)
        usage.ai_summary_count += 1
        db.commit()


subscription_service = SubscriptionService()

