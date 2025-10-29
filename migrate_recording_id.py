#!/usr/bin/env python3
"""
Recording 모델에 recording_id 컬럼 추가 및 기존 데이터 마이그레이션
"""
import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# 프로젝트 루트를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.config import DATABASE_URL

def migrate_recording_id():
    """recording_id 컬럼 추가 및 기존 데이터 마이그레이션"""
    
    # 데이터베이스 연결
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        print("🔄 Recording 테이블에 recording_id 컬럼 추가 중...")
        
        # 1. recording_id 컬럼이 이미 존재하는지 확인
        result = session.execute(text("""
            SELECT COUNT(*) as count 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = DATABASE() 
            AND TABLE_NAME = 'recordings' 
            AND COLUMN_NAME = 'recording_id'
        """)).fetchone()
        
        if result.count == 0:
            # recording_id 컬럼 추가 (auto_increment)
            session.execute(text("""
                ALTER TABLE recordings 
                ADD COLUMN recording_id INT AUTO_INCREMENT UNIQUE AFTER id
            """))
            print("✅ recording_id 컬럼 추가 완료")
        else:
            print("ℹ️ recording_id 컬럼이 이미 존재합니다")
        
        # 2. 기존 데이터에 recording_id 값 설정 (1부터 시작)
        # MySQL에서 변수 설정과 UPDATE를 분리
        session.execute(text("SET @row_number = 0"))
        session.execute(text("""
            UPDATE recordings 
            SET recording_id = (@row_number := @row_number + 1)
            WHERE recording_id IS NULL
        """))
        
        print("✅ 기존 데이터에 recording_id 값 설정 완료")
        
        # 3. team_meetings 테이블의 meeting_id를 recording_id로 업데이트
        print("🔄 team_meetings 테이블 업데이트 중...")
        
        # 먼저 team_meetings 테이블에 임시 컬럼 추가
        session.execute(text("""
            ALTER TABLE team_meetings 
            ADD COLUMN new_meeting_id INT
        """))
        
        # recordings 테이블과 조인하여 recording_id를 임시 컬럼에 복사
        session.execute(text("""
            UPDATE team_meetings tm
            JOIN recordings r ON tm.meeting_id = r.id
            SET tm.new_meeting_id = r.recording_id
        """))
        
        # 기존 meeting_id 컬럼 삭제
        session.execute(text("""
            ALTER TABLE team_meetings 
            DROP COLUMN meeting_id
        """))
        
        # 임시 컬럼을 meeting_id로 이름 변경
        session.execute(text("""
            ALTER TABLE team_meetings 
            CHANGE COLUMN new_meeting_id meeting_id INT NOT NULL
        """))
        
        print("✅ team_meetings 테이블 업데이트 완료")
        
        # 4. 변경사항 커밋
        session.commit()
        print("✅ 모든 마이그레이션 완료!")
        
    except Exception as e:
        print(f"❌ 마이그레이션 실패: {e}")
        session.rollback()
        raise
    finally:
        session.close()

if __name__ == "__main__":
    migrate_recording_id()
