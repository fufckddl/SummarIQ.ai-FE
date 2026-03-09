# S3 Direct Upload 구현 가이드

## 📌 개요

**문제**: 대용량 파일(100MB+)을 프론트엔드 → 백엔드로 업로드 시 2분 이상 소요

**해결**: S3 Presigned URL을 사용한 클라이언트 직업로드

```
[기존] 프론트 → 백엔드(132MB, 2분) → 압축(13MB) → AssemblyAI
[개선] 프론트 → S3(132MB, 10초) → 백엔드(다운로드 13MB) → AssemblyAI
```

**효과**: 업로드 시간 **90% 단축** (2분 → 10초)

---

## 🔧 설치 및 설정

### 1. Python 패키지 설치

```bash
cd backend
pip install boto3==1.35.0
```

### 2. AWS S3 버킷 생성

AWS Console에서:
1. S3 버킷 생성: `summariq-audio`
2. 리전: `ap-northeast-2` (서울)
3. CORS 설정 추가:

```json
[
    {
        "AllowedHeaders": ["*"],
        "AllowedMethods": ["GET", "PUT", "POST", "DELETE"],
        "AllowedOrigins": ["*"],
        "ExposeHeaders": ["ETag"]
    }
]
```

### 3. IAM 사용자 생성 및 권한 부여

1. IAM → 사용자 생성
2. 정책 연결: `AmazonS3FullAccess` (또는 커스텀 정책)
3. Access Key 생성 (키 ID, 시크릿 키 저장)

**커스텀 정책 (권장)**:
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:PutObject",
                "s3:GetObject",
                "s3:DeleteObject",
                "s3:ListBucket"
            ],
            "Principal": "*",
            "Resource": [
                "arn:aws:s3:::summariq-audio",
                "arn:aws:s3:::summariq-audio/*"
            ]
        }
    ]
}
```

### 4. 환경 변수 설정

`backend/.env` 파일에 추가:

```bash
# AWS S3
AWS_ACCESS_KEY_ID=your-access-key-id
AWS_SECRET_ACCESS_KEY=your-secret-access-key
AWS_REGION=ap-northeast-2
AWS_S3_BUCKET=summariq-audio

# 환경
ENVIRONMENT=dev  # dev, staging, prod
TENANT=default
```

---

## 🚀 사용 방법

### 프론트엔드 (React Native / Expo)

**기존 방식**:
```typescript
import { uploadAudioFile } from '@/lib/sttApi';

// 직접 백엔드로 업로드 (느림)
const result = await uploadAudioFile(fileUri, fileName);
```

**S3 직업로드 방식**:
```typescript
import { uploadAudioFileToS3 } from '@/lib/s3UploadApi';

// S3로 직업로드 (빠름)
const result = await uploadAudioFileToS3(
  fileUri,
  fileName,
  (progress) => console.log(`업로드 ${progress}%`)
);

console.log('Recording ID:', result.recordingId);
console.log('Task ID:', result.taskId);
```

### API 플로우

**1. Presigned URL 요청**
```http
POST /upload/presigned-url
Authorization: Bearer <token>
Content-Type: application/json

{
  "filename": "meeting-2025-01-15.webm",
  "content_type": "audio/webm"
}
```

**응답**:
```json
{
  "upload_url": "https://summariq-audio.s3.ap-northeast-2.amazonaws.com/...",
  "object_key": "dev/default/summariq/user/1/2025/01/15/uuid/raw/meeting.webm",
  "recording_id": "uuid",
  "expires_at": "2025-01-15T12:00:00Z",
  "bucket": "summariq-audio",
  "region": "ap-northeast-2"
}
```

**2. S3 직접 업로드**
```http
PUT <upload_url>
Content-Type: audio/webm

<binary data>
```

**3. 업로드 완료 알림**
```http
POST /upload/complete
Authorization: Bearer <token>
Content-Type: application/json

{
  "recording_id": "uuid",
  "object_key": "dev/default/summariq/user/1/...",
  "file_size": 138649600
}
```

**응답**:
```json
{
  "recording_id": "uuid",
  "task_id": "celery-task-id",
  "status": "processing",
  "message": "S3 업로드 완료. STT 처리가 시작되었습니다."
}
```

---

## 📊 S3 객체 키 구조

**Format**:
```
{env}/{tenant}/{project}/user/{userId}/{yyyy}/{mm}/{dd}/{recordingId}/{assetType}/{filename}
```

**예시**:
```
dev/default/summariq/user/1/2025/01/15/abc-123-def/raw/meeting.webm
dev/default/summariq/user/1/2025/01/15/abc-123-def/processed/compressed.webm
dev/default/summariq/user/1/2025/01/15/abc-123-def/transcript/output.json
```

**장점**:
- ✅ 유저별 격리 (프라이버시)
- ✅ 날짜별 파티셔닝 (빠른 검색)
- ✅ 파일 타입별 분류 (관리 용이)

---

## 🔐 보안

### 1. Presigned URL 만료 시간
- 기본: 1시간 (3600초)
- 업로드 완료 전까지만 유효

### 2. 사용자 격리
- S3 키에 `user/{userId}` 포함
- 다른 사용자 파일 접근 불가

### 3. CORS 설정
- S3 버킷 CORS 정책으로 허용된 도메인만 업로드 가능

---

## 🧪 테스트

### 1. Presigned URL 생성 테스트

```bash
curl -X POST http://localhost:8000/upload/presigned-url \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "filename": "test.webm",
    "content_type": "audio/webm"
  }'
```

### 2. S3 업로드 테스트

```bash
# 1. Presigned URL 받기
UPLOAD_URL="<presigned_url>"

# 2. 파일 업로드
curl -X PUT "$UPLOAD_URL" \
  -H "Content-Type: audio/webm" \
  --upload-file /path/to/audio.webm
```

### 3. 업로드 완료 알림

```bash
curl -X POST http://localhost:8000/upload/complete \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "recording_id": "<recording_id>",
    "object_key": "<object_key>",
    "file_size": 138649600
  }'
```

---

## 🐛 트러블슈팅

### 1. `AccessDenied` 에러
**원인**: IAM 권한 부족
**해결**: IAM 사용자에 `s3:PutObject` 권한 추가

### 2. CORS 에러
**원인**: S3 버킷 CORS 설정 누락
**해결**: S3 버킷 → 권한 → CORS 구성 추가

### 3. `SignatureDoesNotMatch` 에러
**원인**: AWS Access Key 또는 Secret Key 오류
**해결**: `.env` 파일의 키 확인

### 4. 업로드 느림
**원인**: 네트워크 속도 또는 파일 크기
**해결**: 
- 파일 압축 (백엔드에서 자동 처리)
- 병렬 처리 (30분+ 파일)

---

## 📈 성능 비교

| 항목 | 기존 방식 | S3 직업로드 |
|------|----------|------------|
| 업로드 시간 (132MB) | 2분 | 10초 |
| 백엔드 부하 | 높음 | 낮음 |
| 확장성 | 제한적 | 우수 |
| 비용 | 서버 대역폭 | S3 스토리지 |

---

## 🔄 마이그레이션 가이드

### 기존 API와 공존

기존 `/stt/upload` 엔드포인트는 **유지**됩니다.
클라이언트는 선택적으로 S3 업로드 사용 가능:

```typescript
// 옵션 1: 기존 방식 (소용량 파일)
if (fileSize < 10 * 1024 * 1024) {
  await uploadAudioFile(fileUri, fileName);
}

// 옵션 2: S3 직업로드 (대용량 파일)
else {
  await uploadAudioFileToS3(fileUri, fileName);
}
```

---

## 📚 참고 자료

- [AWS S3 Presigned URLs](https://docs.aws.amazon.com/AmazonS3/latest/userguide/PresignedUrlUploadObject.html)
- [Boto3 Documentation](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html)
- [S3 CORS Configuration](https://docs.aws.amazon.com/AmazonS3/latest/userguide/cors.html)

---

## ✅ 체크리스트

### 설정
- [ ] boto3 설치
- [ ] S3 버킷 생성
- [ ] IAM 사용자 생성 및 권한 부여
- [ ] S3 CORS 설정
- [ ] `.env` 파일 설정

### 테스트
- [ ] Presigned URL 생성 확인
- [ ] S3 업로드 성공 확인
- [ ] Celery 작업 시작 확인
- [ ] STT 처리 완료 확인

### 배포
- [ ] Production 환경 변수 설정
- [ ] S3 버킷 권한 점검
- [ ] 모니터링 설정 (CloudWatch)

