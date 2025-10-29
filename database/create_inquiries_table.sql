-- 문의하기 테이블 생성
CREATE TABLE inquiries (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    status ENUM('pending', 'in_progress', 'completed') DEFAULT 'pending' NOT NULL,
    
    -- 작성자 정보
    author_id INTEGER NOT NULL,
    
    -- 관리자 답변 정보
    admin_reply TEXT NULL,
    admin_reply_at DATETIME NULL,
    admin_id INTEGER NULL,
    
    -- 메타데이터
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    -- 외래키 제약조건
    FOREIGN KEY (author_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (admin_id) REFERENCES users(id) ON DELETE SET NULL,
    
    -- 인덱스
    INDEX idx_inquiries_author_id (author_id),
    INDEX idx_inquiries_status (status),
    INDEX idx_inquiries_created_at (created_at),
    INDEX idx_inquiries_admin_id (admin_id)
);
