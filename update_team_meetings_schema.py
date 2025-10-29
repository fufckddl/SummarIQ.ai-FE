#!/usr/bin/env python3
"""
팀 회의록 테이블의 meeting_id 컬럼을 String으로 변경하고 데이터를 UUID로 업데이트
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.connection import get_db
from sqlalchemy import text

def update_team_meetings_schema():
    """팀 회의록 테이블 스키마 업데이트"""
    db = next(get_db())
    
    try:
        print("🔄 팀 회의록 테이블 스키마 업데이트 시작...")
        
        # 1. meeting_id 컬럼을 VARCHAR로 변경
        print("📝 meeting_id 컬럼을 VARCHAR로 변경...")
        db.execute(text("ALTER TABLE team_meetings MODIFY COLUMN meeting_id VARCHAR(255)"))
        
        # 2. 기존 데이터를 UUID로 업데이트
        print("🔄 기존 데이터를 UUID로 업데이트...")
        
        # meeting_id가 정수인 레코드들을 UUID로 업데이트
        result = db.execute(text("""
            SELECT tm.id, tm.meeting_id, r.id as recording_uuid
            FROM team_meetings tm
            LEFT JOIN recordings r ON tm.meeting_id = r.recording_id
            WHERE tm.meeting_id REGEXP '^[0-9]+$'
        """))
        
        updates = []
        for row in result:
            if row.recording_uuid:
                updates.append((row.id, row.recording_uuid))
                print(f"🔄 업데이트: team_meeting_id={row.id}, meeting_id={row.meeting_id} -> {row.recording_uuid}")
        
        # 업데이트 실행
        for team_meeting_id, recording_uuid in updates:
            db.execute(text("""
                UPDATE team_meetings 
                SET meeting_id = :recording_uuid 
                WHERE id = :team_meeting_id
            """), {
                'recording_uuid': recording_uuid,
                'team_meeting_id': team_meeting_id
            })
        
        db.commit()
        print("✅ 팀 회의록 테이블 업데이트 완료")
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    update_team_meetings_schema()
