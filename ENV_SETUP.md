# 환경 변수 설정 가이드

## 📋 .env 파일 생성

`backend/.env` 파일을 생성하고 아래 내용을 추가하세요:

```bash
# OpenAI API Key
OPENAI_API_KEY=your_openai_api_key_here

# Google Cloud STT
GOOGLE_APPLICATION_CREDENTIALS=summariq-credentials.json

# MySQL Database Configuration
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your-mysql-password
MYSQL_DATABASE=summariq

# Server Configuration
# Mac의 실제 IP 주소 입력 (아래 명령어로 확인)
# ifconfig | grep "inet " | grep -v 127.0.0.1
SERVER_HOST=10.9.118.119
SERVER_PORT=8000
```

## 🔍 IP 주소 확인 방법

### 방법 1: 터미널
```bash
ifconfig | grep "inet " | grep -v 127.0.0.1
```

출력 예시:
```
inet 10.9.118.119 netmask 0xfffff800 broadcast 10.9.119.255
```

### 방법 2: 시스템 환경설정
1. 시스템 환경설정 열기
2. 네트워크 클릭
3. 연결된 Wi-Fi 선택
4. IP 주소 확인

## ⚠️ IP 주소 변경 시

Wi-Fi 네트워크가 변경되면 IP 주소도 변경됩니다.

### 자동 업데이트 스크립트
```bash
cd /Users/dlckdfuf/Desktop/SummarIQ/backend
./update_server_ip.sh
```

이 스크립트가 자동으로:
1. 현재 IP 주소 감지
2. .env 파일 업데이트
3. 기존 녹음 URL 업데이트
4. 서버 재시작

## 🧪 테스트

`.env` 파일 설정 후:

```bash
# 설정 확인
cd backend
source venv/bin/activate
python -c "from database.config import SERVER_BASE_URL; print(f'Server URL: {SERVER_BASE_URL}')"

# API 테스트
curl http://localhost:8000/stt/start
```

## 📝 프론트엔드 설정

`lib/sttApi.ts`도 동일한 IP를 사용하도록 수정하세요:

```typescript
const API_BASE_URL = __DEV__ ? 'http://10.9.118.119:8000' : 'https://api.summariq.app';
```

IP 변경 시:
1. `backend/.env`의 `SERVER_HOST` 변경
2. `lib/sttApi.ts`의 IP 변경
3. 서버 재시작

