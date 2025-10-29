-- recordings 테이블에 stt_started 상태 추가

ALTER TABLE recordings 
MODIFY COLUMN status ENUM('recording', 'processing', 'stt_started', 'ready', 'failed') NULL;

SELECT '✅ stt_started status added to recordings table' AS status;

