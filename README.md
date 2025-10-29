<<<<<<< HEAD
# SummarIQ Backend API

FastAPI 기반 음성 녹음 및 STT(Speech-to-Text) 백엔드 서버

## 🚀 빠른 시작

### 1. 의존성 설치

```bash
cd backend
pip install -r requirements.txt
```

### 2. ffmpeg 설치 (오디오 변환용)

**Mac:**
```bash
brew install ffmpeg
```

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install ffmpeg
```

### 3. Google Cloud 설정

1. [Google Cloud Console](https://console.cloud.google.com/)에서 프로젝트 생성
2. Speech-to-Text API 활성화
3. 서비스 계정 생성 및 JSON 키 다운로드
4. 키 파일을 `backend/summariq-credentials.json`으로 저장

### 4. 환경 변수 설정

```bash
cp .env.example .env
```

`.env` 파일 수정:
```env
GOOGLE_APPLICATION_CREDENTIALS=./summariq-credentials.json
GOOGLE_CLOUD_PROJECT_ID=your-project-id-here
```

### 5. 서버 실행

```bash
python main.py
```

서버 주소: http://localhost:8000  
API 문서: http://localhost:8000/docs

## 📡 API 엔드포인트

### STT 관련

| Method | Endpoint | 설명 |
|--------|----------|------|
| POST | `/stt/start` | 녹음 세션 시작 |
| POST | `/stt/chunk` | 세그먼트 업로드 및 STT |
| POST | `/stt/commit` | 녹음 종료 및 합본 |
| GET | `/recordings` | 녹음 목록 조회 |
| GET | `/recordings/{id}` | 녹음 상세 조회 |
| DELETE | `/recordings/{id}` | 녹음 삭제 |

### 예시

#### 1. 녹음 시작
```bash
curl -X POST http://localhost:8000/stt/start \
  -H "Content-Type: application/json" \
  -d '{"title": "테스트 녹음"}'
```

#### 2. 세그먼트 업로드
```bash
curl -X POST http://localhost:8000/stt/chunk \
  -F "recordingId=abc-123" \
  -F "seq=0" \
  -F "file=@segment_0.m4a"
```

#### 3. 녹음 종료
```bash
curl -X POST http://localhost:8000/stt/commit \
  -H "Content-Type: application/json" \
  -d '{"recordingId": "abc-123"}'
```

## 🏗️ 프로젝트 구조

```
backend/
├─ main.py                      # FastAPI 앱
├─ routers/
│   └─ stt.py                  # STT 라우터
├─ services/
│   ├─ google_stt.py           # Google STT 서비스
│   └─ audio_processor.py      # 오디오 변환
├─ requirements.txt
├─ .env
├─ .env.example
└─ summariq-credentials.json   # Google 서비스 계정 키
```

## ⚙️ 설정

### 지원 언어

기본: 한국어(`ko-KR`), 영어(`en-US`)

`services/google_stt.py`에서 수정 가능:
```python
language_codes = ["ko-KR", "en-US", "ja-JP"]  # 일본어 추가
```

### 오디오 형식

- 입력: M4A (AAC)
- 변환: OGG Opus, 16kHz, 모노
- 세그먼트 크기: 2초 권장

## 💰 비용

Google Speech-to-Text 가격:
- **무료:** 월 60분
- **유료:** 분당 $0.006 ~ $0.024

자세한 내용: https://cloud.google.com/speech-to-text/pricing

## 🔒 보안

**중요:** `summariq-credentials.json`을 절대 Git에 커밋하지 마세요!

`.gitignore`에 이미 추가되어 있습니다.

## 🐛 문제 해결

### "API not enabled" 오류
→ Google Cloud Console에서 Speech-to-Text API 활성화

### "Permission denied" 오류
→ 서비스 계정 권한 확인 (`Cloud Speech 클라이언트` 역할 필요)

### ffmpeg 관련 오류
→ ffmpeg 설치 확인: `ffmpeg -version`

### CORS 오류
→ `.env`의 `ALLOWED_ORIGINS` 설정 확인

## 📚 참고 자료

- [Google Speech-to-Text 문서](https://cloud.google.com/speech-to-text/docs)
- [FastAPI 문서](https://fastapi.tiangolo.com/)
- [pydub 문서](https://github.com/jiaaro/pydub)

=======
# SummarIQ.ai
AI 기반 사용자 회의 요약 및 분석 플랫폼
>>>>>>> 7dbc68d1cc7bddeea82da28850a5b04f64b7c6a3
