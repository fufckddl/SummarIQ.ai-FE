-- users 테이블의 id 필드를 AUTO_INCREMENT INT로 수정
USE summariq;

-- 1. 외래키 제약조건 임시 비활성화
SET FOREIGN_KEY_CHECKS = 0;

-- 2. 기존 외래키 제약조건 삭제 (오류 무시)
ALTER TABLE identities DROP FOREIGN KEY identities_ibfk_1;
ALTER TABLE credentials DROP FOREIGN KEY credentials_ibfk_1;
ALTER TABLE refresh_tokens DROP FOREIGN KEY refresh_tokens_ibfk_1;
ALTER TABLE recordings DROP FOREIGN KEY fk_recordings_user_id;

-- 3. users 테이블의 id 필드를 INT AUTO_INCREMENT로 변경
ALTER TABLE users MODIFY COLUMN id INT AUTO_INCREMENT PRIMARY KEY;

-- 4. 다른 테이블들의 user_id 필드도 INT로 변경
ALTER TABLE identities MODIFY COLUMN user_id INT;
ALTER TABLE credentials MODIFY COLUMN user_id INT;
ALTER TABLE refresh_tokens MODIFY COLUMN user_id INT;
ALTER TABLE recordings MODIFY COLUMN user_id INT;

-- 5. 외래키 제약조건 재추가
ALTER TABLE identities ADD CONSTRAINT identities_ibfk_1 FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
ALTER TABLE credentials ADD CONSTRAINT credentials_ibfk_1 FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
ALTER TABLE refresh_tokens ADD CONSTRAINT refresh_tokens_ibfk_1 FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
ALTER TABLE recordings ADD CONSTRAINT fk_recordings_user_id FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL;

-- 6. AUTO_INCREMENT 값 초기화
ALTER TABLE users AUTO_INCREMENT = 0;

-- 7. 외래키 제약조건 재활성화
SET FOREIGN_KEY_CHECKS = 1;

-- 8. 결과 확인
SELECT 'Users table fixed successfully!' AS message;
DESCRIBE users;
