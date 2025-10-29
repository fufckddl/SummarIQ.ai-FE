"""
사용자 플랜을 Pro로 업데이트하는 스크립트
"""
import sys
import os

# 현재 디렉토리를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text
from datetime import datetime

# 데이터베이스 URL (환경변수 또는 기본값 사용)
DB_USER = os.getenv('DB_USER', 'root')
DB_PASSWORD = os.getenv('DB_PASSWORD', '')
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '3306')
DB_NAME = os.getenv('DB_NAME', 'summariq')

# 비밀번호가 있으면 포함, 없으면 제외
if DB_PASSWORD:
    DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
else:
    DATABASE_URL = f"mysql+pymysql://{DB_USER}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

print(f"📡 데이터베이스 연결 시도: {DB_HOST}:{DB_PORT}/{DB_NAME}")

try:
    # 엔진 생성
    engine = create_engine(DATABASE_URL, echo=True)
    
    # 연결 테스트
    with engine.connect() as conn:
        # 현재 구독 정보 확인
        result = conn.execute(text("SELECT * FROM subscriptions WHERE user_id = 3"))
        row = result.fetchone()
        
        if row:
            # 기존 구독 정보 업데이트
            conn.execute(text("""
                UPDATE subscriptions 
                SET plan = 'PRO', 
                    status = 'ACTIVE',
                    updated_at = :updated_at
                WHERE user_id = 3
            """), {"updated_at": datetime.now()})
            conn.commit()
            print(f'\n✅ 기존 구독 정보 업데이트: user_id=3, plan=PRO')
        else:
            # 새 구독 정보 생성
            conn.execute(text("""
                INSERT INTO subscriptions (user_id, plan, status, started_at, created_at, updated_at)
                VALUES (3, 'PRO', 'ACTIVE', :started_at, :created_at, :updated_at)
            """), {
                "started_at": datetime.now(),
                "created_at": datetime.now(),
                "updated_at": datetime.now()
            })
            conn.commit()
            print(f'\n✅ 새 구독 정보 생성: user_id=3, plan=PRO')
        
        # 결과 확인
        result = conn.execute(text("SELECT user_id, plan, status, started_at, expires_at FROM subscriptions WHERE user_id = 3"))
        row = result.fetchone()
        
        print(f'\n📋 현재 구독 정보:')
        print(f'   - user_id: {row[0]}')
        print(f'   - plan: {row[1]}')
        print(f'   - status: {row[2]}')
        print(f'   - started_at: {row[3]}')
        print(f'   - expires_at: {row[4]}')
        print(f'\n✨ 플랜 변경 완료!')

except Exception as e:
    print(f'\n❌ 오류 발생: {e}')
    import traceback
    traceback.print_exc()

