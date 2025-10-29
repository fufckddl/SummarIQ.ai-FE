-- users 테이블에 is_admin 필드 추가
-- 기본값: 0 (일반 사용자), 1 (관리자)

ALTER TABLE users 
ADD COLUMN is_admin BOOLEAN DEFAULT 0 NOT NULL;

-- 기존 사용자들은 모두 일반 사용자(0)로 설정
UPDATE users SET is_admin = 0 WHERE is_admin IS NULL;

-- 특정 사용자를 관리자로 설정 (예: user_id = 5)
-- UPDATE users SET is_admin = 1 WHERE id = 5;

-- 인덱스 추가 (선택사항)
CREATE INDEX idx_users_is_admin ON users(is_admin);
