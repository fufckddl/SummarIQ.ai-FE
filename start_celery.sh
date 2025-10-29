#!/bin/bash

# SummarIQ Celery 워커 시작 스크립트 (중복 방지)

echo "🚀 Celery 워커 시작 중..."

# 기존 워커 확인
EXISTING=$(pgrep -f "celery.*worker")

if [ ! -z "$EXISTING" ]; then
  echo "⚠️  이미 실행 중인 Celery 워커가 있습니다:"
  echo "$EXISTING" | while read pid; do
    echo "   - PID: $pid"
  done
  echo ""
  read -p "종료하고 재시작하시겠습니까? (y/n): " -n 1 -r
  echo
  if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🛑 기존 워커 종료 중..."
    ./stop_celery.sh
  else
    echo "❌ 취소되었습니다."
    exit 1
  fi
fi

# 가상환경 활성화
if [ ! -d "venv" ]; then
  echo "❌ 가상환경(venv)이 없습니다. 먼저 생성해주세요."
  exit 1
fi

source venv/bin/activate

# Redis 실행 확인
if ! redis-cli ping > /dev/null 2>&1; then
  echo "⚠️  Redis가 실행 중이 아닙니다. Redis를 먼저 시작해주세요."
  echo "   brew services start redis"
  exit 1
fi

# Celery 워커 시작 (백그라운드, 다중 큐 지원)
echo "🔄 Celery 워커 시작..."
celery -A celery_app worker \
  --loglevel=info \
  --concurrency=4 \
  -Q stt,summary \
  --max-tasks-per-child=10 \
  --autoscale=6,2 \
  > celery_worker.log 2>&1 &

CELERY_PID=$!

# 시작 확인 (2초 대기)
sleep 2

if ps -p $CELERY_PID > /dev/null; then
  echo "✅ Celery 워커가 시작되었습니다."
  echo "   PID: $CELERY_PID"
  echo "   로그: tail -f celery_worker.log"
else
  echo "❌ Celery 워커 시작 실패. celery_worker.log를 확인하세요."
  exit 1
fi

