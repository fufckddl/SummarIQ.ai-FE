-- users 테이블에 is_admin 필드 추가 및 관리자 설정
ALTER TABLE users ADD COLUMN is_admin BOOLEAN DEFAULT 0 NOT NULL;
UPDATE users SET is_admin = 0 WHERE is_admin IS NULL;
UPDATE users SET is_admin = 1 WHERE id = 5;
CREATE INDEX idx_users_is_admin ON users(is_admin);
