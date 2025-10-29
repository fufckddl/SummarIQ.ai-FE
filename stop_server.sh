#!/bin/bash

# SummarIQ 백엔드 서버 종료 스크립트

echo "🛑 SummarIQ 백엔드 서버 종료 중..."

# 포트 8000을 사용하는 프로세스 종료
PID=$(lsof -ti:8000)

if [ -z "$PID" ]; then
  echo "❌ 포트 8000에서 실행 중인 서버가 없습니다."
  exit 0
fi

echo "📍 프로세스 ID: $PID"
kill -9 $PID 2>/dev/null

if [ $? -eq 0 ]; then
  echo "✅ 서버가 종료되었습니다."
else
  echo "❌ 서버 종료에 실패했습니다."
  exit 1
fi

