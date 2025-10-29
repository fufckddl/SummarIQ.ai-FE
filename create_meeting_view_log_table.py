"""
meeting_view_logs 테이블 생성
"""
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

def create_meeting_view_log_table():
    print("🔄 meeting_view_logs 테이블 생성 시작...")
    session = SessionLocal()
    try:
        # meeting_view_logs 테이블 생성
        print("📝 meeting_view_logs 테이블 생성...")
        session.execute(text("""
            CREATE TABLE IF NOT EXISTS meeting_view_logs (
                id INTEGER PRIMARY KEY AUTO_INCREMENT,
                meeting_id VARCHAR(36) NOT NULL,
                user_id INTEGER NOT NULL,
                viewed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (meeting_id) REFERENCES recordings(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                UNIQUE KEY unique_user_meeting_view (user_id, meeting_id)
            );
        """))
        print("✅ meeting_view_logs 테이블 생성 완료")

        session.commit()
        print("✅ meeting_view_logs 테이블 생성 완료")

    except Exception as e:
        session.rollback()
        print(f"❌ 테이블 생성 실패: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()

if __name__ == "__main__":
    create_meeting_view_log_table()

