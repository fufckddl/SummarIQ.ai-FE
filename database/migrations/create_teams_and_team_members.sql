-- 팀 및 팀 멤버 테이블 생성
-- 실행: mysql -u root -pyour-mysql-password summariq < backend/database/migrations/create_teams_and_team_members.sql

-- Teams 테이블 생성
CREATE TABLE IF NOT EXISTS teams (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description VARCHAR(500) DEFAULT NULL,
    owner_id INT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP NOT NULL,
    
    FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_owner_id (owner_id),
    INDEX idx_is_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- TeamMembers 테이블 생성
CREATE TABLE IF NOT EXISTS team_members (
    id INT AUTO_INCREMENT PRIMARY KEY,
    team_id INT NOT NULL,
    user_id INT NOT NULL,
    role ENUM('owner', 'admin', 'member', 'viewer') DEFAULT 'member' NOT NULL,
    joined_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    
    FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE KEY unique_team_user (team_id, user_id),
    INDEX idx_team_id (team_id),
    INDEX idx_user_id (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Recordings 테이블에 팀 관련 컬럼 추가
DELIMITER //

DROP PROCEDURE IF EXISTS AddTeamFieldsToRecordings //

CREATE PROCEDURE AddTeamFieldsToRecordings()
BEGIN
    -- team_id 컬럼 추가
    IF NOT EXISTS (SELECT * FROM information_schema.COLUMNS
                   WHERE TABLE_SCHEMA = DATABASE()
                   AND TABLE_NAME = 'recordings'
                   AND COLUMN_NAME = 'team_id') THEN
        ALTER TABLE recordings ADD COLUMN team_id INT DEFAULT NULL;
        ALTER TABLE recordings ADD FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE SET NULL;
        ALTER TABLE recordings ADD INDEX idx_team_id (team_id);
        SELECT 'team_id column added to recordings table' AS status;
    ELSE
        SELECT 'team_id column already exists in recordings table' AS status;
    END IF;

    -- is_shared 컬럼 추가 (팀 내 공유 여부)
    IF NOT EXISTS (SELECT * FROM information_schema.COLUMNS
                   WHERE TABLE_SCHEMA = DATABASE()
                   AND TABLE_NAME = 'recordings'
                   AND COLUMN_NAME = 'is_shared') THEN
        ALTER TABLE recordings ADD COLUMN is_shared BOOLEAN DEFAULT FALSE NOT NULL;
        ALTER TABLE recordings ADD INDEX idx_is_shared (is_shared);
        SELECT 'is_shared column added to recordings table' AS status;
    ELSE
        SELECT 'is_shared column already exists in recordings table' AS status;
    END IF;

    -- shared_at 컬럼 추가
    IF NOT EXISTS (SELECT * FROM information_schema.COLUMNS
                   WHERE TABLE_SCHEMA = DATABASE()
                   AND TABLE_NAME = 'recordings'
                   AND COLUMN_NAME = 'shared_at') THEN
        ALTER TABLE recordings ADD COLUMN shared_at DATETIME DEFAULT NULL;
        SELECT 'shared_at column added to recordings table' AS status;
    ELSE
        SELECT 'shared_at column already exists in recordings table' AS status;
    END IF;

END //

DELIMITER ;

CALL AddTeamFieldsToRecordings();

SELECT 'Teams and TeamMembers tables created successfully!' AS status;

