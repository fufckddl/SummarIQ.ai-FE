#!/usr/bin/env python3
"""
기존 team_meetings 데이터 정리 및 새로운 방식으로 마이그레이션
"""
import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# 프로젝트 루트를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.config import DATABASE_URL

def clean_migrate():
    """기존 데이터 정리 및 새로운 방식으로 마이그레이션"""
    
    # 데이터베이스 연결
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        print("🔄 기존 team_meetings 데이터 정리 중...")
        
        # 1. 기존 team_meetings 데이터 삭제 (해시된 값으로는 매칭 불가)
        session.execute(text("DELETE FROM team_meetings"))
        print("✅ 기존 team_meetings 데이터 삭제 완료")
        
        # 2. recordings 테이블에 recording_id가 없는 경우 설정
        session.execute(text("SET @row_number = 0"))
        session.execute(text("""
            UPDATE recordings 
            SET recording_id = (@row_number := @row_number + 1)
            WHERE recording_id IS NULL
        """))
        print("✅ recordings 테이블 recording_id 설정 완료")
        
        # 3. 변경사항 커밋
        session.commit()
        print("✅ 모든 정리 작업 완료!")
        print("ℹ️ 이제 새로운 회의록을 팀에 공유하면 auto_increment ID가 사용됩니다.")
        
    except Exception as e:
        print(f"❌ 정리 실패: {e}")
        session.rollback()
        raise
    finally:
        session.close()

if __name__ == "__main__":
    clean_migrate()
