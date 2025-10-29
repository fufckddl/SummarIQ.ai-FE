#!/usr/bin/env python3
"""
최종 데이터베이스 마이그레이션 - team_meetings 테이블 정리
"""
import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# 프로젝트 루트를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.config import DATABASE_URL

def final_migrate():
    """최종 데이터베이스 마이그레이션"""
    
    # 데이터베이스 연결
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        print("🔄 team_meetings 테이블 최종 정리 중...")
        
        # 1. new_meeting_id 컬럼이 있으면 삭제
        result = session.execute(text("""
            SELECT COUNT(*) as count 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = DATABASE() 
            AND TABLE_NAME = 'team_meetings' 
            AND COLUMN_NAME = 'new_meeting_id'
        """)).fetchone()
        
        if result.count > 0:
            session.execute(text("ALTER TABLE team_meetings DROP COLUMN new_meeting_id"))
            print("✅ new_meeting_id 컬럼 삭제 완료")
        
        # 2. meeting_id 컬럼이 NULL을 허용하지 않도록 수정
        session.execute(text("""
            ALTER TABLE team_meetings 
            MODIFY COLUMN meeting_id INT NOT NULL
        """))
        print("✅ meeting_id 컬럼을 NOT NULL로 수정 완료")
        
        # 3. recordings 테이블의 recording_id가 없는 경우 설정
        session.execute(text("SET @row_number = 0"))
        session.execute(text("""
            UPDATE recordings 
            SET recording_id = (@row_number := @row_number + 1)
            WHERE recording_id IS NULL
        """))
        print("✅ recordings 테이블 recording_id 설정 완료")
        
        # 4. 변경사항 커밋
        session.commit()
        print("✅ 최종 마이그레이션 완료!")
        
        # 5. 최종 상태 확인
        print("\n🔍 최종 상태 확인:")
        result = session.execute(text("""
            SELECT COUNT(*) as count FROM recordings WHERE recording_id IS NOT NULL
        """)).fetchone()
        print(f"  - recordings with recording_id: {result.count}")
        
        result = session.execute(text("""
            SELECT COUNT(*) as count FROM team_meetings
        """)).fetchone()
        print(f"  - team_meetings records: {result.count}")
        
    except Exception as e:
        print(f"❌ 마이그레이션 실패: {e}")
        session.rollback()
        raise
    finally:
        session.close()

if __name__ == "__main__":
    final_migrate()
