"""
잘못된 duration 값을 수정하는 스크립트
세그먼트의 실제 end_ms 최대값으로 duration을 업데이트합니다.
"""
import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# database/config.py의 설정 사용
from database.config import DATABASE_URL

# 데이터베이스 연결
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
db = Session()

try:
    # 1. 모든 녹음 조회
    result = db.execute(text("SELECT id, duration FROM recordings WHERE status != 'cancelled'"))
    recordings = result.fetchall()
    
    print(f"📊 총 {len(recordings)}개 녹음 확인 중...\n")
    
    fixed_count = 0
    for rec_id, current_duration in recordings:
        # 2. 해당 녹음의 세그먼트 중 최대 end_ms 조회
        seg_result = db.execute(
            text("SELECT MAX(end_ms) FROM segments WHERE recording_id = :rec_id"),
            {"rec_id": rec_id}
        )
        max_end_ms = seg_result.fetchone()[0]
        
        if max_end_ms and max_end_ms != current_duration:
            # 3. duration 업데이트
            db.execute(
                text("UPDATE recordings SET duration = :duration WHERE id = :rec_id"),
                {"duration": max_end_ms, "rec_id": rec_id}
            )
            
            current_min = current_duration // 60000
            current_sec = (current_duration % 60000) // 1000
            actual_min = max_end_ms // 60000
            actual_sec = (max_end_ms % 60000) // 1000
            
            print(f"✅ {rec_id[:8]}... : {current_min}분 {current_sec}초 → {actual_min}분 {actual_sec}초")
            fixed_count += 1
    
    # 4. 변경사항 커밋
    db.commit()
    
    print(f"\n✅ 완료! {fixed_count}개 녹음의 duration 수정됨")
    
except Exception as e:
    print(f"❌ 오류 발생: {e}")
    import traceback
    traceback.print_exc()
    db.rollback()
finally:
    db.close()

