-- 1단계 필드 추가: Q&A, 미결 사항, 핵심 인사이트
-- 실행 방법: mysql -u root -p summariq < backend/database/add_phase1_fields.sql

USE summariq;

ALTER TABLE recordings
ADD COLUMN questions_answers JSON COMMENT 'Q&A 목록 (질문과 답변)',
ADD COLUMN open_issues JSON COMMENT '미결 사항 (추가 논의 필요)',
ADD COLUMN key_insights JSON COMMENT '핵심 인사이트 (AI 발견)';

-- 확인
DESCRIBE recordings;

