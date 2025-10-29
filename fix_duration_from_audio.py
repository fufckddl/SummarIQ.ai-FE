"""
오디오 파일의 실제 길이로 duration을 수정하는 스크립트
"""
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from pydub import AudioSegment

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
        # 2. 해당 녹음의 오디오 폴더 확인
        audio_dir = f"storage/audio/{rec_id}"
        
        if not os.path.exists(audio_dir):
            print(f"⚠️  {rec_id[:8]}... : 오디오 폴더 없음")
            continue
        
        # 3. 모든 청크 파일 찾기
        chunk_files = sorted([f for f in os.listdir(audio_dir) if f.startswith("chunk_") and f.endswith(".m4a")])
        
        if not chunk_files:
            print(f"⚠️  {rec_id[:8]}... : 청크 파일 없음")
            continue
        
        # 4. 모든 청크를 병합하여 총 길이 계산
        total_duration_ms = 0
        try:
            for chunk_file in chunk_files:
                chunk_path = os.path.join(audio_dir, chunk_file)
                try:
                    chunk_audio = AudioSegment.from_file(chunk_path)
                    total_duration_ms += len(chunk_audio)
                except Exception as e:
                    print(f"   ⚠️  청크 읽기 실패: {chunk_file} - {e}")
            
            if total_duration_ms > 0 and total_duration_ms != current_duration:
                # 5. duration 업데이트
                db.execute(
                    text("UPDATE recordings SET duration = :duration WHERE id = :rec_id"),
                    {"duration": total_duration_ms, "rec_id": rec_id}
                )
                
                current_min = current_duration // 60000
                current_sec = (current_duration % 60000) // 1000
                actual_min = total_duration_ms // 60000
                actual_sec = (total_duration_ms % 60000) // 1000
                
                print(f"✅ {rec_id[:8]}... : {current_min}분 {current_sec}초 → {actual_min}분 {actual_sec}초 ({len(chunk_files)}개 청크)")
                fixed_count += 1
        except Exception as e:
            print(f"❌ {rec_id[:8]}... : 오류 - {e}")
    
    # 6. 변경사항 커밋
    db.commit()
    
    print(f"\n✅ 완료! {fixed_count}개 녹음의 duration 수정됨")
    
except Exception as e:
    print(f"❌ 오류 발생: {e}")
    import traceback
    traceback.print_exc()
    db.rollback()
finally:
    db.close()

