"""
팀 역할 enum 값 직접 수정
"""
import sys
import os

# 현재 디렉토리를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.connection import SessionLocal
from sqlalchemy import text

def fix_team_roles_direct():
    """팀 역할 enum 값을 직접 SQL로 수정"""
    db = SessionLocal()
    try:
        print("🔧 팀 역할 enum 값 직접 수정 시작...")
        
        # 기존 데이터 확인
        result = db.execute(text("SELECT role, COUNT(*) as count FROM team_members GROUP BY role"))
        roles = result.fetchall()
        print(f"📋 수정 전 역할 분포:")
        for role, count in roles:
            print(f"   - {role}: {count}명")
        
        # 소문자 'owner'를 대문자 'OWNER'로 변경
        print("🔄 'owner' → 'OWNER' 변경 중...")
        result = db.execute(text("UPDATE team_members SET role = 'OWNER' WHERE role = 'owner'"))
        print(f"✅ {result.rowcount}개 행이 업데이트되었습니다.")
        
        # 변경 후 데이터 확인
        result = db.execute(text("SELECT role, COUNT(*) as count FROM team_members GROUP BY role"))
        roles = result.fetchall()
        print(f"📋 수정 후 역할 분포:")
        for role, count in roles:
            print(f"   - {role}: {count}명")
        
        db.commit()
        print("✅ 팀 역할 enum 값 수정 완료!")
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        db.rollback()
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    fix_team_roles_direct()
