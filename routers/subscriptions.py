"""
구독 및 결제 API 라우터
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Dict, Optional
from datetime import datetime, timedelta

from database.connection import get_db
from utils.auth_dependency import get_current_user
from models.subscription import Subscription, SubscriptionPlan, SubscriptionStatus, Payment
from models.user import User
from services.subscription_service import subscription_service

router = APIRouter(prefix="/api/subscriptions", tags=["subscriptions"])

# ==================== Pydantic 모델 ====================

class PlanInfo(BaseModel):
    name: str
    price_monthly: int
    price_yearly: int
    features: Dict

# ==================== 요금제 정보 ====================

# 얼리버드 프로모션 설정
EARLY_BIRD_PROMOTION = {
    "active": True,
    "end_date": "2025-06-30T23:59:59",  # 얼리버드 종료일
    "discount_rate": 0.33,  # 33% 할인
}

PLAN_PRICES = {
    "free": {
        "name": "FREE",
        "price_monthly": 0,
        "price_yearly": 0,
        "features": {
            "monthly_minutes": 600,  # 10시간
            "team_members": 0,
            "storage_days": 30,
            "ai_summary": True,
            "notion_integration": True,
            "voice_enhancement": False,
            "priority_support": False,
            "api_access": False,
        }
    },
    "basic": {
        "name": "BASIC",
        "price_monthly": 14900,  # 정가
        "price_yearly": 149000,
        "early_bird_monthly": 9900,  # 얼리버드 가격
        "early_bird_yearly": 99000,
        "features": {
            "monthly_minutes": 1500,  # 25시간
            "team_members": 0,  # 팀 기능 없음 (개인용)
            "storage_days": 365,
            "ai_summary": True,
            "notion_integration": True,
            "voice_enhancement": True,
            "priority_support": True,  # 우선 처리
            "api_access": False,
        }
    },
    "plus": {
        "name": "PLUS",
        "price_monthly": 29900,  # 정가
        "price_yearly": 299000,
        "early_bird_monthly": 19900,  # 얼리버드 가격
        "early_bird_yearly": 199000,
        "features": {
            "monthly_minutes": 3000,  # 50시간
            "team_members": 5,
            "storage_days": 365,
            "ai_summary": True,
            "notion_integration": True,
            "voice_enhancement": True,
            "priority_support": True,
            "api_access": False,
        }
    },
    "pro": {
        "name": "PRO",
        "price_monthly": 49900,  # 정가
        "price_yearly": 499000,
        "early_bird_monthly": 33900,  # 얼리버드 가격
        "early_bird_yearly": 339000,
        "features": {
            "monthly_minutes": -1,  # 무제한
            "team_members": 10,
            "storage_days": -1,  # 무제한
            "ai_summary": True,
            "notion_integration": True,
            "voice_enhancement": True,
            "priority_support": True,
            "api_access": True,
        }
    }
}

# ==================== API 엔드포인트 ====================

@router.get("/plans")
async def get_plans():
    """사용 가능한 요금제 목록 (프로모션 정보 포함)"""
    return {
        "plans": PLAN_PRICES,
        "promotion": EARLY_BIRD_PROMOTION
    }

@router.get("/my-subscription")
async def get_my_subscription(
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """현재 사용자의 구독 정보"""
    user_id = current_user["id"]
    
    subscription = subscription_service.get_or_create_subscription(db, user_id)
    usage = subscription_service.get_current_month_usage(db, user_id)
    
    plan_limits = subscription_service.PLAN_LIMITS[subscription.plan]
    
    return {
        "subscription": subscription.to_dict(),
        "plan_info": PLAN_PRICES[subscription.plan.value.lower()],  # 대문자 → 소문자 변환
        "usage": usage.to_dict(),
        "limits": plan_limits
    }

@router.get("/usage")
async def get_usage_stats(
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """사용량 통계"""
    user_id = current_user["id"]
    usage = subscription_service.get_current_month_usage(db, user_id)
    subscription = subscription_service.get_or_create_subscription(db, user_id)
    plan_limits = subscription_service.PLAN_LIMITS[subscription.plan]
    
    return {
        "current_month": usage.to_dict(),
        "limits": plan_limits,
        "percentage": {
            "recording_minutes": (usage.recording_minutes / plan_limits["monthly_minutes"] * 100) 
                if plan_limits["monthly_minutes"] > 0 else 0
        }
    }

@router.post("/upgrade")
async def upgrade_subscription(
    plan: str,
    billing_cycle: str,  # 'monthly' or 'yearly'
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    구독 업그레이드 (실제 결제는 프론트엔드에서 처리)
    """
    user_id = current_user["id"]
    
    # 플랜 검증
    if plan not in ['basic', 'plus', 'pro']:
        raise HTTPException(status_code=400, detail="Invalid plan")
    
    # 현재 구독 조회
    current_subscription = subscription_service.get_or_create_subscription(db, user_id)
    
    # 이미 같은 플랜이거나 더 높은 플랜인 경우
    plan_enum = SubscriptionPlan(plan)
    if current_subscription.plan == plan_enum:
        raise HTTPException(status_code=400, detail="Already subscribed to this plan")
    
    # TODO: 실제 결제 처리 (Stripe, Toss Payments, IAP 등)
    # 여기서는 시뮬레이션
    
    # 기존 구독 만료 처리
    if current_subscription.plan != SubscriptionPlan.FREE:
        current_subscription.status = SubscriptionStatus.CANCELLED
        current_subscription.cancelled_at = datetime.now()
        current_subscription.expires_at = datetime.now()
    
    # 새 구독 생성
    duration = 30 if billing_cycle == 'monthly' else 365
    new_subscription = Subscription(
        user_id=user_id,
        plan=plan_enum,
        status=SubscriptionStatus.ACTIVE,
        started_at=datetime.now(),
        expires_at=datetime.now() + timedelta(days=duration),
        payment_provider='simulation'  # 실제로는 'stripe', 'toss', 'iap'
    )
    
    db.add(new_subscription)
    db.commit()
    db.refresh(new_subscription)
    
    return {
        "message": f"{plan.upper()} 플랜으로 업그레이드되었습니다!",
        "subscription": new_subscription.to_dict()
    }

@router.post("/cancel")
async def cancel_subscription(
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """구독 취소 (기간 만료까지 사용 가능)"""
    user_id = current_user["id"]
    
    subscription = subscription_service.get_user_subscription(db, user_id)
    
    if not subscription:
        raise HTTPException(status_code=404, detail="활성 구독이 없습니다")
    
    if subscription.plan == SubscriptionPlan.FREE:
        raise HTTPException(status_code=400, detail="FREE 플랜은 취소할 수 없습니다")
    
    if subscription.status == SubscriptionStatus.CANCELLED:
        raise HTTPException(status_code=400, detail="이미 취소된 구독입니다")
    
    # 취소 처리
    subscription.status = SubscriptionStatus.CANCELLED
    subscription.cancelled_at = datetime.now()
    
    db.commit()
    db.refresh(subscription)
    
    return {
        "message": "구독이 취소되었습니다. 기간 만료까지 사용 가능합니다.",
        "subscription": subscription.to_dict()
    }


subscription_service_instance = subscription_service

