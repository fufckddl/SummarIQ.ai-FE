#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
데이터베이스 내용 확인 스크립트
"""
from database.connection import get_db_context
from database import crud

def check_database():
    print("="*80)
    print("📊 SummarIQ 데이터베이스 내용 확인")
    print("="*80)
    print()
    
    with get_db_context() as db:
        # 녹음 목록
        recordings = crud.list_recordings(db)
        
        print(f"📋 총 {len(recordings)}개 녹음")
        print()
        
        for idx, recording in enumerate(recordings, 1):
            print(f"{'='*80}")
            print(f"🎙️  녹음 #{idx}")
            print(f"{'='*80}")
            print(f"ID: {recording.id}")
            print(f"제목: {recording.title}")
            print(f"상태: {recording.status}")
            print(f"길이: {recording.duration}ms ({recording.duration/1000:.1f}초)")
            print(f"언어: {recording.lang_auto}")
            print(f"생성일: {recording.created_at}")
            print()
            
            # 전체 텍스트
            if recording.transcript:
                print(f"📝 전체 텍스트 ({len(recording.transcript)}자):")
                print(f"{recording.transcript[:200]}...")
                print()
            else:
                print("📝 전체 텍스트: (없음)")
                print()
            
            # 요약
            if recording.summary:
                print(f"📋 AI 요약:")
                print(f"{recording.summary}")
                print()
            
            # 세그먼트 목록
            segments = crud.get_segments(db, recording.id)
            print(f"🔊 세그먼트: {len(segments)}개")
            print()
            
            for seg in segments[:5]:  # 최대 5개만 표시
                print(f"  세그먼트 #{seg.seq}")
                print(f"  - 시간: {seg.start_ms}ms ~ {seg.end_ms}ms ({seg.start_ms/1000:.1f}초 ~ {seg.end_ms/1000:.1f}초)")
                print(f"  - 텍스트: {seg.text[:100]}...")
                print(f"  - 언어: {seg.lang}, 신뢰도: {float(seg.confidence):.2f}")
                print()
            
            if len(segments) > 5:
                print(f"  ... 외 {len(segments)-5}개 세그먼트")
                print()
            
            # 의사결정
            decisions = crud.get_decisions(db, recording.id)
            if decisions:
                print(f"🎯 의사결정: {len(decisions)}개")
                for i, dec in enumerate(decisions, 1):
                    print(f"  {i}. {dec.decision}")
                print()
            
            # 액션 아이템
            actions = crud.get_actions(db, recording.id)
            if actions:
                print(f"📝 액션 아이템: {len(actions)}개")
                for i, act in enumerate(actions, 1):
                    print(f"  {i}. {act.task}")
                    if act.owner:
                        print(f"     담당자: {act.owner}")
                    if act.due_date:
                        print(f"     마감일: {act.due_date}")
                    print(f"     우선순위: {act.priority}")
                print()
            
            print()

if __name__ == "__main__":
    check_database()

