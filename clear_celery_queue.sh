#!/bin/bash

# SummarIQ Celery 큐 데이터 삭제 스크립트
# 사용법: ./clear_celery_queue.sh [옵션]

echo "🗑️  SummarIQ Celery 큐 데이터 삭제 도구"
echo "=========================================="

# Redis 연결 확인
echo "📡 Redis 연결 확인 중..."
if ! redis-cli ping > /dev/null 2>&1; then
    echo "❌ Redis 서버에 연결할 수 없습니다."
    echo "   Redis가 실행 중인지 확인하세요: brew services start redis"
    exit 1
fi
echo "✅ Redis 연결 성공"

# 현재 큐 상태 확인
echo ""
echo "📊 현재 큐 상태:"
redis-cli info keyspace

# 키 개수 확인
KEY_COUNT=$(redis-cli dbsize)
echo "🔢 총 키 개수: $KEY_COUNT"

if [ "$KEY_COUNT" -eq 0 ]; then
    echo "✅ 큐가 이미 비어있습니다."
    exit 0
fi

echo ""
echo "🔍 현재 저장된 키들:"
redis-cli keys "*" | head -10

# 사용자 확인
echo ""
echo "⚠️  경고: 이 작업은 모든 Celery 큐 데이터를 삭제합니다."
echo "   - 대기 중인 작업들"
echo "   - 작업 결과 캐시"
echo "   - 큐 메타데이터"
echo ""
read -p "정말 삭제하시겠습니까? (y/N): " confirm

if [[ $confirm != [yY] ]]; then
    echo "❌ 작업이 취소되었습니다."
    exit 0
fi

# 삭제 실행
echo ""
echo "🗑️  큐 데이터 삭제 중..."

# 방법 1: 전체 데이터베이스 삭제 (추천)
redis-cli flushdb

# 삭제 결과 확인
echo "✅ 삭제 완료!"
echo ""
echo "📊 삭제 후 상태:"
redis-cli info keyspace

# Celery 워커 재시작 권장
echo ""
echo "💡 권장사항:"
echo "   큐를 삭제했으니 Celery 워커를 재시작하는 것이 좋습니다:"
echo "   ./stop_celery.sh && ./start_celery.sh"
echo ""
echo "🎉 큐 데이터 삭제가 완료되었습니다!"
