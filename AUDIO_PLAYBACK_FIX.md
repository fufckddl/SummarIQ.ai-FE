# 오디오 재생 문제 해결 가이드

## 문제 증상

### iOS 재생 오류
```
Error: The AVPlayerItem instance has failed 
with the error code -1001/-1004 and domain "NSURLErrorDomain"
```

## 근본 원인 분석

### 1. 에러 코드 의미

| 코드 | 의미 | 원인 |
|------|------|------|
| -1001 | 타임아웃 | 서버 응답 없음 또는 느림 |
| -1004 | 서버 연결 불가 | 잘못된 URL 또는 서버 다운 |

### 2. 실제 문제들

#### A) 잘못된 IP 주소 ❌
```python
# audio_url에 저장된 값
http://192.168.0.160:8000/stt/audio/{id}  # 이전 IP (접근 불가)

# 실제 서버 IP
http://192.168.0.166:8000/stt/audio/{id}  # 현재 IP
```

#### B) Range 요청 미지원 ❌
iOS AVPlayer는 **필수적으로** HTTP Range 요청을 사용합니다:
```http
GET /stt/audio/{id}
Range: bytes=0-1023
```

서버가 Range를 지원하지 않으면:
- 작은 파일(~1MB): 재생 가능
- 큰 파일(>10MB): 타임아웃 또는 실패

#### C) CORS 헤더 누락 ❌
```
Access-Control-Allow-Origin
Access-Control-Expose-Headers: Content-Range, Accept-Ranges
```

## 해결 방법

### ✅ 1. Range 요청 지원 추가
**파일**: `backend/routers/stt.py` → `get_audio_file()` 수정

**변경 사항**:
```python
# Range 헤더 확인
if range_header:
    # 206 Partial Content 응답
    return StreamingResponse(
        iterfile(),
        status_code=206,
        headers={
            "Content-Range": f"bytes {start}-{end}/{file_size}",
            "Accept-Ranges": "bytes",
        }
    )
else:
    # 200 OK 응답 (Accept-Ranges 헤더 포함)
    return FileResponse(
        path=file_path,
        headers={"Accept-Ranges": "bytes"}
    )
```

### ✅ 2. IP 주소 환경변수 관리
**파일**: `backend/database/config.py`

**변경 사항**:
```python
# 환경변수 필수
SERVER_HOST = os.getenv("SERVER_HOST")
if not SERVER_HOST:
    raise ValueError("SERVER_HOST 환경변수가 필요합니다")

SERVER_BASE_URL = f"http://{SERVER_HOST}:{SERVER_PORT}"
```

**`.env` 파일**:
```bash
SERVER_HOST=192.168.0.166  # ← IP 변경 시 여기만 수정
SERVER_PORT=8000
```

### ✅ 3. 기존 녹음 URL 일괄 수정
```sql
UPDATE recordings 
SET audio_url = REPLACE(audio_url, '192.168.0.160', '192.168.0.166') 
WHERE audio_url LIKE '%192.168.0.160%';
```

### ✅ 4. CORS 헤더 추가 (이미 적용됨)
**파일**: `backend/main.py`

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Range", "Accept-Ranges"]  # ← 추가
)
```

## 테스트 방법

### 1. 백엔드 확인
```bash
# IP 확인
ifconfig | grep "inet " | grep -v 127.0.0.1

# 서버 재시작
cd backend
./stop_server.sh
./start_server.sh

# 오디오 API 테스트
curl -I http://192.168.0.166:8000/stt/audio/{recording_id}
# 응답에 "Accept-Ranges: bytes" 확인

# Range 요청 테스트
curl -H "Range: bytes=0-1023" http://192.168.0.166:8000/stt/audio/{recording_id}
# 206 Partial Content 응답 확인
```

### 2. 앱 테스트
```
1. 앱 재시작
2. 녹음 목록 → 녹음 선택
3. 재생 버튼 클릭
4. 오디오 재생 확인
```

### 3. 로그 확인
```bash
# 서버 로그에서 Range 요청 확인
tail -f backend/server.log | grep "GET /stt/audio"

# 예상 로그:
# GET /stt/audio/{id} HTTP/1.1" 206 Partial Content
# (206 = Range 요청 성공)
```

## 예방 조치

### 1. .env로 IP 관리
```bash
# backend/.env
SERVER_HOST=192.168.0.166  # ← 변경 필요 시 여기만 수정

# frontend/.env
EXPO_PUBLIC_API_URL=http://192.168.0.166:8000  # ← 여기도 동기화
```

### 2. IP 자동 업데이트 스크립트
**파일**: `backend/update_server_ip.sh` (이미 존재)

```bash
./update_server_ip.sh  # 자동으로 현재 IP 감지 및 업데이트
```

### 3. 서버 시작 시 IP 출력
**파일**: `backend/start_server.sh`에 추가

```bash
echo "📡 현재 서버 IP:"
ifconfig | grep "inet " | grep -v 127.0.0.1 | awk '{print "   - " $2}'
echo ""
echo "⚠️  .env 파일의 SERVER_HOST와 일치하는지 확인하세요!"
```

## 성능 최적화

### Range 요청 장점
1. **메모리 효율**: 전체 파일을 메모리에 로드하지 않음
2. **빠른 시작**: 처음 몇 KB만 받아서 즉시 재생
3. **탐색 기능**: 사용자가 중간으로 건너뛸 수 있음
4. **iOS 필수**: AVPlayer가 Range 요청 없이는 큰 파일 재생 불가

### 청크 크기 조정
```python
# 현재: 8KB 청크
read_size = min(8192, remaining)

# 네트워크 느리면: 64KB로 증가
read_size = min(65536, remaining)
```

## 문제 해결 체크리스트

- [x] Range 요청 지원 추가
- [x] Accept-Ranges 헤더 추가
- [x] IP 주소 환경변수화
- [x] 기존 녹음 URL 업데이트
- [x] CORS 헤더 확인
- [ ] 백엔드 서버 재시작
- [ ] 앱에서 재생 테스트

## 추가 디버깅

### 문제가 계속되면

#### 1. 네트워크 확인
```bash
# Mac과 iPhone이 같은 Wi-Fi에 있는지 확인
# iPhone에서 Safari 열고:
http://192.168.0.166:8000/health

# 응답이 오면 네트워크 OK
```

#### 2. 파일 존재 확인
```bash
# 서버에서 확인
ls -lh backend/storage/audio/{recording_id}/full.*

# 파일이 없으면: 업로드 실패
# 파일이 0바이트면: 저장 실패
```

#### 3. 로그 분석
```bash
# Range 요청 로그
tail -f backend/server.log | grep -E "(Range|206|audio)"

# 예상 로그:
# Range: bytes=0-1023
# 206 Partial Content
```

## 요약

### 근본 원인
1. **IP 주소 불일치** (160 vs 166)
2. **Range 요청 미지원** (iOS 필수)
3. **하드코딩된 설정** (환경변수 미사용)

### 해결 완료
1. ✅ Range 요청 지원 (206 Partial Content)
2. ✅ IP 주소 .env 관리
3. ✅ 기존 DB 업데이트
4. ✅ Accept-Ranges 헤더 추가

### 남은 작업
- **백엔드 재시작** (필수)
- 앱 테스트

재시작 후 모든 녹음이 정상 재생될 것입니다! 🎵

