"""
팀 회의록 테이블 업데이트 스크립트
meeting_id 컬럼을 INTEGER에서 VARCHAR로 변경
"""
import pymysql
from database.connection import engine
from models import Base
from models.team_meeting import TeamMeeting
from models.team import Team

def update_team_meetings_table():
    print("Updating team_meetings table...")
    
    # 기존 테이블 삭제 후 재생성
    try:
        # 테이블 삭제
        with engine.connect() as conn:
            conn.execute("DROP TABLE IF EXISTS team_meetings")
            conn.commit()
        print("✅ 기존 team_meetings 테이블 삭제 완료")
        
        # 새 테이블 생성
        Base.metadata.create_all(engine)
        print("✅ 새로운 team_meetings 테이블 생성 완료")
        
    except Exception as e:
        print(f"❌ 테이블 업데이트 실패: {e}")
        raise

if __name__ == "__main__":
    update_team_meetings_table()
