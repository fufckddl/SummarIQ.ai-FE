-- 사용자 음성 품질 설정 필드 추가
-- 실행: mysql -u root -pyour-mysql-password summariq < backend/database/migrations/add_audio_quality_settings_to_users.sql

DELIMITER //

DROP PROCEDURE IF EXISTS AddAudioQualitySettingsToUsers //

CREATE PROCEDURE AddAudioQualitySettingsToUsers()
BEGIN
    -- audio_quality_enabled 컬럼 추가
    IF NOT EXISTS (SELECT * FROM information_schema.COLUMNS
                   WHERE TABLE_SCHEMA = DATABASE()
                   AND TABLE_NAME = 'users'
                   AND COLUMN_NAME = 'audio_quality_enabled') THEN
        ALTER TABLE users ADD COLUMN audio_quality_enabled BOOLEAN DEFAULT TRUE;
        SELECT 'audio_quality_enabled column added to users table' AS status;
    ELSE
        SELECT 'audio_quality_enabled column already exists in users table' AS status;
    END IF;

    -- audio_quality_settings 컬럼 추가 (JSON)
    IF NOT EXISTS (SELECT * FROM information_schema.COLUMNS
                   WHERE TABLE_SCHEMA = DATABASE()
                   AND TABLE_NAME = 'users'
                   AND COLUMN_NAME = 'audio_quality_settings') THEN
        ALTER TABLE users ADD COLUMN audio_quality_settings JSON DEFAULT NULL;
        SELECT 'audio_quality_settings column added to users table' AS status;
    ELSE
        SELECT 'audio_quality_settings column already exists in users table' AS status;
    END IF;

END //

DELIMITER ;

CALL AddAudioQualitySettingsToUsers();

