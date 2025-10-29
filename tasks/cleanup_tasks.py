"""
정리 작업 태스크
- 오래된 실패 녹음 정리
- 임시 파일 정리
- Celery 결과 정리
"""
from celery_app import celery_app
from database.connection import get_db_context
from database import crud
from datetime import datetime, timedelta
import os
import shutil

# ⚠️ 모든 모델 명시적으로 임포트 (SQLAlchemy relationship 해결)
from models.recording import Recording
from models.segment import Segment
from models.user import User
from models.subscription import Subscription
from models.team import Team, TeamMember
from models.tag import Tag
from models.action import Action
from models.decision import Decision


@celery_app.task(
    name='tasks.cleanup_tasks.cleanup_old_failed_recordings',
    queue='default'
)
def cleanup_old_failed_recordings():
    """
    오래된 실패 녹음 정리
    - 7일 이상 된 failed/processing/stt_started 상태 녹음 삭제
    """
    try:
        print("🧹 [Cleanup] 오래된 실패 녹음 정리 시작...")
        
        from sqlalchemy import or_
        
        with get_db_context() as db:
            # 7일 이상 된 실패/처리중 녹음 조회
            cutoff_date = datetime.now() - timedelta(days=7)
            
            old_recordings = db.query(Recording).filter(
                or_(
                    Recording.status == 'failed',
                    Recording.status == 'processing',
                    Recording.status == 'stt_started'
                ),
                Recording.created_at < cutoff_date
            ).all()
            
            cleaned_count = 0
            for recording in old_recordings:
                try:
                    recording_id = recording.id
                    
                    # 오디오 파일 삭제
                    audio_dir = f"storage/audio/{recording_id}"
                    if os.path.exists(audio_dir):
                        shutil.rmtree(audio_dir)
                        print(f"   🗑️  삭제: {recording_id} ({recording.status})")
                    
                    # DB에서 녹음 삭제 (세그먼트, 결정사항, 액션 등 cascade 삭제)
                    db.delete(recording)
                    cleaned_count += 1
                    
                except Exception as e:
                    print(f"   ⚠️  녹음 삭제 실패 {recording_id}: {e}")
                    continue
            
            db.commit()
            
            print(f"✅ [Cleanup] 완료: {cleaned_count}개 녹음 정리")
            
            return {
                "status": "completed",
                "cleaned_count": cleaned_count
            }
            
    except Exception as e:
        print(f"❌ [Cleanup] 실패: {e}")
        import traceback
        traceback.print_exc()
        return {
            "status": "failed",
            "error": str(e)
        }


@celery_app.task(
    name='tasks.cleanup_tasks.cleanup_stale_processing_recordings',
    queue='default'
)
def cleanup_stale_processing_recordings():
    """
    오래 처리 중인 녹음 실패 처리
    - 1시간 이상 processing/stt_started 상태인 녹음 → failed
    """
    try:
        print("🧹 [Cleanup] 오래된 처리 중 녹음 확인...")
        
        from sqlalchemy import or_
        
        with get_db_context() as db:
            # 1시간 이상 처리 중인 녹음
            cutoff_date = datetime.now() - timedelta(hours=1)
            
            stale_recordings = db.query(Recording).filter(
                or_(
                    Recording.status == 'processing',
                    Recording.status == 'stt_started'
                ),
                Recording.updated_at < cutoff_date
            ).all()
            
            failed_count = 0
            for recording in stale_recordings:
                try:
                    recording.status = 'failed'
                    print(f"   💀 실패 처리: {recording.id}")
                    failed_count += 1
                except Exception as e:
                    print(f"   ⚠️  업데이트 실패 {recording.id}: {e}")
                    continue
            
            db.commit()
            
            print(f"✅ [Cleanup] 완료: {failed_count}개 녹음 실패 처리")
            
            return {
                "status": "completed",
                "failed_count": failed_count
            }
            
    except Exception as e:
        print(f"❌ [Cleanup] 실패: {e}")
        import traceback
        traceback.print_exc()
        return {
            "status": "failed",
            "error": str(e)
        }


@celery_app.task(
    name='tasks.cleanup_tasks.cleanup_temp_files',
    queue='default'
)
def cleanup_temp_files():
    """
    임시 파일 정리
    - /tmp 디렉토리의 오래된 오디오 파일 삭제
    """
    try:
        print("🧹 [Cleanup] 임시 파일 정리...")
        
        import tempfile
        import glob
        
        temp_dir = tempfile.gettempdir()
        patterns = [
            f"{temp_dir}/*.m4a",
            f"{temp_dir}/*.wav",
            f"{temp_dir}/*.mp3",
            f"{temp_dir}/audio_*",
        ]
        
        cleaned_count = 0
        cutoff_time = datetime.now() - timedelta(hours=24)
        
        for pattern in patterns:
            for file_path in glob.glob(pattern):
                try:
                    # 파일 수정 시간 확인
                    file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
                    
                    if file_mtime < cutoff_time:
                        os.remove(file_path)
                        cleaned_count += 1
                        
                except Exception as e:
                    continue
        
        print(f"✅ [Cleanup] 임시 파일 정리 완료: {cleaned_count}개")
        
        return {
            "status": "completed",
            "cleaned_count": cleaned_count
        }
        
    except Exception as e:
        print(f"❌ [Cleanup] 임시 파일 정리 실패: {e}")
        return {
            "status": "failed",
            "error": str(e)
        }

