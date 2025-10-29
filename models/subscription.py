"""
구독 및 결제 모델
"""
from sqlalchemy import Column, String, Integer, DateTime, Boolean, ForeignKey, Enum, Numeric, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from models import Base
import enum


class SubscriptionPlan(str, enum.Enum):
    """구독 플랜"""
    FREE = "FREE"
    BASIC = "BASIC"
    PLUS = "PLUS"
    PRO = "PRO"


class SubscriptionStatus(str, enum.Enum):
    """구독 상태"""
    ACTIVE = "ACTIVE"           # 활성
    CANCELLED = "CANCELLED"     # 취소됨 (기간 만료까지 사용 가능)
    EXPIRED = "EXPIRED"         # 만료됨
    PENDING = "PENDING"         # 결제 대기


class Subscription(Base):
    """사용자 구독 테이블"""
    __tablename__ = "subscriptions"
    
    # 기본 정보
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    
    # 플랜 정보
    plan = Column(Enum(SubscriptionPlan), default=SubscriptionPlan.FREE, nullable=False)
    status = Column(Enum(SubscriptionStatus), default=SubscriptionStatus.ACTIVE, nullable=False)
    
    # 기간
    started_at = Column(DateTime, nullable=False)
    expires_at = Column(DateTime, nullable=True)  # None이면 무제한 (FREE)
    cancelled_at = Column(DateTime, nullable=True)
    
    # 결제 정보
    payment_provider = Column(String(50), nullable=True)  # 'stripe', 'toss', 'iap'
    payment_id = Column(String(255), nullable=True)  # 외부 결제 시스템 ID
    
    # 타임스탬프
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)
    
    # 관계
    user = relationship("User", back_populates="subscription")
    
    def to_dict(self):
        """딕셔너리 변환"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "plan": self.plan.value if isinstance(self.plan, SubscriptionPlan) else self.plan,
            "status": self.status.value if isinstance(self.status, SubscriptionStatus) else self.status,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "cancelled_at": self.cancelled_at.isoformat() if self.cancelled_at else None,
            "payment_provider": self.payment_provider,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class UsageStats(Base):
    """사용량 통계 테이블 (월별)"""
    __tablename__ = "usage_stats"
    
    # 기본 정보
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    
    # 기간
    year = Column(Integer, nullable=False)
    month = Column(Integer, nullable=False)
    
    # 사용량
    recording_minutes = Column(Integer, default=0, nullable=False)  # 녹음 시간 (분)
    recording_count = Column(Integer, default=0, nullable=False)    # 녹음 개수
    ai_summary_count = Column(Integer, default=0, nullable=False)   # AI 요약 생성 횟수
    
    # 타임스탬프
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)
    
    # 관계
    user = relationship("User", backref="usage_stats")
    
    def to_dict(self):
        """딕셔너리 변환"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "year": self.year,
            "month": self.month,
            "recording_minutes": self.recording_minutes,
            "recording_count": self.recording_count,
            "ai_summary_count": self.ai_summary_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Payment(Base):
    """결제 내역 테이블"""
    __tablename__ = "payments"
    
    # 기본 정보
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    subscription_id = Column(Integer, ForeignKey('subscriptions.id'), nullable=True)
    
    # 결제 정보
    amount = Column(Numeric(10, 2), nullable=False)  # 금액
    currency = Column(String(3), default='KRW', nullable=False)  # 통화
    
    # 결제 수단
    payment_provider = Column(String(50), nullable=False)  # 'stripe', 'toss', 'iap'
    payment_method = Column(String(50), nullable=True)  # 'card', 'bank', 'apple_pay'
    payment_id = Column(String(255), nullable=False)  # 외부 결제 시스템 ID
    
    # 상태
    status = Column(String(20), default='pending', nullable=False)  # pending, completed, failed, refunded
    
    # 메타데이터
    description = Column(Text, nullable=True)
    receipt_url = Column(String(500), nullable=True)
    
    # 타임스탬프
    paid_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)
    
    # 관계
    user = relationship("User", backref="payments")
    
    def to_dict(self):
        """딕셔너리 변환"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "subscription_id": self.subscription_id,
            "amount": float(self.amount) if self.amount else 0,
            "currency": self.currency,
            "payment_provider": self.payment_provider,
            "payment_method": self.payment_method,
            "status": self.status,
            "description": self.description,
            "receipt_url": self.receipt_url,
            "paid_at": self.paid_at.isoformat() if self.paid_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

