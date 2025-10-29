# 🗑️ Celery 큐 관리 스크립트 가이드

SummarIQ 프로젝트의 Celery 큐 데이터를 관리하기 위한 스크립트 모음입니다.

## 📁 스크립트 파일들

| 스크립트 | 용도 | 설명 |
|---------|------|------|
| `clear_celery_queue.sh` | 전체 큐 삭제 | 모든 Celery 큐 데이터 삭제 |
| `clear_specific_queue.sh` | 특정 큐 삭제 | 지정된 큐만 삭제 |
| `monitor_celery_queue.sh` | 큐 모니터링 | 실시간 큐 상태 확인 |

---

## 🚀 사용법

### 1️⃣ **전체 큐 삭제**

```bash
# 모든 Celery 큐 데이터 삭제
./clear_celery_queue.sh
```

**기능**:
- ✅ Redis 연결 확인
- ✅ 현재 큐 상태 표시
- ✅ 사용자 확인 후 삭제
- ✅ 삭제 결과 확인

**삭제되는 데이터**:
- 대기 중인 모든 작업
- 작업 결과 캐시
- 큐 메타데이터
- 작업 바인딩 정보

---

### 2️⃣ **특정 큐만 삭제**

```bash
# stt 큐만 삭제
./clear_specific_queue.sh stt

# summary 큐만 삭제
./clear_specific_queue.sh summary

# stt_heavy 큐만 삭제
./clear_specific_queue.sh stt_heavy
```

**기능**:
- ✅ 사용 가능한 큐 목록 표시
- ✅ 큐 크기 확인
- ✅ 큐 내용 미리보기
- ✅ 선택적 삭제

---

### 3️⃣ **큐 모니터링**

```bash
# 실시간 모니터링
./monitor_celery_queue.sh
```

**메뉴 옵션**:
1. **실시간 모니터링** (2초마다 업데이트)
2. **현재 상태만 확인**
3. **큐 내용 상세 보기**
4. **종료**

---

## 🔧 수동 명령어

### **Redis 직접 조작**

```bash
# Redis 연결 확인
redis-cli ping

# 전체 데이터베이스 삭제
redis-cli flushdb

# 특정 큐 삭제
redis-cli del stt
redis-cli del summary
redis-cli del stt_heavy

# 큐 크기 확인
redis-cli llen stt
redis-cli llen summary
redis-cli llen stt_heavy

# 큐 내용 확인
redis-cli lrange stt 0 -1
redis-cli lrange summary 0 -1

# 작업 메타데이터 삭제
redis-cli --scan --pattern "celery-task-meta-*" | xargs redis-cli del
```

---

## 🚨 주의사항

### **삭제 전 확인사항**

1. **실행 중인 작업**: 삭제하면 진행 중인 작업이 중단됩니다
2. **Celery 워커**: 큐 삭제 후 워커 재시작 권장
3. **데이터 손실**: 삭제된 작업은 복구할 수 없습니다

### **안전한 삭제 절차**

```bash
# 1. Celery 워커 중지
./stop_celery.sh

# 2. 큐 데이터 삭제
./clear_celery_queue.sh

# 3. Celery 워커 재시작
./start_celery.sh
```

---

## 📊 모니터링 도구

### **Celery Flower (웹 UI)**

```bash
# Flower 시작
celery -A celery_app flower --port=5555

# 웹 브라우저에서 접속
# http://localhost:5555
```

### **Redis 모니터링**

```bash
# 실시간 Redis 명령어 모니터링
redis-cli monitor

# Redis 정보 확인
redis-cli info

# 메모리 사용량
redis-cli info memory
```

---

## 🛠️ 문제 해결

### **일반적인 문제들**

#### 1️⃣ **Redis 연결 실패**
```bash
# Redis 서비스 시작
brew services start redis

# 또는 수동 시작
redis-server
```

#### 2️⃣ **큐가 계속 쌓임**
```bash
# Celery 워커 상태 확인
ps aux | grep celery

# 워커 재시작
./stop_celery.sh && ./start_celery.sh
```

#### 3️⃣ **작업이 처리되지 않음**
```bash
# 큐 상태 확인
./monitor_celery_queue.sh

# 특정 큐만 삭제
./clear_specific_queue.sh stt
```

---

## 📋 체크리스트

큐 관리 시 확인할 항목:

- [ ] Redis 서버 실행 중
- [ ] Celery 워커 실행 중
- [ ] 큐에 오래된 작업이 쌓여있지 않음
- [ ] 메모리 사용량 정상
- [ ] 작업 결과가 적절히 만료됨

---

## 🎯 사용 시나리오

### **개발 중**
```bash
# 코드 변경 후 큐 정리
./clear_celery_queue.sh
```

### **테스트 중**
```bash
# 특정 큐만 정리
./clear_specific_queue.sh stt
```

### **운영 중**
```bash
# 모니터링으로 상태 확인
./monitor_celery_queue.sh
```

---

## 📚 참고

- **Celery 공식 문서**: https://docs.celeryproject.org/
- **Redis 명령어**: https://redis.io/commands/
- **Flower 모니터링**: https://flower.readthedocs.io/

---

**💡 팁**: 정기적으로 큐를 모니터링하고 불필요한 데이터를 정리하면 시스템 성능이 향상됩니다!
