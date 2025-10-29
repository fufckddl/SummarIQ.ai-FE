#!/bin/bash

# Celery 워커 실행 스크립트

echo "🚀 Celery 워커 시작 중..."

# 현재 디렉토리를 백엔드로 변경
cd "$(dirname "$0")"

# 가상환경 활성화
echo "📦 가상환경 활성화 중..."
source venv/bin/activate

# 환경 변수 설정
echo "🔧 환경 변수 설정 중..."
export GOOGLE_APPLICATION_CREDENTIALS=$(pwd)/summariq-credentials.json
export GOOGLE_CLOUD_PROJECT_ID=summariq-project

# .env 파일에서 환경 변수 로드
if [ -f .env ]; then
  export $(cat .env | grep -v '^#' | xargs)
  echo "✅ .env 파일 로드됨"
fi

# Redis 연결 확인
echo "🔍 Redis 연결 확인..."
redis-cli ping > /dev/null 2>&1
if [ $? -ne 0 ]; then
  echo "⚠️  Redis가 실행되지 않았습니다."
  echo "   다음 명령으로 Redis를 시작하세요:"
  echo "   brew install redis (처음 한 번)"
  echo "   redis-server"
  exit 1
fi
echo "✅ Redis 연결 성공"

# Celery 워커 실행
echo "🌐 Celery 워커 실행 중..."
echo "📍 큐: stt, summary"
echo "📊 동시 작업: 4개"
echo ""
echo "종료하려면 Ctrl+C를 누르세요"
echo "=========================================="

# -A: Celery 앱 위치
# -l info: 로그 레벨
# --concurrency=4: 동시 4개 작업 처리
# -Q stt,summary: stt와 summary 큐 처리
celery -A celery_app worker \
  --loglevel=info \
  --concurrency=4 \
  -Q stt,summary \
  --max-tasks-per-child=50


