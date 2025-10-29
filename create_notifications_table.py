"""
알림 테이블 생성 스크립트
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.connection import engine, Base
from models.notification import Notification
from models.user import User

def create_notifications_table():
    """알림 테이블 생성"""
    try:
        print("🔍 알림 테이블 생성 중...")
        
        # 알림 테이블 생성
        Notification.__table__.create(engine, checkfirst=True)
        print("✅ 알림 테이블이 성공적으로 생성되었습니다")
        
        return True
    except Exception as e:
        print(f"❌ 알림 테이블 생성 실패: {e}")
        return False

if __name__ == "__main__":
    create_notifications_table()
