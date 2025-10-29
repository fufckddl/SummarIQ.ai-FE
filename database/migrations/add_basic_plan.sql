-- BASIC 플랜 추가

-- subscriptions 테이블의 plan Enum에 BASIC 추가
ALTER TABLE subscriptions 
MODIFY COLUMN plan ENUM('FREE', 'BASIC', 'PLUS', 'PRO') NOT NULL DEFAULT 'FREE';

SELECT '✅ BASIC 플랜 추가 완료' AS status;

