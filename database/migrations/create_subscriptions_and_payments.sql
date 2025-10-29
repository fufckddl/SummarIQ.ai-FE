-- 구독 및 결제 테이블 생성
-- 실행: mysql -u root -pyour-mysql-password -h 127.0.0.1 summariq < backend/database/migrations/create_subscriptions_and_payments.sql

-- Subscriptions 테이블 생성
CREATE TABLE IF NOT EXISTS subscriptions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    plan ENUM('free', 'plus', 'pro') DEFAULT 'free' NOT NULL,
    status ENUM('active', 'cancelled', 'expired', 'pending') DEFAULT 'active' NOT NULL,
    started_at DATETIME NOT NULL,
    expires_at DATETIME DEFAULT NULL,
    cancelled_at DATETIME DEFAULT NULL,
    payment_provider VARCHAR(50) DEFAULT NULL,
    payment_id VARCHAR(255) DEFAULT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP NOT NULL,
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE KEY unique_user_active (user_id, status),
    INDEX idx_user_id (user_id),
    INDEX idx_plan (plan),
    INDEX idx_status (status),
    INDEX idx_expires_at (expires_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- UsageStats 테이블 생성
CREATE TABLE IF NOT EXISTS usage_stats (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    year INT NOT NULL,
    month INT NOT NULL,
    recording_minutes INT DEFAULT 0 NOT NULL,
    recording_count INT DEFAULT 0 NOT NULL,
    ai_summary_count INT DEFAULT 0 NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP NOT NULL,
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE KEY unique_user_month (user_id, year, month),
    INDEX idx_user_id (user_id),
    INDEX idx_year_month (year, month)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Payments 테이블 생성
CREATE TABLE IF NOT EXISTS payments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    subscription_id INT DEFAULT NULL,
    amount DECIMAL(10, 2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'KRW' NOT NULL,
    payment_provider VARCHAR(50) NOT NULL,
    payment_method VARCHAR(50) DEFAULT NULL,
    payment_id VARCHAR(255) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending' NOT NULL,
    description TEXT DEFAULT NULL,
    receipt_url VARCHAR(500) DEFAULT NULL,
    paid_at DATETIME DEFAULT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP NOT NULL,
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (subscription_id) REFERENCES subscriptions(id) ON DELETE SET NULL,
    INDEX idx_user_id (user_id),
    INDEX idx_subscription_id (subscription_id),
    INDEX idx_payment_id (payment_id),
    INDEX idx_status (status),
    INDEX idx_paid_at (paid_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 모든 기존 사용자에게 FREE 플랜 부여
INSERT INTO subscriptions (user_id, plan, status, started_at)
SELECT id, 'free', 'active', NOW()
FROM users
WHERE NOT EXISTS (
    SELECT 1 FROM subscriptions WHERE subscriptions.user_id = users.id
);

SELECT 'Subscriptions, UsageStats, and Payments tables created successfully!' AS status;

