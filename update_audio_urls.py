#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
기존 녹음들의 audio_url을 새 IP로 업데이트
"""
from sqlalchemy import text
from database.connection import get_db_context
from database import crud
from database.config import SERVER_BASE_URL

def update_all_audio_urls():
    """모든 녹음의 audioUrl을 환경변수 기반 URL로 업데이트"""
    
    print("🔧 오디오 URL 업데이트 시작...")
    print(f"📍 서버 URL: {SERVER_BASE_URL}")
    
    with get_db_context() as db:
        # 모든 녹음 조회
        recordings = crud.list_recordings(db)
        
        print(f"📋 총 {len(recordings)}개 녹음 발견")
        
        updated_count = 0
        for recording in recordings:
            old_url = recording.audio_url
            new_url = f"{SERVER_BASE_URL}/stt/audio/{recording.id}"
            
            if old_url != new_url:
                crud.update_recording(db, recording.id, audio_url=new_url)
                print(f"✅ {recording.id[:8]}... 업데이트 완료")
                print(f"   {old_url}")
                print(f"   → {new_url}")
                updated_count += 1
            else:
                print(f"⏭️  {recording.id[:8]}... 이미 최신 URL")
        
        print(f"\n✅ 총 {updated_count}개 녹음의 URL이 업데이트되었습니다!")


if __name__ == "__main__":
    update_all_audio_urls()

