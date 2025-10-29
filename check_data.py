#!/usr/bin/env python3
"""
데이터베이스 현재 상태 확인
"""
import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# 프로젝트 루트를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.config import DATABASE_URL

def check_data():
    """데이터베이스 현재 상태 확인"""
    
    # 데이터베이스 연결
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        print("🔍 recordings 테이블 상태 확인:")
        result = session.execute(text("""
            SELECT id, recording_id, title 
            FROM recordings 
            LIMIT 5
        """)).fetchall()
        
        for row in result:
            print(f"  - id: {row.id}, recording_id: {row.recording_id}, title: {row.title}")
        
        print("\n🔍 team_meetings 테이블 상태 확인:")
        result = session.execute(text("""
            SELECT id, team_id, meeting_id, shared_by 
            FROM team_meetings 
            LIMIT 5
        """)).fetchall()
        
        for row in result:
            print(f"  - id: {row.id}, team_id: {row.team_id}, meeting_id: {row.meeting_id}, shared_by: {row.shared_by}")
        
        print("\n🔍 team_meetings와 recordings 조인 테스트:")
        result = session.execute(text("""
            SELECT tm.id, tm.meeting_id, r.id as recording_id, r.recording_id as r_recording_id
            FROM team_meetings tm
            LEFT JOIN recordings r ON tm.meeting_id = r.id
            LIMIT 5
        """)).fetchall()
        
        for row in result:
            print(f"  - tm.id: {row.id}, tm.meeting_id: {row.meeting_id}, r.id: {row.recording_id}, r.recording_id: {row.r_recording_id}")
        
    except Exception as e:
        print(f"❌ 확인 실패: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    check_data()
