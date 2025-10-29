"""
사용자 플랜 정보 확인 스크립트
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
    engine = create_engine(DATABASE_URL, echo=False)
    
    # 연결 테스트
    with engine.connect() as conn:
        # user_id = 3의 구독 정보 조회
        result = conn.execute(text("""
            SELECT 
                s.id as subscription_id,
                s.user_id,
                s.plan,
                s.status,
                s.started_at,
                s.expires_at,
                s.created_at,
                s.updated_at
            FROM subscriptions s 
            WHERE s.user_id = 3
        """))
        
        row = result.fetchone()
        
        if row:
            print(f'\n📋 User ID 3의 구독 정보:')
            print(f'   - 구독 ID: {row[0]}')
            print(f'   - 사용자 ID: {row[1]}')
            print(f'   - 플랜: {row[2]}')
            print(f'   - 상태: {row[3]}')
            print(f'   - 시작일: {row[4]}')
            print(f'   - 만료일: {row[5]}')
            print(f'   - 생성일: {row[6]}')
            print(f'   - 수정일: {row[7]}')
        else:
            print('\n❌ User ID 3의 구독 정보를 찾을 수 없습니다.')
            
            # 사용자 정보 확인
            result = conn.execute(text("""
                SELECT 
                    u.id,
                    u.email,
                    u.display_name,
                    u.created_at
                FROM users u 
                WHERE u.id = 3
            """))
            
            user_row = result.fetchone()
            if user_row:
                print(f'\n👤 사용자 정보:')
                print(f'   - ID: {user_row[0]}')
                print(f'   - 이메일: {user_row[1]}')
                print(f'   - 이름: {user_row[2]}')
                print(f'   - 생성일: {user_row[3]}')
            else:
                print('\n❌ User ID 3의 사용자 정보도 찾을 수 없습니다.')
        
        # 모든 구독 정보 확인
        print(f'\n📊 전체 구독 정보:')
        result = conn.execute(text("""
            SELECT 
                s.user_id,
                s.plan,
                s.status,
                u.email,
                u.display_name
            FROM subscriptions s
            LEFT JOIN users u ON s.user_id = u.id
            ORDER BY s.user_id
        """))
        
        rows = result.fetchall()
        for row in rows:
            print(f'   - User {row[0]}: {row[1]} ({row[2]}) - {row[3]} ({row[4]})')

except Exception as e:
    print(f'\n❌ 오류 발생: {e}')
    import traceback
    traceback.print_exc()
