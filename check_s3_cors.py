#!/usr/bin/env python3
"""
S3 버킷 CORS 설정 확인 및 자동 설정
"""
import os
import boto3
import json
from dotenv import load_dotenv

load_dotenv()

bucket_name = os.getenv("AWS_S3_BUCKET", "summariq-assets")
region = os.getenv("AWS_REGION", "ap-northeast-2")

print(f"🔍 S3 버킷 CORS 확인: {bucket_name}")

s3_client = boto3.client(
    's3',
    region_name=region,
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY")
)

# 현재 CORS 설정 확인
try:
    response = s3_client.get_bucket_cors(Bucket=bucket_name)
    print("\n📋 현재 CORS 설정:")
    print(json.dumps(response['CORSRules'], indent=2))
except s3_client.exceptions.NoSuchCORSConfiguration:
    print("\n⚠️  CORS 설정이 없습니다!")
    print("\n🔧 CORS 설정을 추가하시겠습니까? (y/n): ", end="")
    
    answer = input().lower()
    if answer == 'y':
        # CORS 설정 추가
        cors_configuration = {
            'CORSRules': [
                {
                    'AllowedHeaders': ['*'],
                    'AllowedMethods': ['GET', 'PUT', 'POST', 'DELETE', 'HEAD'],
                    'AllowedOrigins': ['*'],
                    'ExposeHeaders': ['ETag', 'x-amz-request-id'],
                    'MaxAgeSeconds': 3000
                }
            ]
        }
        
        try:
            s3_client.put_bucket_cors(
                Bucket=bucket_name,
                CORSConfiguration=cors_configuration
            )
            print("✅ CORS 설정이 추가되었습니다!")
            print(json.dumps(cors_configuration['CORSRules'], indent=2))
        except Exception as e:
            print(f"❌ CORS 설정 실패: {e}")
    else:
        print("\n수동으로 CORS를 설정하세요:")
        print("1. AWS Console → S3 → 버킷 선택")
        print("2. 권한 탭 → CORS 구성")
        print("3. 다음 JSON 추가:")
        print("""
[
    {
        "AllowedHeaders": ["*"],
        "AllowedMethods": ["GET", "PUT", "POST", "DELETE", "HEAD"],
        "AllowedOrigins": ["*"],
        "ExposeHeaders": ["ETag", "x-amz-request-id"],
        "MaxAgeSeconds": 3000
    }
]
""")
except Exception as e:
    print(f"❌ CORS 확인 실패: {e}")

