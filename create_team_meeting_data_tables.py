import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("DATABASE_URL 환경 변수가 설정되지 않았습니다.")
    sys.exit(1)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def create_team_meeting_data_tables():
    print("🔄 팀 회의 데이터 테이블 생성 시작...")
    session = SessionLocal()
    try:
        # 1. 팀 액션 아이템 테이블 생성
        print("📝 team_actions 테이블 생성...")
        session.execute(text("""
            CREATE TABLE IF NOT EXISTS team_actions (
                id INTEGER PRIMARY KEY AUTO_INCREMENT,
                team_meeting_id INTEGER NOT NULL,
                content TEXT NOT NULL,
                completed BOOLEAN DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (team_meeting_id) REFERENCES team_meetings(id) ON DELETE CASCADE
            );
        """))
        print("✅ team_actions 테이블 생성 완료")

        # 2. 팀 결정사항 테이블 생성
        print("📝 team_decisions 테이블 생성...")
        session.execute(text("""
            CREATE TABLE IF NOT EXISTS team_decisions (
                id INTEGER PRIMARY KEY AUTO_INCREMENT,
                team_meeting_id INTEGER NOT NULL,
                content TEXT NOT NULL,
                completed BOOLEAN DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (team_meeting_id) REFERENCES team_meetings(id) ON DELETE CASCADE
            );
        """))
        print("✅ team_decisions 테이블 생성 완료")

        # 3. 팀 태그 테이블 생성
        print("📝 team_tags 테이블 생성...")
        session.execute(text("""
            CREATE TABLE IF NOT EXISTS team_tags (
                id INTEGER PRIMARY KEY AUTO_INCREMENT,
                team_meeting_id INTEGER NOT NULL,
                name VARCHAR(100) NOT NULL,
                color VARCHAR(20),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (team_meeting_id) REFERENCES team_meetings(id) ON DELETE CASCADE
            );
        """))
        print("✅ team_tags 테이블 생성 완료")

        session.commit()
        print("✅ 팀 회의 데이터 테이블 생성 완료")

    except Exception as e:
        session.rollback()
        print(f"❌ 테이블 생성 실패: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()

if __name__ == "__main__":
    create_team_meeting_data_tables()

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("DATABASE_URL 환경 변수가 설정되지 않았습니다.")
    sys.exit(1)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def create_team_meeting_data_tables():
    print("🔄 팀 회의 데이터 테이블 생성 시작...")
    session = SessionLocal()
    try:
        # 1. 팀 액션 아이템 테이블 생성
        print("📝 team_actions 테이블 생성...")
        session.execute(text("""
            CREATE TABLE IF NOT EXISTS team_actions (
                id INTEGER PRIMARY KEY AUTO_INCREMENT,
                team_meeting_id INTEGER NOT NULL,
                content TEXT NOT NULL,
                completed BOOLEAN DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (team_meeting_id) REFERENCES team_meetings(id) ON DELETE CASCADE
            );
        """))
        print("✅ team_actions 테이블 생성 완료")

        # 2. 팀 결정사항 테이블 생성
        print("📝 team_decisions 테이블 생성...")
        session.execute(text("""
            CREATE TABLE IF NOT EXISTS team_decisions (
                id INTEGER PRIMARY KEY AUTO_INCREMENT,
                team_meeting_id INTEGER NOT NULL,
                content TEXT NOT NULL,
                completed BOOLEAN DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (team_meeting_id) REFERENCES team_meetings(id) ON DELETE CASCADE
            );
        """))
        print("✅ team_decisions 테이블 생성 완료")

        # 3. 팀 태그 테이블 생성
        print("📝 team_tags 테이블 생성...")
        session.execute(text("""
            CREATE TABLE IF NOT EXISTS team_tags (
                id INTEGER PRIMARY KEY AUTO_INCREMENT,
                team_meeting_id INTEGER NOT NULL,
                name VARCHAR(100) NOT NULL,
                color VARCHAR(20),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (team_meeting_id) REFERENCES team_meetings(id) ON DELETE CASCADE
            );
        """))
        print("✅ team_tags 테이블 생성 완료")

        session.commit()
        print("✅ 팀 회의 데이터 테이블 생성 완료")

    except Exception as e:
        session.rollback()
        print(f"❌ 테이블 생성 실패: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()

if __name__ == "__main__":
    create_team_meeting_data_tables()
