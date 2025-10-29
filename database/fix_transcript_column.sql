-- transcript 컬럼을 LONGTEXT로 변경 (대용량 전사 텍스트 지원)
-- TEXT: 최대 65KB (65,535 bytes)
-- LONGTEXT: 최대 4GB (4,294,967,295 bytes)

USE summariq;

-- transcript 컬럼 타입 변경
ALTER TABLE recordings 
MODIFY COLUMN transcript LONGTEXT COMMENT '전사 텍스트 (대용량 지원)';

-- summary 컬럼도 함께 확장 (안전 조치)
ALTER TABLE recordings 
MODIFY COLUMN summary LONGTEXT COMMENT 'AI 요약 (대용량 지원)';

-- 확인
SHOW COLUMNS FROM recordings WHERE Field IN ('transcript', 'summary');


