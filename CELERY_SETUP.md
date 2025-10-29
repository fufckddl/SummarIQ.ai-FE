# Celery + Redis 백그라운드 작업 큐 설정

## 📋 개요

무거운 STT/요약 작업을 Celery 워커로 분리하여 FastAPI 서버가 즉시 응답하도록 구성

## 🎯 아키텍처

```
사용자 요청 → FastAPI (즉시 202 응답)
              ↓ (큐에 작업 추가)
            Redis (메시지 브로커)
              ↓ (작업 가져옴)
       Celery Worker (별도 프로세스 4개)
              ↓
       STT → 요약 → DB 저장 → 푸시 알림
```

## 🔧 설치

### 1. Redis 설치 및 실행

```bash
# Mac
brew install redis
redis-server

# Linux
sudo apt-get install redis-server
sudo systemctl start redis

# 연결 확인
redis-cli ping  # 응답: PONG
```

### 2. Python 패키지 설치

```bash
cd backend
pip install -r requirements.txt

# 또는 개별 설치
pip install celery==5.3.4 redis==5.0.1
```

### 3. 데이터베이스 테이블 생성

```bash
# MySQL 접속
mysql -u root -p summariq_db

# 스키마 실행
source database/task_schema.sql;

# 확인
SHOW TABLES;  # task_status 테이블 확인
```

## 🚀 실행

### 터미널 1: Redis
```bash
redis-server
```

### 터미널 2: FastAPI 서버
```bash
cd backend
./start_server.sh
```

### 터미널 3: Celery 워커
```bash
cd backend
./start_celery_worker.sh
```

### 터미널 4: Celery Flower (모니터링 - 선택)
```bash
cd backend
source venv/bin/activate
celery -A celery_app flower --port=5555

# 브라우저: http://localhost:5555
```

## 📊 작업 흐름

### 1️⃣ 파일 업로드
```
POST /stt/upload
→ 파일 저장 (1초)
→ Celery 큐에 추가
→ 202 응답 {"recordingId": "xxx", "taskId": "yyy"}
```

### 2️⃣ 백그라운드 처리 (Celery 워커)
```
1. STT 처리 (60초~10분)
2. 화자별 세그먼트 저장
3. AI 제목 생성
4. 요약 생성
5. DB 업데이트 (status: ready)
6. 푸시 알림 (향후 추가)
```

### 3️⃣ 상태 확인 (폴링)
```
GET /stt/tasks/{taskId}
→ {
    "status": "processing",
    "progress": 60,
    "currentStep": "generate_summary"
  }
```

## 🔄 AWS SQS + Lambda 전환

### 전환 과정

```python
# 1. 추상화 레이어 추가 (backend/tasks/queue_adapter.py)
class QueueAdapter:
    @staticmethod
    def enqueue(recording_id, local_path):
        backend = os.getenv("QUEUE_BACKEND", "celery")
        
        if backend == "celery":
            from tasks.audio_tasks import process_audio_task
            return process_audio_task.delay(recording_id, local_path)
        
        elif backend == "sqs":
            import boto3
            sqs = boto3.client('sqs')
            # S3 업로드 후 SQS 메시지 전송
            s3_url = upload_to_s3(local_path)
            sqs.send_message(...)
            return {"MessageId": "..."}

# 2. 점진적 전환
export QUEUE_BACKEND=celery  # 현재
export SQS_MIGRATION_PERCENT=10  # 10% 트래픽만 SQS
export QUEUE_BACKEND=sqs  # 전환 완료 후
```

### 데이터 마이그레이션

**✅ 필요 없음!**
- MySQL 데이터 그대로 유지
- 오디오 파일만 로컬 → S3 이동
- 큐 시스템은 임시 작업만 관리

## 📈 성능 비교

| 방법 | 동시 처리 | 확장성 | 비용 |
|------|----------|--------|------|
| BackgroundTasks | 4명 | ❌ 불가능 | 무료 |
| Celery (4 workers) | 4명 | ✅ 워커 추가 가능 | 서버 비용 |
| Celery (10 workers) | 10명 | ✅ 무제한 확장 | 서버 비용 |
| AWS SQS + Lambda | 무제한 | ✅ 자동 확장 | 사용량 과금 |

## 🐛 트러블슈팅

### Redis 연결 실패
```bash
# Redis 상태 확인
redis-cli ping

# Redis 재시작
redis-server

# 연결 설정 확인
echo $REDIS_URL  # redis://localhost:6379/0
```

### Celery 작업 안 보임
```bash
# 큐 상태 확인
celery -A celery_app inspect active

# 워커 상태 확인
celery -A celery_app inspect stats

# 큐 비우기 (개발용)
celery -A celery_app purge
```

### 작업 실패 확인
```bash
# Flower에서 확인
http://localhost:5555

# 또는 로그 확인
celery -A celery_app events
```

## 📝 요약

✅ **현재**: Celery + Redis (개발/중소규모)
✅ **미래**: AWS SQS + Lambda (대규모)
✅ **전환**: 점진적, 데이터 유지, 리스크 최소


