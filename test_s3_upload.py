#!/usr/bin/env python3
"""
S3 업로드 시스템 테스트 스크립트
"""
import os
import sys
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# 환경 변수 확인
print("🔍 S3 환경 변수 확인...")

required_vars = [
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
    "AWS_REGION",
    "AWS_S3_BUCKET",
    "ENVIRONMENT",
    "TENANT"
]

missing_vars = []
for var in required_vars:
    value = os.getenv(var)
    if value:
        # 민감한 정보는 마스킹
        if "KEY" in var or "SECRET" in var:
            masked = value[:4] + "****" + value[-4:] if len(value) > 8 else "****"
            print(f"✅ {var}: {masked}")
        else:
            print(f"✅ {var}: {value}")
    else:
        print(f"❌ {var}: 설정되지 않음")
        missing_vars.append(var)

if missing_vars:
    print(f"\n⚠️  누락된 환경 변수: {', '.join(missing_vars)}")
    print("backend/.env 파일을 확인하세요.")
    sys.exit(1)

print("\n🧪 boto3 import 테스트...")
try:
    import boto3
    print("✅ boto3 import 성공")
except ImportError as e:
    print(f"❌ boto3 import 실패: {e}")
    print("pip install boto3==1.35.0 실행 필요")
    sys.exit(1)

print("\n🔗 S3 연결 테스트...")
try:
    s3_client = boto3.client(
        's3',
        region_name=os.getenv("AWS_REGION"),
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY")
    )
    
    # 버킷 존재 확인
    bucket_name = os.getenv("AWS_S3_BUCKET")
    s3_client.head_bucket(Bucket=bucket_name)
    print(f"✅ S3 버킷 '{bucket_name}' 접근 가능")
    
except Exception as e:
    print(f"❌ S3 연결 실패: {e}")
    print("\n해결 방법:")
    print("1. AWS 자격 증명 확인")
    print("2. S3 버킷이 존재하는지 확인")
    print("3. IAM 권한 확인 (s3:ListBucket, s3:GetObject, s3:PutObject)")
    sys.exit(1)

print("\n🎯 S3 Storage Service 테스트...")
try:
    from services.s3_storage import get_s3_storage
    
    s3_service = get_s3_storage()
    
    # Presigned URL 생성 테스트
    print("\n📝 Presigned URL 생성 테스트...")
    result = s3_service.generate_presigned_upload_url(
        user_id=1,
        recording_id="test-123-abc",
        filename="test-audio.webm",
        content_type="audio/webm",
        expires_in=300  # 5분
    )
    
    print(f"✅ Upload URL 생성 성공")
    print(f"   - Object Key: {result['object_key']}")
    print(f"   - Bucket: {result['bucket']}")
    print(f"   - Region: {result['region']}")
    print(f"   - Expires: {result['expires_at']}")
    
except Exception as e:
    print(f"❌ S3 Storage Service 실패: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "="*60)
print("✅ 모든 테스트 통과!")
print("="*60)
print("\n다음 단계:")
print("1. 프론트엔드에서 /upload/presigned-url API 호출")
print("2. 받은 URL로 S3에 직접 업로드")
print("3. /upload/complete API 호출하여 STT 시작")
print("\n자세한 내용은 S3_DIRECT_UPLOAD.md 참조")

