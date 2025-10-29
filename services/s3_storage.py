"""
AWS S3 스토리지 서비스
유저별 프리픽스 격리 및 Presigned URL 관리
"""
import os
import boto3
from datetime import datetime, timedelta
from typing import Optional, Dict
from botocore.exceptions import ClientError
from dotenv import load_dotenv

load_dotenv()


class S3StorageService:
    """S3 기반 파일 저장 서비스"""
    
    def __init__(self):
        self.bucket_name = os.getenv("AWS_S3_BUCKET", "summariq-audio")
        self.region = os.getenv("AWS_REGION", "ap-northeast-2")
        
        # S3 클라이언트 초기화
        self.s3_client = boto3.client(
            's3',
            region_name=self.region,
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY")
        )
        
        # 환경 설정
        self.env = os.getenv("ENVIRONMENT", "dev")  # dev, staging, prod
        self.tenant = os.getenv("TENANT", "default")
        self.project = "summariq"
        
        print(f"✅ S3 스토리지 초기화:")
        print(f"   - Bucket: {self.bucket_name}")
        print(f"   - Region: {self.region}")
        print(f"   - Environment: {self.env}")
    
    def generate_object_key(
        self,
        user_id: int,
        recording_id: str,
        asset_type: str,
        filename: str
    ) -> str:
        """
        S3 객체 키 생성 (유저별 프리픽스)
        
        Format: {env}/{tenant}/{project}/user/{userId}/{yyyy}/{mm}/{dd}/{recordingId}/{assetType}/{filename}
        
        Args:
            user_id: 사용자 ID
            recording_id: 녹음 ID
            asset_type: raw|processed|segments|transcript|metadata
            filename: 파일명
        
        Returns:
            S3 object key
        """
        now = datetime.utcnow()
        
        # 파일명 정규화 (소문자, 공백 제거)
        safe_filename = filename.lower().replace(" ", "-").replace("_", "-")
        
        key = (
            f"{self.env}/{self.tenant}/{self.project}/"
            f"user/{user_id}/"
            f"{now.year:04d}/{now.month:02d}/{now.day:02d}/"
            f"{recording_id}/"
            f"{asset_type}/"
            f"{safe_filename}"
        )
        
        return key
    
    def generate_presigned_upload_url(
        self,
        user_id: int,
        recording_id: str,
        filename: str,
        content_type: str = "audio/webm",
        expires_in: int = 3600
    ) -> Dict[str, str]:
        """
        Presigned PUT URL 생성 (클라이언트 직업로드용)
        
        Args:
            user_id: 사용자 ID
            recording_id: 녹음 ID
            filename: 원본 파일명
            content_type: MIME 타입
            expires_in: URL 만료 시간 (초, 기본 1시간)
        
        Returns:
            {
                "upload_url": str,
                "object_key": str,
                "expires_at": str
            }
        """
        # S3 키 생성
        object_key = self.generate_object_key(
            user_id=user_id,
            recording_id=recording_id,
            asset_type="raw",
            filename=filename
        )
        
        try:
            # Presigned PUT URL 생성
            url = self.s3_client.generate_presigned_url(
                ClientMethod='put_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': object_key,
                    'ContentType': content_type
                },
                ExpiresIn=expires_in
            )
            
            expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
            
            print(f"✅ Presigned URL 생성:")
            print(f"   - Key: {object_key}")
            print(f"   - Expires: {expires_at.isoformat()}")
            
            return {
                "upload_url": url,
                "object_key": object_key,
                "expires_at": expires_at.isoformat(),
                "bucket": self.bucket_name,
                "region": self.region
            }
            
        except ClientError as e:
            print(f"❌ Presigned URL 생성 실패: {e}")
            raise Exception(f"S3 URL 생성 실패: {str(e)}")
    
    def generate_presigned_download_url(
        self,
        object_key: str,
        expires_in: int = 3600
    ) -> str:
        """
        Presigned GET URL 생성 (다운로드/스트리밍용)
        
        Args:
            object_key: S3 객체 키
            expires_in: URL 만료 시간 (초)
        
        Returns:
            Presigned GET URL
        """
        try:
            url = self.s3_client.generate_presigned_url(
                ClientMethod='get_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': object_key
                },
                ExpiresIn=expires_in
            )
            
            return url
            
        except ClientError as e:
            print(f"❌ Presigned download URL 생성 실패: {e}")
            raise Exception(f"S3 다운로드 URL 생성 실패: {str(e)}")
    
    def get_public_url(self, object_key: str) -> str:
        """
        S3 객체의 공개 URL 생성
        
        Args:
            object_key: S3 객체 키
        
        Returns:
            S3 공개 URL
        """
        return f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{object_key}"
    
    def upload_file(
        self,
        file_path: str,
        user_id: int,
        recording_id: str,
        asset_type: str,
        filename: str = None
    ) -> str:
        """
        파일을 S3에 업로드 (백엔드에서 직접)
        
        Args:
            file_path: 로컬 파일 경로
            user_id: 사용자 ID
            recording_id: 녹음 ID
            asset_type: 파일 타입
            filename: S3 파일명 (None이면 원본 파일명 사용)
        
        Returns:
            S3 object key
        """
        if filename is None:
            filename = os.path.basename(file_path)
        
        object_key = self.generate_object_key(
            user_id=user_id,
            recording_id=recording_id,
            asset_type=asset_type,
            filename=filename
        )
        
        try:
            self.s3_client.upload_file(
                file_path,
                self.bucket_name,
                object_key
            )
            
            print(f"✅ S3 업로드 완료: {object_key}")
            return object_key
            
        except ClientError as e:
            print(f"❌ S3 업로드 실패: {e}")
            raise Exception(f"S3 업로드 실패: {str(e)}")
    
    def delete_user_files(self, user_id: int) -> int:
        """
        사용자의 모든 파일 삭제
        
        Args:
            user_id: 사용자 ID
        
        Returns:
            삭제된 파일 수
        """
        prefix = f"{self.env}/{self.tenant}/{self.project}/user/{user_id}/"
        
        try:
            # 사용자 프리픽스의 모든 객체 나열
            paginator = self.s3_client.get_paginator('list_objects_v2')
            pages = paginator.paginate(Bucket=self.bucket_name, Prefix=prefix)
            
            delete_count = 0
            for page in pages:
                if 'Contents' not in page:
                    continue
                
                objects = [{'Key': obj['Key']} for obj in page['Contents']]
                
                # 일괄 삭제
                if objects:
                    self.s3_client.delete_objects(
                        Bucket=self.bucket_name,
                        Delete={'Objects': objects}
                    )
                    delete_count += len(objects)
            
            print(f"✅ 사용자 {user_id} 파일 {delete_count}개 삭제 완료")
            return delete_count
            
        except ClientError as e:
            print(f"❌ S3 삭제 실패: {e}")
            raise Exception(f"S3 삭제 실패: {str(e)}")


# 싱글톤 인스턴스
_s3_storage = None

def get_s3_storage() -> S3StorageService:
    """S3 스토리지 서비스 싱글톤"""
    global _s3_storage
    if _s3_storage is None:
        _s3_storage = S3StorageService()
    return _s3_storage

