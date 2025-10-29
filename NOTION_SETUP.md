# Notion 연동 설정 가이드

## 📋 개요

사용자별로 Notion OAuth를 통해 연결하고, 회의 요약을 자동으로 사용자의 Notion 워크스페이스에 업로드

## 🔧 Notion Integration 생성

### 1. Notion Integration 만들기

1. https://www.notion.so/my-integrations 접속
2. "+ New integration" 클릭
3. 정보 입력:
   - **Name**: SummarIQ
   - **Associated workspace**: 본인 워크스페이스 선택
   - **Type**: Public integration 선택
   - **Capabilities**: Read content, Update content, Insert content
4. "Submit" 클릭

### 2. OAuth 설정

Integration 설정 페이지에서:

1. **OAuth Domain & URIs** 섹션:
   - **Redirect URIs** 추가:
     ```
     http://192.168.0.160:8000/notion/oauth/callback  (개발용)
     https://api.summariq.app/notion/oauth/callback   (프로덕션)
     ```

2. **Secrets** 탭에서 확인:
   - **OAuth client ID**: 복사
   - **OAuth client secret**: "Show" 클릭 후 복사

### 3. 환경 변수 설정

`backend/.env` 파일에 추가:

```bash
# Notion OAuth
NOTION_CLIENT_ID=your_client_id_here
NOTION_CLIENT_SECRET=your_client_secret_here
NOTION_REDIRECT_URI=http://192.168.0.160:8000/notion/oauth/callback

# Notion 토큰 암호화 키 (32바이트 base64)
# 생성: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
NOTION_ENCRYPTION_KEY=your_encryption_key_here
```

### 4. 암호화 키 생성

```bash
cd backend
source venv/bin/activate
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

출력된 키를 `.env`의 `NOTION_ENCRYPTION_KEY`에 복사

---

## 🚀 사용 흐름

### 1️⃣ Notion 연결 (OAuth)

**앱에서:**
1. 설정 → "Notion 연결" 버튼
2. Notion 로그인 페이지로 이동
3. 권한 승인
4. 콜백 완료 → "연결 완료!" 메시지

**API:**
```
GET /notion/oauth/start
  → { "authUrl": "https://api.notion.com/..." }

GET /notion/oauth/callback?code=xxx&state=user_id
  → 토큰 저장 (암호화)
```

### 2️⃣ 업로드 대상 선택

**앱에서:**
1. Notion 연결 후 → "대상 선택" 화면
2. 검색 또는 URL 붙여넣기
3. 데이터베이스/페이지 선택
4. "테스트 업로드" → 권한 확인

**API:**
```
GET /notion/search?q=회의&type=database
  → { "results": [{ "id": "xxx", "title": "회의록" }] }

POST /notion/target
  { "target_type": "database", "target_id": "xxx", "as_default": true }
```

### 3️⃣ 자동 업로드

**회의 종료 후:**
```
POST /notion/upload-summary
  { "recording_id": "uuid" }

→ 기본 대상에 페이지 생성
→ { "notionPageUrl": "https://notion.so/..." }
```

---

## 📊 Notion 페이지 구조

### Database에 생성되는 페이지

**Properties:**
- **Name** (title): 회의 제목
- **Date** (date): 회의 시작 시간
- **Participants** (multi_select): 참석자
- **Tags** (multi_select): 태그

**Content (Blocks):**
```
📝 요약
[요약 내용...]

✅ 결정사항
• 결정사항 1
• 결정사항 2

🎯 액션 아이템
☐ 액션 1 (@담당자) [~마감일]
☐ 액션 2
```

---

## 🔐 보안

### 토큰 암호화

- Notion access token은 **암호화하여 DB 저장**
- `cryptography.Fernet` 사용 (AES-128)
- 암호화 키는 환경변수로 관리

### 권한 검증

- OAuth는 **사용자별**로 분리
- 업로드는 **본인 녹음만** 가능
- Notion API 호출 시 사용자의 토큰 사용

---

## 🐛 트러블슈팅

### "봇을 초대해주세요" 오류

**원인**: Notion 봇이 대상 데이터베이스/페이지에 접근 권한이 없음

**해결:**
1. Notion에서 대상 데이터베이스/페이지 열기
2. 우측 상단 "..." → "Connections" → "Add connections"
3. "SummarIQ" 선택하여 초대

### OAuth 실패

**원인**: Redirect URI 불일치

**해결:**
1. Integration 설정에서 Redirect URI 확인
2. `.env`의 `NOTION_REDIRECT_URI`와 일치하는지 확인
3. 서버 재시작

### 검색 결과 없음

**원인**: 봇이 초대된 페이지만 검색됨

**해결:**
1. Notion에서 원하는 데이터베이스/페이지에 봇 초대
2. 검색 다시 시도

---

## 📈 향후 개선

- [ ] 규칙 기반 라우팅 (태그별로 다른 DB에 저장)
- [ ] 자동 속성 생성 (DB에 Date 속성 없으면 자동 추가)
- [ ] 실시간 동기화 (Notion 변경사항 → 앱 반영)
- [ ] 템플릿 커스터마이징
- [ ] 다중 워크스페이스 지원


