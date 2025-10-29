-- 구독 플랜 및 상태 Enum 값을 대문자로 통일

-- 1. plan 컬럼 Enum 값 수정
ALTER TABLE subscriptions 
MODIFY COLUMN plan ENUM('FREE', 'PLUS', 'PRO') NOT NULL DEFAULT 'FREE';

-- 2. 기존 데이터 업데이트
UPDATE subscriptions SET plan = 'FREE' WHERE plan = 'free';
UPDATE subscriptions SET plan = 'PLUS' WHERE plan = 'plus';
UPDATE subscriptions SET plan = 'PRO' WHERE plan = 'pro';

-- 3. status 컬럼 Enum 값 수정
ALTER TABLE subscriptions 
MODIFY COLUMN status ENUM('ACTIVE', 'CANCELLED', 'EXPIRED', 'PENDING') NOT NULL DEFAULT 'ACTIVE';

-- 4. 기존 데이터 업데이트
UPDATE subscriptions SET status = 'ACTIVE' WHERE status = 'active';
UPDATE subscriptions SET status = 'CANCELLED' WHERE status = 'cancelled';
UPDATE subscriptions SET status = 'EXPIRED' WHERE status = 'expired';
UPDATE subscriptions SET status = 'PENDING' WHERE status = 'pending';

SELECT '✅ Subscription Enum 값 대문자로 업데이트 완료' AS status;

