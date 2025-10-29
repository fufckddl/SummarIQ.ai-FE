#!/usr/bin/env python3
"""
팀 회의록 테이블의 meeting_id를 UUID로 업데이트하는 스크립트
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.connection import get_db
from models.team_meeting import TeamMeeting
from models.recording import Recording
from sqlalchemy.orm import Session

def fix_team_meetings():
    """팀 회의록 테이블의 meeting_id를 UUID로 업데이트"""
    db = next(get_db())
    
    try:
        # 모든 팀 회의록 조회
        team_meetings = db.query(TeamMeeting).all()
        print(f"📋 팀 회의록 개수: {len(team_meetings)}")
        
        for tm in team_meetings:
            print(f"🔍 팀 회의록: team_id={tm.team_id}, meeting_id={tm.meeting_id}, is_active={tm.is_active}")
            
            # meeting_id가 정수인 경우 UUID로 변환
            if isinstance(tm.meeting_id, int):
                # recordings 테이블에서 해당 ID의 회의 찾기
                recording = db.query(Recording).filter(Recording.id == tm.meeting_id).first()
                if recording:
                    print(f"✅ 회의 찾음: {recording.id} -> {recording.id}")
                    # meeting_id를 UUID로 업데이트
                    tm.meeting_id = recording.id
                    print(f"🔄 업데이트: {tm.meeting_id} -> {recording.id}")
                else:
                    print(f"❌ 회의를 찾을 수 없음: {tm.meeting_id}")
            else:
                print(f"ℹ️ 이미 UUID: {tm.meeting_id}")
        
        # 변경사항 저장
        db.commit()
        print("✅ 팀 회의록 테이블 업데이트 완료")
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    fix_team_meetings()
