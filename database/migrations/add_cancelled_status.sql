-- 녹음 상태에 'cancelled' 추가
DELIMITER //

DROP PROCEDURE IF EXISTS AddCancelledStatus //

CREATE PROCEDURE AddCancelledStatus()
BEGIN
    -- recordings 테이블의 status Enum에 'cancelled' 추가
    ALTER TABLE recordings 
    MODIFY COLUMN status ENUM(
        'recording', 
        'processing', 
        'stt_started', 
        'ready', 
        'failed', 
        'cancelled'  -- 추가
    ) DEFAULT 'recording';
    
    SELECT '✅ cancelled 상태 추가 완료' AS status;
END //

DELIMITER ;

CALL AddCancelledStatus();

