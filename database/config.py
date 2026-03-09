"""
데이터베이스 및 서버 설정
"""
import os
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# MySQL 설정 (환경변수 우선)
MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "summariq")

# 서버 설정 (환경변수 우선)
SERVER_HOST = os.getenv("SERVER_HOST")
SERVER_PORT = int(os.getenv("SERVER_PORT", "8000"))

if not SERVER_HOST:
    raise ValueError(
        "SERVER_HOST 환경변수가 설정되지 않았습니다.\n"
        ".env 파일에 SERVER_HOST=192.168.0.xxx 를 추가하세요.\n"
        "현재 IP 확인: ifconfig | grep 'inet ' | grep -v 127.0.0.1"
    )

SERVER_BASE_URL = f"http://{SERVER_HOST}:{SERVER_PORT}"

print(f"📡 서버 설정 로드:")
print(f"   - SERVER_HOST: {SERVER_HOST}")
print(f"   - SERVER_PORT: {SERVER_PORT}")
print(f"   - SERVER_BASE_URL: {SERVER_BASE_URL}")

# SQLAlchemy 연결 URL
DATABASE_URL = f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}?charset=utf8mb4"

# 연결 풀 설정
SQLALCHEMY_POOL_SIZE = 10
SQLALCHEMY_MAX_OVERFLOW = 20
SQLALCHEMY_POOL_TIMEOUT = 30
SQLALCHEMY_POOL_RECYCLE = 3600
