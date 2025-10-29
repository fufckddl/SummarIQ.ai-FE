-- 공지사항 테이블 생성
CREATE TABLE announcements (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    view_count INT DEFAULT 0 NOT NULL,
    author_id INT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    -- 외래키 제약조건
    FOREIGN KEY (author_id) REFERENCES users(id) ON DELETE CASCADE,
    
    -- 인덱스
    INDEX idx_announcements_active (is_active),
    INDEX idx_announcements_created (created_at),
    INDEX idx_announcements_author (author_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 샘플 데이터 삽입 (선택사항)
INSERT INTO announcements (title, content, author_id) VALUES 
('SummarIQ 서비스 오픈 안내', 'SummarIQ AI 회의 비서 서비스가 정식 오픈되었습니다. 많은 이용 부탁드립니다.', 1),
('새로운 기능 업데이트', '회의록 자동 생성 및 Notion 연동 기능이 추가되었습니다.', 1),
('서비스 점검 안내', '2024년 1월 15일 새벽 2시-4시 서비스 점검이 예정되어 있습니다.', 1);
