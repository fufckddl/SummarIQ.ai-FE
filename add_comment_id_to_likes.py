"""
team_meeting_likes 테이블에 comment_id 컬럼 추가
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

def add_comment_id_column():
    print("🔄 team_meeting_likes 테이블에 comment_id 컬럼 추가 시작...")
    session = SessionLocal()
    try:
        # 기존 데이터 삭제 (외래키 제약조건 때문에)
        print("🗑️ 기존 team_meeting_likes 데이터 삭제...")
        session.execute(text("DELETE FROM team_meeting_likes"))
        
        # comment_id 컬럼 추가 (NULL 허용)
        print("📝 comment_id 컬럼 추가...")
        session.execute(text("""
            ALTER TABLE team_meeting_likes 
            ADD COLUMN comment_id INTEGER NULL
        """))
        print("✅ comment_id 컬럼 추가 완료")

        session.commit()
        print("✅ team_meeting_likes 테이블 수정 완료")

    except Exception as e:
        session.rollback()
        print(f"❌ 테이블 수정 실패: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()

if __name__ == "__main__":
    add_comment_id_column()

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

def add_comment_id_column():
    print("🔄 team_meeting_likes 테이블에 comment_id 컬럼 추가 시작...")
    session = SessionLocal()
    try:
        # 기존 데이터 삭제 (외래키 제약조건 때문에)
        print("🗑️ 기존 team_meeting_likes 데이터 삭제...")
        session.execute(text("DELETE FROM team_meeting_likes"))
        
        # comment_id 컬럼 추가 (NULL 허용)
        print("📝 comment_id 컬럼 추가...")
        session.execute(text("""
            ALTER TABLE team_meeting_likes 
            ADD COLUMN comment_id INTEGER NULL
        """))
        print("✅ comment_id 컬럼 추가 완료")

        session.commit()
        print("✅ team_meeting_likes 테이블 수정 완료")

    except Exception as e:
        session.rollback()
        print(f"❌ 테이블 수정 실패: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()

if __name__ == "__main__":
    add_comment_id_column()
