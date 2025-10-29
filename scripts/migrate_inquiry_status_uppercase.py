import os
from sqlalchemy import create_engine, text

# DATABASE_URL 은 기존 설정에서 가져옵니다.
DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    # fallback: 기존 config를 import 시도 (프로젝트 구조에 맞춤)
    try:
        from database.config import DATABASE_URL as CONFIG_DB_URL  # type: ignore
        DATABASE_URL = CONFIG_DB_URL
    except Exception:
        raise RuntimeError("DATABASE_URL이 설정되어 있지 않습니다. 환경변수 또는 database.config를 확인하세요.")

engine = create_engine(DATABASE_URL)

STATEMENTS = [
    # 소문자 값을 대문자로 정규화
    "UPDATE inquiries SET status='PENDING' WHERE status='pending';",
    "UPDATE inquiries SET status='IN_PROGRESS' WHERE status='in_progress';",
    "UPDATE inquiries SET status='COMPLETED' WHERE status='completed';",
]

with engine.begin() as conn:
    for stmt in STATEMENTS:
        conn.execute(text(stmt))

print("✅ inquiries.status 값이 대문자로 정규화되었습니다.")
