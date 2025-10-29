#!/bin/bash

# SummarIQ Celery 큐 모니터링 스크립트
# 사용법: ./monitor_celery_queue.sh

echo "📊 SummarIQ Celery 큐 모니터링"
echo "==============================="

# Redis 연결 확인
echo "📡 Redis 연결 확인 중..."
if ! redis-cli ping > /dev/null 2>&1; then
    echo "❌ Redis 서버에 연결할 수 없습니다."
    exit 1
fi
echo "✅ Redis 연결 성공"

# 실시간 모니터링 함수
monitor_queues() {
    while true; do
        clear
        echo "📊 SummarIQ Celery 큐 모니터링 - $(date)"
        echo "=========================================="
        
        # 전체 키 개수
        TOTAL_KEYS=$(redis-cli dbsize)
        echo "🔢 총 키 개수: $TOTAL_KEYS"
        
        # 큐별 크기
        echo ""
        echo "📋 큐별 상태:"
        for queue in stt summary; do
            size=$(redis-cli llen "$queue" 2>/dev/null || echo "0")
            echo "   $queue: $size 개 작업"
        done
        
        # 작업 메타데이터 개수
        META_COUNT=$(redis-cli --scan --pattern "celery-task-meta-*" | wc -l)
        echo "   작업 메타데이터: $META_COUNT 개"
        
        # 최근 작업들 (최대 3개)
        echo ""
        echo "🔄 최근 작업들:"
        redis-cli --scan --pattern "celery-task-meta-*" | head -3 | while read key; do
            if [ ! -z "$key" ]; then
                # Celery 메타데이터는 JSON 문자열로 저장됨
                status=$(redis-cli get "$key" 2>/dev/null | grep -o '"status":"[^"]*"' | cut -d'"' -f4 || echo "unknown")
                echo "   $key: $status"
            fi
        done
        
        echo ""
        echo "⏰ 업데이트: $(date '+%H:%M:%S')"
        echo "종료하려면 Ctrl+C를 누르세요"
        
        sleep 2
    done
}

# 메뉴 표시
echo ""
echo "📋 모니터링 옵션:"
echo "1) 실시간 모니터링 (2초마다 업데이트)"
echo "2) 현재 상태만 확인"
echo "3) 큐 내용 상세 보기"
echo "4) 종료"
echo ""

read -p "선택하세요 (1-4): " choice

case $choice in
    1)
        echo "🔄 실시간 모니터링 시작..."
        monitor_queues
        ;;
    2)
        echo "📊 현재 상태:"
        redis-cli info keyspace
        echo ""
        echo "📋 큐별 크기:"
        for queue in stt summary; do
            size=$(redis-cli llen "$queue" 2>/dev/null || echo "0")
            echo "   $queue: $size 개 작업"
        done
        ;;
    3)
        echo "🔍 큐 내용 상세:"
        for queue in stt summary; do
            size=$(redis-cli llen "$queue" 2>/dev/null || echo "0")
            if [ "$size" -gt 0 ]; then
                echo ""
                echo "📋 큐 '$queue' 내용:"
                redis-cli lrange "$queue" 0 4
            fi
        done
        ;;
    4)
        echo "👋 종료합니다."
        exit 0
        ;;
    *)
        echo "❌ 잘못된 선택입니다."
        exit 1
        ;;
esac
