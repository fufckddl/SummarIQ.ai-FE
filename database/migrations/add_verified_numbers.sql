-- 숫자 검증 시스템 필드 추가

DELIMITER //

DROP PROCEDURE IF EXISTS AddVerifiedNumbersToRecordings //

CREATE PROCEDURE AddVerifiedNumbersToRecordings()
BEGIN
    -- verified_numbers 컬럼 추가
    IF NOT EXISTS (SELECT * FROM information_schema.COLUMNS
                   WHERE TABLE_SCHEMA = DATABASE()
                   AND TABLE_NAME = 'recordings'
                   AND COLUMN_NAME = 'verified_numbers') THEN
        ALTER TABLE recordings ADD COLUMN verified_numbers JSON NULL;
        SELECT '✅ verified_numbers column added to recordings table' AS status;
    ELSE
        SELECT 'ℹ️  verified_numbers column already exists in recordings table' AS status;
    END IF;

END //

DELIMITER ;

CALL AddVerifiedNumbersToRecordings();

