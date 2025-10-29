"""
Celery 앱 설정
백그라운드 작업 처리용 (STT, 요약, 긴 작업)
"""
from celery import Celery
import os
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

# Redis URL 설정
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Celery 앱 생성
celery_app = Celery(
    'summariq',
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=[
        'tasks.audio_tasks',
        'tasks.cleanup_tasks'  # 정리 작업 추가
    ]
)

# Celery 설정
celery_app.conf.update(
    # 작업 설정
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Asia/Seoul',
    enable_utc=True,
    
    # 작업 타임아웃
    task_time_limit=3600,  # 1시간 (hard limit)
    task_soft_time_limit=3300,  # 55분 (soft limit)
    
    # 결과 백엔드
    result_expires=3600,  # 결과 1시간 후 삭제
    result_backend_transport_options={
        'master_name': 'mymaster',
    },
    
    # 작업 라우팅
    task_routes={
        'tasks.audio_tasks.process_audio_task': {'queue': 'stt'},
        'tasks.audio_tasks.process_audio_from_s3': {'queue': 'stt'},
        'tasks.audio_tasks.process_hybrid_recording': {'queue': 'stt'},
        'tasks.audio_tasks.process_summary_task': {'queue': 'summary'},
        'tasks.cleanup_tasks.*': {'queue': 'default'},
    },
    
    # 📅 주기적 작업 스케줄 (Celery Beat)
    beat_schedule={
        # 1시간마다 오래된 처리 중 녹음 실패 처리
        'cleanup-stale-recordings': {
            'task': 'tasks.cleanup_tasks.cleanup_stale_processing_recordings',
            'schedule': 3600.0,  # 1시간
        },
        # 매일 새벽 3시에 오래된 실패 녹음 삭제
        'cleanup-old-failed-recordings': {
            'task': 'tasks.cleanup_tasks.cleanup_old_failed_recordings',
            'schedule': 86400.0,  # 24시간
            'options': {'expires': 3600}
        },
        # 6시간마다 임시 파일 정리
        'cleanup-temp-files': {
            'task': 'tasks.cleanup_tasks.cleanup_temp_files',
            'schedule': 21600.0,  # 6시간
        },
    },
    
    # 워커 설정
    worker_prefetch_multiplier=1,  # 한 번에 하나씩 처리 (메모리 절약)
    worker_max_tasks_per_child=10,  # 10개 작업 후 워커 재시작 (메모리 누수 방지)
    worker_max_memory_per_child=800_000,  # 800MB 메모리 한도 (OOM 방지)
    
    # 재시도 설정
    task_acks_late=True,  # 작업 완료 후 ACK
    task_reject_on_worker_lost=True,  # 워커 종료 시 작업 재큐잉
    
    # 브로커 설정
    broker_heartbeat=30,
    broker_pool_limit=10,
    broker_connection_retry_on_startup=True,
)

# 작업 우선순위
celery_app.conf.task_default_priority = 5
celery_app.conf.task_inherit_parent_priority = True

print(f"✅ Celery 앱 초기화 완료")
print(f"   - Broker: {REDIS_URL}")
print(f"   - Backend: {REDIS_URL}")

