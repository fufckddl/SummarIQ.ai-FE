-- 태그 및 즐겨찾기 기능 추가
-- 실행: mysql -u root -pyour-mysql-password -h 127.0.0.1 summariq < backend/database/migrations/create_tags_and_favorites.sql

-- Tags 테이블 생성
CREATE TABLE IF NOT EXISTS tags (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,
    color VARCHAR(7) DEFAULT NULL,
    usage_count INT DEFAULT 0 NOT NULL,
    created_by INT DEFAULT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP NOT NULL,
    
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL,
    INDEX idx_name (name),
    INDEX idx_usage_count (usage_count)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- RecordingTags 연결 테이블 생성
CREATE TABLE IF NOT EXISTS recording_tags (
    recording_id VARCHAR(36) NOT NULL,
    tag_id INT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    
    PRIMARY KEY (recording_id, tag_id),
    FOREIGN KEY (recording_id) REFERENCES recordings(id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE,
    INDEX idx_recording_id (recording_id),
    INDEX idx_tag_id (tag_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Recordings 테이블에 즐겨찾기 필드 추가
DELIMITER //

DROP PROCEDURE IF EXISTS AddFavoriteFieldsToRecordings //

CREATE PROCEDURE AddFavoriteFieldsToRecordings()
BEGIN
    -- is_favorite 컬럼 추가
    IF NOT EXISTS (SELECT * FROM information_schema.COLUMNS
                   WHERE TABLE_SCHEMA = DATABASE()
                   AND TABLE_NAME = 'recordings'
                   AND COLUMN_NAME = 'is_favorite') THEN
        ALTER TABLE recordings ADD COLUMN is_favorite BOOLEAN DEFAULT FALSE NOT NULL;
        ALTER TABLE recordings ADD INDEX idx_is_favorite (is_favorite);
        SELECT 'is_favorite column added to recordings table' AS status;
    ELSE
        SELECT 'is_favorite column already exists in recordings table' AS status;
    END IF;

    -- favorited_at 컬럼 추가
    IF NOT EXISTS (SELECT * FROM information_schema.COLUMNS
                   WHERE TABLE_SCHEMA = DATABASE()
                   AND TABLE_NAME = 'recordings'
                   AND COLUMN_NAME = 'favorited_at') THEN
        ALTER TABLE recordings ADD COLUMN favorited_at DATETIME DEFAULT NULL;
        SELECT 'favorited_at column added to recordings table' AS status;
    ELSE
        SELECT 'favorited_at column already exists in recordings table' AS status;
    END IF;

END //

DELIMITER ;

CALL AddFavoriteFieldsToRecordings();

-- 기본 태그 데이터 삽입
INSERT IGNORE INTO tags (name, color) VALUES
('기획회의', '#FF6B6B'),
('개발미팅', '#4ECDC4'),
('디자인리뷰', '#95E1D3'),
('팀회의', '#FFA07A'),
('고객미팅', '#FFD93D'),
('브레인스토밍', '#A8E6CF'),
('프로젝트회의', '#6C5CE7'),
('1on1', '#FD79A8'),
('전사회의', '#74B9FF'),
('스프린트', '#55EFC4');

SELECT 'Tags and Favorites feature created successfully!' AS status;

