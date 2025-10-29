"""
데이터베이스 연결 관리
"""
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from contextlib import contextmanager
from typing import Generator

from database.config import (
    DATABASE_URL,
    SQLALCHEMY_POOL_SIZE,
    SQLALCHEMY_MAX_OVERFLOW,
    SQLALCHEMY_POOL_TIMEOUT,
    SQLALCHEMY_POOL_RECYCLE
)
from models import Base
# 모델들을 import하여 테이블 생성 시 인식되도록 함
from models.recording import Recording
from models.segment import Segment
from models.decision import Decision
from models.action import Action

# SQLAlchemy 엔진 생성
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=SQLALCHEMY_POOL_SIZE,
    max_overflow=SQLALCHEMY_MAX_OVERFLOW,
    pool_timeout=SQLALCHEMY_POOL_TIMEOUT,
    pool_recycle=SQLALCHEMY_POOL_RECYCLE,
    echo=False,  # SQL 로그 출력 (개발 시 True)
)

# 세션 팩토리 생성
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """데이터베이스 초기화 (테이블 생성)"""
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created successfully")


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI Dependency용 DB 세션 생성기
    
    사용 예:
        @app.get("/recordings")
        def list_recordings(db: Session = Depends(get_db)):
            recordings = db.query(Recording).all()
            return recordings
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context():
    """
    Context Manager용 DB 세션
    
    사용 예:
        with get_db_context() as db:
            recording = db.query(Recording).filter_by(id=recording_id).first()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_connection():
    """데이터베이스 연결 테스트"""
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            print("✅ Database connection successful!")
            return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

