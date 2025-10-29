#!/bin/bash

# SummarIQ Celery 워커 종료 스크립트 (중복 방지)

echo "🛑 Celery 워커 종료 중..."

# Celery 워커 프로세스 찾기
PIDS=$(pgrep -f "celery.*worker")

if [ -z "$PIDS" ]; then
  echo "✅ 실행 중인 Celery 워커가 없습니다."
  exit 0
fi

echo "📍 발견된 Celery 워커 프로세스:"
echo "$PIDS" | while read pid; do
  echo "   - PID: $pid"
done

# SIGTERM으로 graceful shutdown 시도
echo "🔄 Graceful shutdown 시도 (SIGTERM)..."
pkill -TERM -f "celery.*worker" 2>/dev/null

# 5초 대기
sleep 5

# 아직 살아있는지 확인
REMAINING=$(pgrep -f "celery.*worker")

if [ -z "$REMAINING" ]; then
  echo "✅ Celery 워커가 정상 종료되었습니다."
  exit 0
fi

# 여전히 살아있으면 강제 종료
echo "⚠️  일부 프로세스가 남아있어 강제 종료합니다..."
pkill -9 -f "celery.*worker" 2>/dev/null

# 최종 확인
sleep 1
FINAL=$(pgrep -f "celery.*worker")

if [ -z "$FINAL" ]; then
  echo "✅ Celery 워커가 완전히 종료되었습니다."
else
  echo "❌ 일부 프로세스 종료 실패:"
  echo "$FINAL"
  exit 1
fi

