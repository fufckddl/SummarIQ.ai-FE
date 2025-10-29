-- FCM 관련 필드를 users 테이블에 추가하는 마이그레이션
-- 2024년 실행

-- fcm_token 컬럼 추가 (이미 존재하면 건너뛰기)
SET @preparedStatement = (SELECT IF(
  (
    SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE table_name = 'users'
    AND table_schema = DATABASE()
    AND column_name = 'fcm_token'
  ) > 0,
  'SELECT 1',
  'ALTER TABLE users ADD COLUMN fcm_token VARCHAR(512) NULL'
));
PREPARE alterIfNotExists FROM @preparedStatement;
EXECUTE alterIfNotExists;
DEALLOCATE PREPARE alterIfNotExists;

-- platform 컬럼 추가 (이미 존재하면 건너뛰기)
SET @preparedStatement = (SELECT IF(
  (
    SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE table_name = 'users'
    AND table_schema = DATABASE()
    AND column_name = 'platform'
  ) > 0,
  'SELECT 1',
  'ALTER TABLE users ADD COLUMN platform VARCHAR(20) NULL COMMENT ''ios, android'''
));
PREPARE alterIfNotExists FROM @preparedStatement;
EXECUTE alterIfNotExists;
DEALLOCATE PREPARE alterIfNotExists;

-- fcm_token 인덱스 추가 (이미 존재하면 건너뛰기)
SET @preparedStatement = (SELECT IF(
  (
    SELECT COUNT(*) FROM INFORMATION_SCHEMA.STATISTICS
    WHERE table_name = 'users'
    AND table_schema = DATABASE()
    AND index_name = 'idx_fcm_token'
  ) > 0,
  'SELECT 1',
  'ALTER TABLE users ADD INDEX idx_fcm_token (fcm_token)'
));
PREPARE alterIfNotExists FROM @preparedStatement;
EXECUTE alterIfNotExists;
DEALLOCATE PREPARE alterIfNotExists;

SELECT 'FCM fields migration completed successfully' AS status;
