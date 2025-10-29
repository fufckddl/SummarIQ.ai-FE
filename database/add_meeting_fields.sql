-- recordings 테이블에 meeting 관련 필드 추가
-- 참석자, 태그, 상태 필드를 추가합니다

USE summariq;

-- participants 필드 추가 (JSON 형태로 저장)
ALTER TABLE recordings 
ADD COLUMN participants JSON COMMENT '참석자 목록 (JSON 배열)';

-- tags 필드 추가 (JSON 형태로 저장)  
ALTER TABLE recordings 
ADD COLUMN tags JSON COMMENT '태그 목록 (JSON 배열)';

-- meeting_status 필드 추가 (회의 상태)
ALTER TABLE recordings 
ADD COLUMN meeting_status VARCHAR(20) DEFAULT '완료' COMMENT '회의 상태 (예정, 진행중, 완료, 취소)';

-- 인덱스 추가
ALTER TABLE recordings 
ADD INDEX idx_meeting_status (meeting_status);

SELECT 'Meeting fields added successfully!' AS message;
