#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
기존 데이터베이스의 STT 텍스트 정리
- ▁ 문자 제거
- 공백 정규화
"""
import re
from database.connection import get_db_context
from database import crud
from sqlalchemy import text

def clean_text(dirty_text: str) -> str:
    """STT 토큰 정리"""
    if not dirty_text:
        return ""
    
    # ▁ 문자를 공백으로 변환
    text = dirty_text.replace('▁', ' ')
    
    # 각 문자 사이의 공백 제거
    text = re.sub(r'(?<=[가-힣a-zA-Z0-9]) (?=[가-힣a-zA-Z0-9])', '', text)
    
    # 연속 공백을 하나로
    text = re.sub(r'\s+', ' ', text)
    
    # 양쪽 공백 제거
    text = text.strip()
    
    return text

def clean_all_text():
    """모든 녹음과 세그먼트의 텍스트 정리"""
    
    print("🔧 STT 텍스트 정리 시작...")
    print()
    
    with get_db_context() as db:
        # 녹음 목록
        recordings = crud.list_recordings(db)
        
        print(f"📋 총 {len(recordings)}개 녹음 발견\n")
        
        total_cleaned = 0
        
        for recording in recordings:
            print(f"{'='*80}")
            print(f"🎙️  {recording.title}")
            print(f"{'='*80}")
            
            cleaned_recording = False
            
            # 1. recordings 테이블의 transcript 정리
            if recording.transcript and '▁' in recording.transcript:
                old_text = recording.transcript[:100]
                new_text = clean_text(recording.transcript)
                
                crud.update_recording(db, recording.id, transcript=new_text)
                
                print(f"✅ Transcript 정리:")
                print(f"   Before: {old_text}...")
                print(f"   After:  {new_text[:100]}...")
                print()
                
                cleaned_recording = True
            
            # 2. segments 테이블의 text 정리
            segments = crud.get_segments(db, recording.id)
            cleaned_segments = 0
            
            for seg in segments:
                if seg.text and '▁' in seg.text:
                    old_text = seg.text[:50]
                    new_text = clean_text(seg.text)
                    
                    # 직접 SQL 업데이트 (crud에 segment update 함수 없음)
                    db.execute(
                        text("UPDATE segments SET text = :text WHERE id = :id"),
                        {"text": new_text, "id": seg.id}
                    )
                    
                    print(f"  ✅ 세그먼트 #{seg.seq} 정리")
                    print(f"     Before: {old_text}...")
                    print(f"     After:  {new_text[:50]}...")
                    
                    cleaned_segments += 1
            
            if cleaned_segments > 0:
                db.commit()
                print(f"\n  📊 {cleaned_segments}개 세그먼트 정리 완료")
                print()
            
            if cleaned_recording or cleaned_segments > 0:
                total_cleaned += 1
            else:
                print("  ⏭️  이미 깨끗한 텍스트")
                print()
        
        print(f"\n{'='*80}")
        print(f"✅ 총 {total_cleaned}개 녹음의 텍스트가 정리되었습니다!")
        print(f"{'='*80}")

if __name__ == "__main__":
    clean_all_text()

