#!/usr/bin/env python3
"""
팀 멤버의 역할을 수정하는 스크립트
팀을 만든 사람(owner_id)의 역할을 OWNER로 설정
"""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import os

# 데이터베이스 연결
DATABASE_URL = os.getenv('DATABASE_URL')

if not DATABASE_URL:
    raise ValueError('DATABASE_URL environment variable is required.')

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db = SessionLocal()

try:
    # 팀과 팀 멤버 정보 조회
    result = db.execute(text("""
        SELECT t.id as team_id, t.name as team_name, t.owner_id, 
               tm.user_id, tm.role, u.email
        FROM teams t
        LEFT JOIN team_members tm ON t.id = tm.team_id
        LEFT JOIN users u ON tm.user_id = u.id
        ORDER BY t.id, tm.user_id
    """))
    rows = result.fetchall()
    
    print('📊 팀 멤버 역할 현황:')
    for row in rows:
        print(f'  팀: {row.team_name} (ID: {row.team_id})')
        print(f'  소유자 ID: {row.owner_id}')
        print(f'  멤버: {row.email} (ID: {row.user_id})')
        print(f'  현재 역할: {row.role}')
        print('  ---')
    
    # 팀 소유자의 역할을 OWNER로 업데이트
    update_result = db.execute(text("""
        UPDATE team_members tm
        JOIN teams t ON tm.team_id = t.id
        SET tm.role = 'OWNER'
        WHERE tm.user_id = t.owner_id
    """))
    
    db.commit()
    print(f'✅ {update_result.rowcount}개의 팀 소유자 역할을 OWNER로 업데이트했습니다')
    
    # 업데이트 후 결과 확인
    result = db.execute(text("""
        SELECT t.id as team_id, t.name as team_name, t.owner_id, 
               tm.user_id, tm.role, u.email
        FROM teams t
        LEFT JOIN team_members tm ON t.id = tm.team_id
        LEFT JOIN users u ON tm.user_id = u.id
        ORDER BY t.id, tm.user_id
    """))
    rows = result.fetchall()
    
    print('\n📊 업데이트 후 팀 멤버 역할 현황:')
    for row in rows:
        print(f'  팀: {row.team_name} (ID: {row.team_id})')
        print(f'  소유자 ID: {row.owner_id}')
        print(f'  멤버: {row.email} (ID: {row.user_id})')
        print(f'  역할: {row.role}')
        print('  ---')
        
except Exception as e:
    print(f'❌ 오류 발생: {e}')
    db.rollback()
finally:
    db.close()
