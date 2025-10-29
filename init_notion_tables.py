"""
Notion 테이블 생성 스크립트
"""
from database.connection import get_db_context
from sqlalchemy import text


def init_notion_tables():
    """Notion 관련 테이블 생성"""
    
    tables = [
        # user_notion 테이블
        """
        CREATE TABLE IF NOT EXISTS user_notion (
            user_id INT PRIMARY KEY COMMENT '사용자 ID',
            access_token_enc TEXT NOT NULL COMMENT '암호화된 Notion access token',
            workspace_id VARCHAR(255) COMMENT 'Notion workspace ID',
            workspace_name VARCHAR(255) COMMENT 'Notion workspace 이름',
            bot_id VARCHAR(255) COMMENT 'Notion bot ID',
            default_target_type ENUM('database', 'page') DEFAULT 'database' COMMENT '기본 대상 타입',
            default_target_id VARCHAR(255) COMMENT '기본 대상 ID',
            default_target_name VARCHAR(255) COMMENT '기본 대상 이름',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            last_sync_at TIMESTAMP NULL COMMENT '마지막 동기화 시간',
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """,
        
        # notion_rules 테이블
        """
        CREATE TABLE IF NOT EXISTS notion_rules (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL COMMENT '사용자 ID',
            matcher_type ENUM('tag', 'calendar', 'keyword') NOT NULL COMMENT '매칭 타입',
            matcher_value VARCHAR(255) NOT NULL COMMENT '매칭 값',
            target_type ENUM('database', 'page') NOT NULL COMMENT '대상 타입',
            target_id VARCHAR(255) NOT NULL COMMENT '대상 ID',
            target_name VARCHAR(255) COMMENT '대상 이름',
            priority INT DEFAULT 0 COMMENT '우선순위',
            enabled BOOLEAN DEFAULT TRUE COMMENT '활성화 여부',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            INDEX idx_user_enabled (user_id, enabled),
            INDEX idx_matcher (matcher_type, matcher_value)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """,
        
        # notion_uploads 테이블
        """
        CREATE TABLE IF NOT EXISTS notion_uploads (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL COMMENT '사용자 ID',
            recording_id VARCHAR(255) NOT NULL COMMENT '녹음 ID',
            target_type ENUM('database', 'page') NOT NULL,
            target_id VARCHAR(255) NOT NULL COMMENT '업로드된 대상 ID',
            notion_page_id VARCHAR(255) COMMENT '생성된 Notion 페이지 ID',
            notion_page_url TEXT COMMENT 'Notion 페이지 URL',
            status ENUM('pending', 'success', 'failed') DEFAULT 'pending',
            error_message TEXT COMMENT '실패 시 오류 메시지',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (recording_id) REFERENCES recordings(id) ON DELETE CASCADE,
            INDEX idx_user_recording (user_id, recording_id),
            INDEX idx_status (status)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
    ]
    
    try:
        with get_db_context() as db:
            for i, table_sql in enumerate(tables, 1):
                print(f"📝 테이블 {i}/3 생성 중...")
                db.execute(text(table_sql))
                db.commit()
            
            print("✅ 모든 Notion 테이블 생성 완료")
            
            # 테이블 확인
            result = db.execute(text("SHOW TABLES LIKE 'user_notion'")).fetchone()
            if result:
                print("✅ user_notion 테이블 확인")
            
            result = db.execute(text("SHOW TABLES LIKE 'notion_uploads'")).fetchone()
            if result:
                print("✅ notion_uploads 테이블 확인")
                
    except Exception as e:
        print(f"❌ 테이블 생성 오류: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    init_notion_tables()

