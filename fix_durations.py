#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
기존 녹음들의 duration 수정 (3초 → 15초 간격)
"""
from database.connection import get_db_context
from database import crud

def fix_all_durations():
    """모든 녹음의 duration을 올바르게 수정"""
    
    print("🔧 녹음 길이(duration) 수정 시작...")
    
    with get_db_context() as db:
        # 모든 녹음 조회
        recordings = crud.list_recordings(db)
        
        print(f"📋 총 {len(recordings)}개 녹음 발견\n")
        
        fixed_count = 0
        for recording in recordings:
            # 세그먼트 수 확인
            segments = crud.get_segments(db, recording.id)
            segment_count = len(segments)
            
            # 올바른 duration 계산 (15초 간격)
            correct_duration = segment_count * 15000
            old_duration = recording.duration
            
            if old_duration != correct_duration:
                crud.update_recording(db, recording.id, duration=correct_duration)
                
                print(f"✅ {recording.title[:30]}...")
                print(f"   ID: {recording.id[:8]}...")
                print(f"   세그먼트: {segment_count}개")
                print(f"   이전: {old_duration}ms ({old_duration/1000:.1f}초)")
                print(f"   수정: {correct_duration}ms ({correct_duration/1000:.1f}초)")
                print()
                
                fixed_count += 1
            else:
                print(f"⏭️  {recording.title[:30]}... (이미 정확함)")
        
        print(f"\n✅ 총 {fixed_count}개 녹음의 duration이 수정되었습니다!")


if __name__ == "__main__":
    fix_all_durations()

