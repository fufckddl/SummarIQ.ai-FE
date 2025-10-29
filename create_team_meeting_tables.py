"""
팀 회의 댓글 및 좋아요 테이블 생성 스크립트
"""
import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# 데이터베이스 연결 설정
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("DATABASE_URL 환경 변수가 설정되지 않았습니다.")
    sys.exit(1)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def create_team_meeting_tables():
    print("🔄 팀 회의 댓글 및 좋아요 테이블 생성 시작...")
    session = SessionLocal()
    try:
        # 1. 팀 회의 댓글 테이블 생성
        print("📝 team_meeting_comments 테이블 생성...")
        session.execute(text("""
            CREATE TABLE IF NOT EXISTS team_meeting_comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                team_meeting_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                parent_id INTEGER NULL,
                content TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                is_deleted BOOLEAN DEFAULT 0,
                FOREIGN KEY (team_meeting_id) REFERENCES team_meetings(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (parent_id) REFERENCES team_meeting_comments(id) ON DELETE CASCADE
            );
        """))
        print("✅ team_meeting_comments 테이블 생성 완료")

        # 2. 팀 회의 좋아요 테이블 생성
        print("📝 team_meeting_likes 테이블 생성...")
        session.execute(text("""
            CREATE TABLE IF NOT EXISTS team_meeting_likes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                team_meeting_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,r
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (team_meeting_id) REFERENCES team_meetings(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                UNIQUE(team_meeting_id, user_id)
            );
        """))
        print("✅ team_meeting_likes 테이블 생성 완료")

        session.commit()
        print("✅ 팀 회의 댓글 및 좋아요 테이블 생성 완료")

    except Exception as e:
        session.rollback()
        print(f"❌ 테이블 생성 실패: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()

if __name__ == "__main__":
    create_team_meeting_tables()
