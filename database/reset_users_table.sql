-- SummarIQ 사용자 테이블 초기화 및 ID 필드 수정
-- ID를 AUTO_INCREMENT INT로 변경하고 0부터 시작

USE summariq;

-- 1. 외래키 제약조건 임시 비활성화
SET FOREIGN_KEY_CHECKS = 0;

-- 2. 기존 테이블들 삭제 (의존성 순서대로)
DROP TABLE IF EXISTS refresh_tokens;
DROP TABLE IF EXISTS credentials;
DROP TABLE IF EXISTS identities;
DROP TABLE IF EXISTS users;

-- 3. users 테이블 재생성 (AUTO_INCREMENT INT, 0부터 시작)
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '사용자 ID (AUTO_INCREMENT, 0부터 시작)',
    
    -- 기본 정보
    email VARCHAR(255) UNIQUE COMMENT '이메일 (선택, 외부 로그인 시 제공될 수 있음)',
    email_verified BOOLEAN DEFAULT FALSE COMMENT '이메일 검증 여부',
    display_name VARCHAR(100) COMMENT '표시 이름',
    avatar_url TEXT COMMENT '프로필 이미지 URL',
    
    -- 메타데이터
    locale VARCHAR(10) DEFAULT 'ko-KR' COMMENT '언어/지역',
    created_via VARCHAR(20) NOT NULL DEFAULT 'local' COMMENT '가입 경로 (local|kakao|google|naver|apple)',
    
    -- 타임스탬프
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    last_login_at DATETIME COMMENT '마지막 로그인 시간',
    
    -- 인덱스
    INDEX idx_email (email),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci 
AUTO_INCREMENT=0 COMMENT='사용자 테이블';

-- 4. identities 테이블 재생성
CREATE TABLE identities (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL COMMENT '사용자 ID',
    
    -- OAuth 프로바이더 정보
    provider VARCHAR(20) NOT NULL COMMENT 'kakao|google|naver|apple',
    subject VARCHAR(255) NOT NULL COMMENT '프로바이더 사용자 ID (sub)',
    
    -- 프로필 정보
    email_verified BOOLEAN DEFAULT NULL COMMENT '프로바이더의 이메일 검증 여부',
    profile_name VARCHAR(100) COMMENT '프로바이더 표시 이름',
    profile_picture TEXT COMMENT '프로파일 이미지 URL',
    
    -- 메타데이터
    raw_profile JSON COMMENT '프로바이더 원본 프로필 (디버깅용)',
    
    -- 타임스탬프
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    -- 외래키 및 인덱스
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE KEY uk_provider_subject (provider, subject),
    INDEX idx_user_id (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='외부 인증 연동 테이블';

-- 5. credentials 테이블 재생성
CREATE TABLE credentials (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL UNIQUE COMMENT '사용자 ID',
    
    -- 비밀번호
    password_hash VARCHAR(255) NOT NULL COMMENT 'bcrypt 해시',
    
    -- 타임스탬프
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    -- 외래키
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='로컬 비밀번호 인증 테이블';

-- 6. refresh_tokens 테이블 재생성
CREATE TABLE refresh_tokens (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL COMMENT '사용자 ID',
    
    -- 토큰 정보
    token_hash VARCHAR(255) NOT NULL UNIQUE COMMENT '리프레시 토큰 해시',
    family_id VARCHAR(36) NOT NULL COMMENT '토큰 패밀리 ID (회전 추적)',
    
    -- 메타데이터
    device_info VARCHAR(255) COMMENT '디바이스 정보',
    ip_address VARCHAR(45) COMMENT 'IP 주소',
    
    -- 만료 정보
    expires_at DATETIME NOT NULL COMMENT '만료 시간',
    revoked BOOLEAN DEFAULT FALSE COMMENT '폐기 여부',
    
    -- 타임스탬프
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    -- 외래키 및 인덱스
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user_id (user_id),
    INDEX idx_family_id (family_id),
    INDEX idx_expires_at (expires_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='리프레시 토큰 테이블';

-- 7. recordings 테이블의 user_id 컬럼 타입 변경 (이미 존재하는 경우)
-- 먼저 외래키 제약조건 삭제
ALTER TABLE recordings DROP FOREIGN KEY IF EXISTS fk_recordings_user_id;

-- 컬럼 타입 변경
ALTER TABLE recordings MODIFY COLUMN user_id INT NULL COMMENT '사용자 ID';

-- 외래키 제약조건 재추가
ALTER TABLE recordings
    ADD CONSTRAINT fk_recordings_user_id 
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL;

-- 8. 외래키 제약조건 재활성화
SET FOREIGN_KEY_CHECKS = 1;

-- 9. 결과 확인
SELECT 'Users table reset successfully with AUTO_INCREMENT INT starting from 0!' AS message;
SHOW TABLES;
DESCRIBE users;






