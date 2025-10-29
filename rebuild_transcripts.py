#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
기존 녹음의 transcript를 세그먼트에서 재생성 (중복 제거)
"""
from database.connection import get_db_context
from database import crud
from services.text_utils import remove_exact_duplicates, remove_duplicate_sentences

def rebuild_all_transcripts():
    """모든 녹음의 transcript를 재생성"""
    
    print("🔧 Transcript 재생성 시작 (중복 제거)")
    print()
    
    with get_db_context() as db:
        recordings = crud.list_recordings(db)
        
        print(f"📋 총 {len(recordings)}개 녹음 발견\n")
        
        for recording in recordings:
            print(f"{'='*80}")
            print(f"🎙️  {recording.title}")
            print(f"{'='*80}")
            
            # 세그먼트에서 텍스트 합본
            segments = crud.get_segments(db, recording.id)
            
            if not segments:
                print("⚠️  세그먼트 없음\n")
                continue
            
            # 기존 transcript
            old_transcript = recording.transcript or ""
            old_length = len(old_transcript)
            
            # 새 transcript 생성 (중복 제거)
            segments_text = [seg.text for seg in segments]
            cleaned_segments_text = remove_exact_duplicates(segments_text)
            new_transcript = " ".join(cleaned_segments_text)
            new_transcript = remove_duplicate_sentences(new_transcript)
            
            new_length = len(new_transcript)
            
            # 업데이트
            if old_transcript != new_transcript:
                crud.update_recording(db, recording.id, transcript=new_transcript)
                
                print(f"✅ Transcript 재생성 완료")
                print(f"   세그먼트 수: {len(segments)}개")
                print(f"   이전 길이: {old_length}자")
                print(f"   새 길이: {new_length}자")
                print(f"   감소: {old_length - new_length}자 ({((old_length-new_length)/old_length*100) if old_length > 0 else 0:.1f}%)")
                print()
                print(f"   미리보기:")
                print(f"   {new_transcript[:200]}...")
                print()
            else:
                print("⏭️  이미 깨끗한 transcript\n")
        
        print(f"{'='*80}")
        print(f"✅ 모든 transcript 재생성 완료!")
        print(f"{'='*80}")


if __name__ == "__main__":
    rebuild_all_transcripts()

