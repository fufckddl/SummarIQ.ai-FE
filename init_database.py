#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
데이터베이스 초기화 스크립트
- MySQL 연결 테스트
- 테이블 생성
- 초기 데이터 확인
"""
import sys
from sqlalchemy import text
from database.connection import test_connection, init_db, engine
from models import Base
from models.recording import Recording
from models.segment import Segment
from models.decision import Decision
from models.action import Action


def main():
    print("="*60)
    print("🚀 SummarIQ 데이터베이스 초기화")
    print("="*60)
    print()
    
    # 1단계: 연결 테스트
    print("1️⃣ MySQL 연결 테스트...")
    if not test_connection():
        print("❌ MySQL 연결 실패!")
        print()
        print("해결 방법:")
        print("1. MySQL이 실행 중인지 확인: sudo /usr/local/mysql/support-files/mysql.server status")
        print("2. 비밀번호가 올바른지 확인: mysql -u root -pyour-mysql-password -e 'SELECT 1;'")
        print("3. backend/.env 파일 확인")
        sys.exit(1)
    
    print()
    
    # 2단계: 데이터베이스 및 테이블 생성
    print("2️⃣ 테이블 생성...")
    try:
        # SQL 파일 실행 (데이터베이스 생성)
        print("   📋 데이터베이스 'summariq' 생성 중...")
        with engine.connect() as conn:
            conn.execute(text("CREATE DATABASE IF NOT EXISTS summariq CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"))
            conn.execute(text("USE summariq"))
            conn.commit()
        
        # SQLAlchemy로 테이블 생성
        print("   📋 테이블 생성 중...")
        Base.metadata.create_all(bind=engine)
        print("   ✅ 테이블 생성 완료!")
        
    except Exception as e:
        print(f"   ❌ 테이블 생성 실패: {e}")
        sys.exit(1)
    
    print()
    
    # 3단계: 테이블 확인
    print("3️⃣ 생성된 테이블 확인...")
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SHOW TABLES"))
            tables = [row[0] for row in result]
            
            if tables:
                print(f"   ✅ 총 {len(tables)}개 테이블:")
                for table in tables:
                    print(f"      - {table}")
            else:
                print("   ⚠️  테이블이 없습니다")
    
    except Exception as e:
        print(f"   ❌ 테이블 확인 실패: {e}")
    
    print()
    
    # 4단계: 스키마 정보 출력
    print("4️⃣ 테이블 스키마 확인...")
    try:
        with engine.connect() as conn:
            for table in ['recordings', 'segments', 'decisions', 'actions']:
                print(f"\n   📋 {table} 테이블:")
                result = conn.execute(text(f"DESCRIBE {table}"))
                for row in result:
                    field_name = row[0]
                    field_type = row[1]
                    nullable = "NULL" if row[2] == "YES" else "NOT NULL"
                    key = f" ({row[3]})" if row[3] else ""
                    print(f"      - {field_name}: {field_type} {nullable}{key}")
    
    except Exception as e:
        print(f"   ❌ 스키마 확인 실패: {e}")
    
    print()
    print("="*60)
    print("✅ 데이터베이스 초기화 완료!")
    print("="*60)
    print()
    print("📋 접속 정보:")
    print("   - 호스트: localhost")
    print("   - 사용자: root")
    print("   - 비밀번호: your-mysql-password")
    print("   - 데이터베이스: summariq")
    print("   - 포트: 3306")
    print()


if __name__ == "__main__":
    main()

