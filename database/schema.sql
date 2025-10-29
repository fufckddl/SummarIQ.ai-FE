-- SummarIQ Database Schema
-- 생성일: 2025-10-10

-- 데이터베이스 생성 (UTF-8 인코딩)
CREATE DATABASE IF NOT EXISTS summariq 
CHARACTER SET utf8mb4 
COLLATE utf8mb4_unicode_ci;

USE summariq;

-- 1. 녹음(recordings) 테이블
CREATE TABLE IF NOT EXISTS recordings (
    id VARCHAR(36) PRIMARY KEY COMMENT '녹음 ID (UUID)',
    title VARCHAR(255) NOT NULL COMMENT '녹음 제목 (AI 자동 생성)',
    status ENUM('recording', 'processing', 'ready', 'failed') DEFAULT 'recording' COMMENT '처리 상태',
    
    -- 메타데이터
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '생성 시간',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '수정 시간',
    duration INT DEFAULT 0 COMMENT '녹음 길이 (밀리초)',
    lang_auto VARCHAR(10) DEFAULT 'ko-KR' COMMENT '자동 감지 언어',
    
    -- 파일 정보
    audio_url VARCHAR(500) COMMENT '오디오 파일 경로/URL',
    local_audio_path VARCHAR(500) COMMENT '로컬 오디오 파일 경로',
    
    -- 전사 및 요약
    transcript TEXT COMMENT '전체 전사 텍스트',
    summary TEXT COMMENT 'AI 생성 요약',
    
    -- 사용자 정보 (향후 확장)
    user_id VARCHAR(36) COMMENT '사용자 ID',
    
    INDEX idx_status (status),
    INDEX idx_created_at (created_at),
    INDEX idx_user_id (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='녹음 메인 테이블';

-- 2. 세그먼트(segments) 테이블
CREATE TABLE IF NOT EXISTS segments (
    id VARCHAR(50) PRIMARY KEY COMMENT '세그먼트 ID',
    recording_id VARCHAR(36) NOT NULL COMMENT '녹음 ID',
    seq INT NOT NULL COMMENT '세그먼트 순서',
    
    -- 오디오 정보
    audio_url VARCHAR(500) COMMENT '세그먼트 오디오 URL',
    start_ms INT NOT NULL COMMENT '시작 시간 (밀리초)',
    end_ms INT NOT NULL COMMENT '종료 시간 (밀리초)',
    
    -- STT 결과
    text TEXT NOT NULL COMMENT '변환된 텍스트',
    lang VARCHAR(10) DEFAULT 'ko-KR' COMMENT '언어',
    confidence DECIMAL(4, 3) DEFAULT 0.95 COMMENT 'STT 신뢰도 (0.0~1.0)',
    
    -- 화자 정보 (JSON)
    speakers JSON COMMENT '화자 정보',
    
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (recording_id) REFERENCES recordings(id) ON DELETE CASCADE,
    INDEX idx_recording_seq (recording_id, seq),
    INDEX idx_recording_id (recording_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='녹음 세그먼트 테이블';

-- 3. 의사결정(decisions) 테이블
CREATE TABLE IF NOT EXISTS decisions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    recording_id VARCHAR(36) NOT NULL COMMENT '녹음 ID',
    decision TEXT NOT NULL COMMENT '의사결정 내용',
    decision_order INT NOT NULL DEFAULT 0 COMMENT '순서',
    
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (recording_id) REFERENCES recordings(id) ON DELETE CASCADE,
    INDEX idx_recording_id (recording_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='회의 의사결정 테이블';

-- 4. 액션 아이템(actions) 테이블
CREATE TABLE IF NOT EXISTS actions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    recording_id VARCHAR(36) NOT NULL COMMENT '녹음 ID',
    
    task TEXT NOT NULL COMMENT '할 일',
    owner VARCHAR(100) COMMENT '담당자',
    due_date DATE COMMENT '마감일',
    priority ENUM('low', 'medium', 'high') DEFAULT 'medium' COMMENT '우선순위',
    completed BOOLEAN DEFAULT FALSE COMMENT '완료 여부',
    action_order INT NOT NULL DEFAULT 0 COMMENT '순서',
    
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (recording_id) REFERENCES recordings(id) ON DELETE CASCADE,
    INDEX idx_recording_id (recording_id),
    INDEX idx_completed (completed)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='액션 아이템 테이블';

-- 초기 데이터 확인
SELECT 'Database and tables created successfully!' AS message;
SHOW TABLES;

