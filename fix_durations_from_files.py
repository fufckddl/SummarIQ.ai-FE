#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
병합된 오디오 파일에서 실제 길이를 읽어서 duration 업데이트
"""
from database.connection import get_db_context
from database import crud
from services.audio_metadata import get_audio_duration_ms
from services.audio_storage import AudioStorage
from pathlib import Path

def fix_durations_from_files():
    """병합된 파일의 실제 길이로 duration 업데이트"""
    
    print("🔧 오디오 파일 기반 duration 업데이트 시작...")
    print()
    
    audio_storage = AudioStorage()
    
    with get_db_context() as db:
        # 모든 녹음 조회
        recordings = crud.list_recordings(db)
        
        print(f"📋 총 {len(recordings)}개 녹음 발견\n")
        
        updated_count = 0
        for recording in recordings:
            try:
                # 병합된 파일 경로 가져오기
                file_path = audio_storage.get_audio_path(recording.id)
                
                # 실제 길이 읽기
                actual_duration = get_audio_duration_ms(file_path)
                
                if actual_duration > 0:
                    old_duration = recording.duration
                    
                    # MySQL 업데이트
                    crud.update_recording(db, recording.id, duration=actual_duration)
                    
                    print(f"✅ {recording.title[:40]}...")
                    print(f"   ID: {recording.id[:8]}...")
                    print(f"   파일: {Path(file_path).name}")
                    print(f"   이전: {old_duration}ms ({old_duration/1000:.1f}초)")
                    print(f"   수정: {actual_duration}ms ({actual_duration/1000:.1f}초)")
                    print()
                    
                    updated_count += 1
                else:
                    print(f"⚠️  {recording.title[:40]}... - duration 읽기 실패")
                    
            except FileNotFoundError:
                print(f"⏭️  {recording.title[:40]}... - 오디오 파일 없음")
            except Exception as e:
                print(f"❌ {recording.title[:40]}... - 오류: {e}")
        
        print(f"\n✅ 총 {updated_count}개 녹음의 duration이 실제 파일 기반으로 업데이트되었습니다!")


if __name__ == "__main__":
    fix_durations_from_files()

