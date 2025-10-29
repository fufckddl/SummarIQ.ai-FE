-- SummarIQ 사용자 테이블 데이터 초기화
-- 모든 사용자 관련 데이터 삭제

USE summariq;

-- 1. 외래키 제약조건 임시 비활성화
SET FOREIGN_KEY_CHECKS = 0;

-- 2. 모든 사용자 관련 테이블 데이터 삭제
DELETE FROM refresh_tokens;
DELETE FROM credentials;
DELETE FROM identities;
DELETE FROM users;

-- 3. AUTO_INCREMENT 값 초기화 (0부터 시작)
ALTER TABLE users AUTO_INCREMENT = 0;
ALTER TABLE identities AUTO_INCREMENT = 0;
ALTER TABLE credentials AUTO_INCREMENT = 0;
ALTER TABLE refresh_tokens AUTO_INCREMENT = 0;

-- 4. 외래키 제약조건 재활성화
SET FOREIGN_KEY_CHECKS = 1;

-- 5. 결과 확인
SELECT 'All user data cleared successfully!' AS message;
SELECT 'Users table is now empty and ready for new data starting from ID 0' AS status;






