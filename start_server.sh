#!/bin/bash

# SummarIQ 백엔드 서버 실행 스크립트

echo "🚀 SummarIQ 백엔드 서버 시작 중..."

# 현재 디렉토리를 백엔드로 변경
cd "$(dirname "$0")"

# 가상환경 활성화
echo "📦 가상환경 활성화 중..."
source venv/bin/activate

# 환경 변수 설정
echo "🔧 환경 변수 설정 중..."
export GOOGLE_APPLICATION_CREDENTIALS=$(pwd)/summariq-credentials.json
export GOOGLE_CLOUD_PROJECT_ID=summariq-project

# .env 파일에서 OPENAI_API_KEY 읽기
if [ -f .env ]; then
  export $(cat .env | grep OPENAI_API_KEY | xargs)
  echo "✅ OPENAI_API_KEY 로드됨"
fi

# 서버 실행
echo "🌐 서버 실행 중..."
echo "📍 서버 주소: http://localhost:8000"
echo "📖 API 문서: http://localhost:8000/docs"
echo "🏥 헬스 체크: http://localhost:8000/health"
echo ""
echo "종료하려면 Ctrl+C를 누르세요"
echo "=========================================="

uvicorn main:app --host 0.0.0.0 --port 8000
