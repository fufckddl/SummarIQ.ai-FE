"""
task_status 테이블 생성 스크립트
"""
from database.connection import get_db_context
from sqlalchemy import text

def init_task_table():
    """task_status 테이블 생성"""
    
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS task_status (
        id VARCHAR(255) PRIMARY KEY COMMENT 'Celery task ID 또는 SQS message ID',
        recording_id VARCHAR(255) NOT NULL COMMENT '연결된 녹음 ID',
        task_type VARCHAR(50) NOT NULL COMMENT 'stt, summary, etc',
        status VARCHAR(50) NOT NULL COMMENT 'pending, processing, completed, failed',
        backend VARCHAR(50) DEFAULT 'celery' COMMENT 'celery, sqs, lambda',
        
        progress INT DEFAULT 0 COMMENT '진행률 0-100',
        current_step VARCHAR(100) COMMENT '현재 단계',
        
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        started_at TIMESTAMP NULL,
        completed_at TIMESTAMP NULL,
        
        result JSON COMMENT '작업 결과',
        error_message TEXT COMMENT '오류 메시지',
        retry_count INT DEFAULT 0 COMMENT '재시도 횟수',
        
        INDEX idx_recording (recording_id),
        INDEX idx_status (status),
        INDEX idx_created (created_at),
        
        FOREIGN KEY (recording_id) REFERENCES recordings(id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """
    
    try:
        with get_db_context() as db:
            print("📝 task_status 테이블 생성 중...")
            db.execute(text(create_table_sql))
            db.commit()
            print("✅ task_status 테이블 생성 완료")
            
            # 테이블 확인
            result = db.execute(text("SHOW TABLES LIKE 'task_status'")).fetchone()
            if result:
                print("✅ 테이블 확인됨: task_status")
            else:
                print("❌ 테이블 생성 실패")
                
    except Exception as e:
        print(f"❌ 테이블 생성 오류: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    init_task_table()

