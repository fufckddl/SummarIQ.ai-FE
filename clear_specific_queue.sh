#!/bin/bash

# SummarIQ 특정 큐만 삭제하는 스크립트
# 사용법: ./clear_specific_queue.sh [큐이름]

echo "🎯 SummarIQ 특정 큐 삭제 도구"
echo "=============================="

# Redis 연결 확인
echo "📡 Redis 연결 확인 중..."
if ! redis-cli ping > /dev/null 2>&1; then
    echo "❌ Redis 서버에 연결할 수 없습니다."
    exit 1
fi
echo "✅ Redis 연결 성공"

# 큐 이름 확인
if [ -z "$1" ]; then
    echo ""
    echo "📋 사용 가능한 큐들:"
    redis-cli keys "*" | grep -E "^(stt|summary)$" | sort
    echo ""
    echo "사용법: ./clear_specific_queue.sh [큐이름]"
    echo "예시: ./clear_specific_queue.sh stt"
    echo "예시: ./clear_specific_queue.sh summary"
    exit 1
fi

QUEUE_NAME="$1"

# 큐 존재 확인
if ! redis-cli exists "$QUEUE_NAME" > /dev/null 2>&1; then
    echo "❌ 큐 '$QUEUE_NAME'이 존재하지 않습니다."
    echo ""
    echo "📋 현재 존재하는 큐들:"
    redis-cli keys "*" | grep -E "^(stt|summary)$" | sort
    exit 1
fi

# 큐 크기 확인
QUEUE_SIZE=$(redis-cli llen "$QUEUE_NAME")
echo "📊 큐 '$QUEUE_NAME' 크기: $QUEUE_SIZE 개 작업"

if [ "$QUEUE_SIZE" -eq 0 ]; then
    echo "✅ 큐가 이미 비어있습니다."
    exit 0
fi

# 큐 내용 미리보기
echo ""
echo "🔍 큐 내용 미리보기 (최대 5개):"
redis-cli lrange "$QUEUE_NAME" 0 4

# 사용자 확인
echo ""
echo "⚠️  경고: 큐 '$QUEUE_NAME'의 모든 작업을 삭제합니다."
read -p "정말 삭제하시겠습니까? (y/N): " confirm

if [[ $confirm != [yY] ]]; then
    echo "❌ 작업이 취소되었습니다."
    exit 0
fi

# 큐 삭제
echo ""
echo "🗑️  큐 '$QUEUE_NAME' 삭제 중..."
redis-cli del "$QUEUE_NAME"

# 결과 확인
NEW_SIZE=$(redis-cli llen "$QUEUE_NAME")
if [ "$NEW_SIZE" -eq 0 ]; then
    echo "✅ 큐 '$QUEUE_NAME' 삭제 완료!"
else
    echo "❌ 큐 삭제 실패. 남은 작업: $NEW_SIZE 개"
    exit 1
fi

echo ""
echo "🎉 큐 '$QUEUE_NAME' 삭제가 완료되었습니다!"

