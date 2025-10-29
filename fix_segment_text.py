#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
세그먼트 텍스트 수정:
1. 공백 복원
2. 중복 제거
"""
import re
from sqlalchemy import text as sql_text
from database.connection import get_db_context
from database import crud

def restore_spacing(text: str) -> str:
    """공백 없는 텍스트에 띄어쓰기 복원 (간단한 방법)"""
    # 이미 공백이 있으면 그대로 반환
    if ' ' in text:
        return text
    
    # 공백이 전혀 없으면 간단한 규칙으로 복원
    # (완벽하진 않지만 읽기는 가능)
    result = []
    for i, char in enumerate(text):
        result.append(char)
        # 조사 앞에서 띄어쓰기 (간단한 규칙)
        if i < len(text) - 1:
            next_char = text[i+1]
            # 영문자 뒤에 한글이 오면 띄어쓰기
            if char.isalpha() and not char.encode().isalpha() == next_char.encode().isalpha():
                result.append(' ')
    
    return ''.join(result)

def clean_text(dirty_text: str) -> str:
    """텍스트 정리"""
    if not dirty_text:
        return ""
    
    # ▁ 문자를 공백으로 변환
    text = dirty_text.replace('▁', ' ')
    
    # 연속 공백을 하나로
    text = re.sub(r'\s+', ' ', text)
    
    # 양쪽 공백 제거
    text = text.strip()
    
    return text

def remove_text_duplicates(text: str) -> str:
    """텍스트 내 절반 중복 제거"""
    # 절반 지점 확인
    length = len(text)
    mid = length // 2
    
    if mid > 10:
        first_half = text[:mid]
        second_half = text[mid:mid*2]
        
        # 절반이 정확히 중복이면
        if first_half == second_half:
            print(f"  🔄 절반 중복 감지 및 제거 ({mid}자)")
            return first_half
    
    return text

def fix_all_segments():
    """모든 세그먼트의 텍스트 수정"""
    
    print("🔧 세그먼트 텍스트 수정 시작...")
    print()
    
    with get_db_context() as db:
        recordings = crud.list_recordings(db)
        
        print(f"📋 총 {len(recordings)}개 녹음\n")
        
        total_fixed = 0
        
        for recording in recordings:
            print(f"{'='*80}")
            print(f"🎙️  {recording.title}")
            print(f"{'='*80}")
            
            segments = crud.get_segments(db, recording.id)
            fixed_count = 0
            
            for seg in segments:
                old_text = seg.text
                old_length = len(old_text)
                
                # 1단계: 공백 복원 (▁ 제거)
                new_text = clean_text(old_text)
                
                # 2단계: 중복 제거
                new_text = remove_text_duplicates(new_text)
                
                new_length = len(new_text)
                
                # 변경사항이 있거나, 공백이 전혀 없으면 수정
                needs_fix = (old_text != new_text) or (' ' not in old_text and old_length > 10)
                
                if needs_fix:
                    print(f"\n세그먼트 #{seg.seq}:")
                    print(f"  Before ({old_length}자): {old_text[:100]}")
                    print(f"  After ({new_length}자): {new_text[:100]}")
                    
                    # 직접 SQL 업데이트
                    db.execute(
                        sql_text("UPDATE segments SET text = :text WHERE id = :id"),
                        {"text": new_text, "id": seg.id}
                    )
                    
                    fixed_count += 1
            
            if fixed_count > 0:
                db.commit()
                print(f"\n✅ {fixed_count}개 세그먼트 수정 완료")
                total_fixed += fixed_count
            else:
                print("⏭️  모든 세그먼트가 정상")
            
            print()
        
        print(f"{'='*80}")
        print(f"✅ 총 {total_fixed}개 세그먼트가 수정되었습니다!")
        print(f"{'='*80}")

if __name__ == "__main__":
    fix_all_segments()

