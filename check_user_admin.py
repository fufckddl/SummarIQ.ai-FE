"""
사용자 정보 확인을 위한 관리자 스크립트
"""
import sys
import os

# 현재 디렉토리를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.connection import SessionLocal
from models.subscription import Subscription
from models.user import User
from sqlalchemy.orm import joinedload

def check_user_plan(user_id: int):
    """사용자 플랜 정보 확인"""
    db = SessionLocal()
    try:
        # 사용자 정보 조회
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            print(f"❌ User ID {user_id}를 찾을 수 없습니다.")
            return
        
        print(f"👤 사용자 정보:")
        print(f"   - ID: {user.id}")
        print(f"   - 이메일: {user.email}")
        print(f"   - 이름: {user.display_name}")
        print(f"   - 생성일: {user.created_at}")
        
        # 구독 정보 조회
        subscription = db.query(Subscription).filter(Subscription.user_id == user_id).first()
        if subscription:
            print(f"\n📋 구독 정보:")
            print(f"   - 구독 ID: {subscription.id}")
            print(f"   - 플랜: {subscription.plan}")
            print(f"   - 상태: {subscription.status}")
            print(f"   - 시작일: {subscription.started_at}")
            print(f"   - 만료일: {subscription.expires_at}")
            print(f"   - 생성일: {subscription.created_at}")
            print(f"   - 수정일: {subscription.updated_at}")
        else:
            print(f"\n❌ User ID {user_id}의 구독 정보를 찾을 수 없습니다.")
        
        # 모든 구독 정보 확인
        print(f"\n📊 전체 구독 정보:")
        all_subscriptions = db.query(Subscription).all()
        for sub in all_subscriptions:
            user_info = db.query(User).filter(User.id == sub.user_id).first()
            print(f"   - User {sub.user_id}: {sub.plan} ({sub.status}) - {user_info.email if user_info else 'Unknown'} ({user_info.display_name if user_info else 'Unknown'})")
            
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    check_user_plan(3)
