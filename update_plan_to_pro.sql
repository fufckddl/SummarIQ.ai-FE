-- userid = 3인 사용자의 플랜을 PRO로 변경
--  사용 방법: mysql -u root -p summariq < update_plan_to_pro.sql

USE summariq;

-- 현재 구독 정보 확인
SELECT '=== 현재 구독 정보 ===' AS '';
SELECT user_id, plan, status, started_at, expires_at 
FROM subscriptions 
WHERE user_id = 3;

-- 기존 구독이 있으면 업데이트, 없으면 삽입
INSERT INTO subscriptions (user_id, plan, status, started_at, created_at, updated_at)
VALUES (3, 'PRO', 'ACTIVE', NOW(), NOW(), NOW())
ON DUPLICATE KEY UPDATE 
    plan = 'PRO',
    status = 'ACTIVE',
    updated_at = NOW();

-- 업데이트 후 구독 정보 확인
SELECT '=== 업데이트 후 구독 정보 ===' AS '';
SELECT user_id, plan, status, started_at, expires_at 
FROM subscriptions 
WHERE user_id = 3;

SELECT '✅ 플랜이 PRO로 변경되었습니다!' AS '';

