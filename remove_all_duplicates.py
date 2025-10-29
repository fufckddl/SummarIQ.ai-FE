#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
세그먼트 및 transcript의 모든 중복 제거
"""
import re
from sqlalchemy import text as sql_text
from database.connection import get_db_context
from database import crud

def find_and_remove_duplicates(text: str) -> str:
    """
    텍스트 내 모든 중복 패턴 찾아서 제거
    """
    if not text or len(text) < 20:
        return text
    
    original_text = text
    changed = True
    iterations = 0
    max_iterations = 10
    
    while changed and iterations < max_iterations:
        changed = False
        iterations += 1
        
        # 다양한 길이의 중복 패턴 체크 (긴 것부터)
        length = len(text)
        
        for pattern_len in range(length // 2, 10, -1):
            i = 0
            while i < len(text) - pattern_len:
                pattern = text[i:i+pattern_len]
                next_part = text[i+pattern_len:i+pattern_len*2]
                
                if pattern == next_part and len(pattern) > 10:
                    print(f"  🔄 중복 제거 ({pattern_len}자): {pattern[:50]}...")
                    text = text[:i+pattern_len] + text[i+pattern_len*2:]
                    changed = True
                    break
                
                i += 1
            
            if changed:
                break
    
    if text != original_text:
        print(f"     원본: {len(original_text)}자 → 결과: {len(text)}자")
    
    return text

def clean_text_simple(text: str) -> str:
    """간단한 텍스트 정리"""
    # ▁ 문자 제거
    text = text.replace('▁', ' ')
    # 연속 공백 정리
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def fix_all_data():
    """모든 세그먼트와 transcript 수정"""
    
    print("="*80)
    print("🔧 세그먼트 및 Transcript 중복 완전 제거")
    print("="*80)
    print()
    
    with get_db_context() as db:
        recordings = crud.list_recordings(db)
        
        for recording in recordings:
            print(f"\n{'='*80}")
            print(f"🎙️  {recording.title}")
            print(f"ID: {recording.id}")
            print(f"{'='*80}\n")
            
            # 세그먼트 수정
            segments = crud.get_segments(db, recording.id)
            print(f"📊 세그먼트: {len(segments)}개\n")
            
            for seg in segments:
                old_text = seg.text
                
                # 중복 제거
                new_text = find_and_remove_duplicates(old_text)
                # 공백 정리
                new_text = clean_text_simple(new_text)
                
                if old_text != new_text:
                    print(f"세그먼트 #{seg.seq} 수정:")
                    print(f"  원본 ({len(old_text)}자): {old_text[:80]}...")
                    print(f"  결과 ({len(new_text)}자): {new_text[:80]}...")
                    
                    db.execute(
                        sql_text("UPDATE segments SET text = :text WHERE id = :id"),
                        {"text": new_text, "id": seg.id}
                    )
                    print()
            
            db.commit()
            
            # Transcript 재생성
            print("\n📝 Transcript 재생성...")
            segments = crud.get_segments(db, recording.id)  # 새로고침
            new_transcript = " ".join([seg.text for seg in segments])
            new_transcript = find_and_remove_duplicates(new_transcript)
            
            old_transcript_len = len(recording.transcript) if recording.transcript else 0
            new_transcript_len = len(new_transcript)
            
            if recording.transcript != new_transcript:
                crud.update_recording(db, recording.id, transcript=new_transcript)
                print(f"   {old_transcript_len}자 → {new_transcript_len}자")
                print(f"   미리보기: {new_transcript[:150]}...")
            else:
                print(f"   변경 없음")
            
            print()
    
    print(f"{'='*80}")
    print(f"✅ 모든 중복 제거 완료!")
    print(f"{'='*80}")

if __name__ == "__main__":
    fix_all_data()

