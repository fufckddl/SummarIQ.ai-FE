-- 작업 상태 테이블 (큐 시스템 독립적)
CREATE TABLE IF NOT EXISTS task_status (
    id VARCHAR(255) PRIMARY KEY COMMENT 'Celery task ID 또는 SQS message ID',
    recording_id VARCHAR(255) NOT NULL COMMENT '연결된 녹음 ID',
    task_type VARCHAR(50) NOT NULL COMMENT 'stt, summary, etc',
    status VARCHAR(50) NOT NULL COMMENT 'pending, processing, completed, failed',
    backend VARCHAR(50) DEFAULT 'celery' COMMENT 'celery, sqs, lambda',
    
    -- 진행 상태
    progress INT DEFAULT 0 COMMENT '진행률 0-100',
    current_step VARCHAR(100) COMMENT '현재 단계',
    
    -- 시간 정보
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP NULL,
    completed_at TIMESTAMP NULL,
    
    -- 결과 및 오류
    result JSON COMMENT '작업 결과',
    error_message TEXT COMMENT '오류 메시지',
    retry_count INT DEFAULT 0 COMMENT '재시도 횟수',
    
    -- 인덱스
    INDEX idx_recording (recording_id),
    INDEX idx_status (status),
    INDEX idx_created (created_at),
    
    FOREIGN KEY (recording_id) REFERENCES recordings(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

