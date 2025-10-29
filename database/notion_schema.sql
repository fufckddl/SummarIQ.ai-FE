-- Notion 연동 테이블
CREATE TABLE IF NOT EXISTS user_notion (
    user_id INT PRIMARY KEY COMMENT '사용자 ID',
    
    -- OAuth 정보 (암호화 저장)
    access_token_enc TEXT NOT NULL COMMENT '암호화된 Notion access token',
    workspace_id VARCHAR(255) COMMENT 'Notion workspace ID',
    workspace_name VARCHAR(255) COMMENT 'Notion workspace 이름',
    bot_id VARCHAR(255) COMMENT 'Notion bot ID',
    
    -- 기본 업로드 대상
    default_target_type ENUM('database', 'page') DEFAULT 'database' COMMENT '기본 대상 타입',
    default_target_id VARCHAR(255) COMMENT '기본 대상 ID (database_id 또는 page_id)',
    default_target_name VARCHAR(255) COMMENT '기본 대상 이름 (사용자 표시용)',
    
    -- 메타데이터
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    last_sync_at TIMESTAMP NULL COMMENT '마지막 동기화 시간',
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Notion 업로드 규칙 (선택적, 태그/캘린더별 라우팅)
CREATE TABLE IF NOT EXISTS notion_rules (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL COMMENT '사용자 ID',
    
    -- 매칭 조건
    matcher_type ENUM('tag', 'calendar', 'keyword') NOT NULL COMMENT '매칭 타입',
    matcher_value VARCHAR(255) NOT NULL COMMENT '매칭 값 (태그명, 캘린더ID 등)',
    
    -- 대상
    target_type ENUM('database', 'page') NOT NULL COMMENT '대상 타입',
    target_id VARCHAR(255) NOT NULL COMMENT '대상 ID',
    target_name VARCHAR(255) COMMENT '대상 이름',
    
    -- 우선순위
    priority INT DEFAULT 0 COMMENT '우선순위 (높을수록 먼저 매칭)',
    enabled BOOLEAN DEFAULT TRUE COMMENT '활성화 여부',
    
    -- 메타데이터
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user_enabled (user_id, enabled),
    INDEX idx_matcher (matcher_type, matcher_value)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Notion 업로드 이력 (디버깅 및 추적용)
CREATE TABLE IF NOT EXISTS notion_uploads (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL COMMENT '사용자 ID',
    recording_id VARCHAR(255) NOT NULL COMMENT '녹음 ID',
    
    -- Notion 정보
    target_type ENUM('database', 'page') NOT NULL,
    target_id VARCHAR(255) NOT NULL COMMENT '업로드된 대상 ID',
    notion_page_id VARCHAR(255) COMMENT '생성된 Notion 페이지 ID',
    notion_page_url TEXT COMMENT 'Notion 페이지 URL',
    
    -- 상태
    status ENUM('pending', 'success', 'failed') DEFAULT 'pending',
    error_message TEXT COMMENT '실패 시 오류 메시지',
    
    -- 메타데이터
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (recording_id) REFERENCES recordings(id) ON DELETE CASCADE,
    INDEX idx_user_recording (user_id, recording_id),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

