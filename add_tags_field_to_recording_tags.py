import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("DATABASE_URL 환경 변수가 설정되지 않았습니다.")
    sys.exit(1)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def add_tags_field_to_recording_tags():
    print("🔄 recording_tags 테이블에 tags 필드 추가 시작...")
    session = SessionLocal()
    try:
        # 1. tags 필드 추가
        print("📝 tags JSON 필드 추가...")
        session.execute(text("""
            ALTER TABLE recording_tags 
            ADD COLUMN tags JSON
        """))
        print("✅ tags 필드 추가 완료")

        # 2. 기존 데이터를 JSON 형태로 변환
        print("📝 기존 태그 데이터를 JSON으로 변환...")
        
        # recording_tags와 tags 테이블 조인하여 데이터 가져오기
        result = session.execute(text("""
            SELECT rt.recording_id, rt.tag_id, t.name, t.color
            FROM recording_tags rt
            JOIN tags t ON rt.tag_id = t.id
            ORDER BY rt.recording_id
        """))
        
        # recording_id별로 태그 그룹화
        recording_tags = {}
        for row in result:
            recording_id = row[0]
            if recording_id not in recording_tags:
                recording_tags[recording_id] = []
            recording_tags[recording_id].append({
                "name": row[2],
                "color": row[3] or "#8B5CF6"
            })
        
        # 각 recording_id에 대해 JSON 업데이트
        for recording_id, tags in recording_tags.items():
            import json
            tags_json = json.dumps(tags, ensure_ascii=False)
            session.execute(text("""
                UPDATE recording_tags 
                SET tags = :tags_json 
                WHERE recording_id = :recording_id
            """), {"tags_json": tags_json, "recording_id": recording_id})
            print(f"📝 {recording_id}: {len(tags)}개 태그 변환 완료")
        
        session.commit()
        print("✅ recording_tags 테이블 수정 완료")

    except Exception as e:
        session.rollback()
        print(f"❌ 테이블 수정 실패: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()

if __name__ == "__main__":
    add_tags_field_to_recording_tags()
