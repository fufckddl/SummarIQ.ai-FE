"""
S3 Presigned URL 업로드 라우터
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from database.connection import get_db
from services.s3_storage import get_s3_storage
from services.jwt_service import JWTService
from pydantic import BaseModel
from typing import Optional
import uuid

router = APIRouter(prefix="/upload", tags=["upload"])


class PresignedUploadRequest(BaseModel):
    """Presigned URL 요청"""
    filename: str
    content_type: Optional[str] = "audio/webm"
    recording_id: Optional[str] = None  # 제공하지 않으면 자동 생성


class PresignedUploadResponse(BaseModel):
    """Presigned URL 응답"""
    upload_url: str
    object_key: str
    recording_id: str
    expires_at: str
    bucket: str
    region: str


@router.post("/presigned-url", response_model=PresignedUploadResponse)
async def create_presigned_upload_url(
    request_data: PresignedUploadRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    S3 Presigned PUT URL 생성
    클라이언트가 이 URL로 직접 S3에 업로드
    
    Args:
        request_data: 파일 정보
        request: HTTP 요청 (JWT 토큰 추출)
        db: DB 세션
    
    Returns:
        Presigned URL 및 메타데이터
    """
    try:
        # 사용자 인증
        jwt_service = JWTService()
        authorization = request.headers.get("Authorization")
        
        if not authorization:
            raise HTTPException(status_code=401, detail="인증이 필요합니다")
        
        token = authorization.replace("Bearer ", "")
        user_id = jwt_service.get_user_id_from_token(token)
        
        print(f"🔐 Presigned URL 요청: user_id={user_id}, filename={request_data.filename}")
        
        # Recording ID 생성 또는 사용
        recording_id = request_data.recording_id or str(uuid.uuid4())
        
        # S3 Presigned URL 생성
        s3_service = get_s3_storage()
        result = s3_service.generate_presigned_upload_url(
            user_id=user_id,
            recording_id=recording_id,
            filename=request_data.filename,
            content_type=request_data.content_type,
            expires_in=3600  # 1시간
        )
        
        # DB에 recording 생성 (상태: uploading)
        from database import crud
        
        title = request_data.filename.rsplit('.', 1)[0][:100]
        recording = crud.create_recording(
            db,
            id=recording_id,
            title=title,
            user_id=user_id,
            status="recording"  # 업로드 대기 상태
        )
        
        print(f"✅ Recording 생성: {recording_id}")
        
        return PresignedUploadResponse(
            upload_url=result["upload_url"],
            object_key=result["object_key"],
            recording_id=recording_id,
            expires_at=result["expires_at"],
            bucket=result["bucket"],
            region=result["region"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Presigned URL 생성 실패: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"URL 생성 실패: {str(e)}")


class UploadCompleteRequest(BaseModel):
    """업로드 완료 알림"""
    recording_id: str
    object_key: str
    file_size: int  # 바이트


@router.post("/complete")
async def upload_complete(
    request_data: UploadCompleteRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    S3 업로드 완료 알림 및 STT 처리 시작
    
    클라이언트가 S3 업로드 완료 후 이 엔드포인트 호출
    → Celery 큐에 STT 작업 추가
    
    Args:
        request_data: 업로드 완료 정보
        request: HTTP 요청
        db: DB 세션
    
    Returns:
        작업 정보
    """
    try:
        # 사용자 인증
        jwt_service = JWTService()
        authorization = request.headers.get("Authorization")
        
        if not authorization:
            raise HTTPException(status_code=401, detail="인증이 필요합니다")
        
        token = authorization.replace("Bearer ", "")
        user_id = jwt_service.get_user_id_from_token(token)
        
        recording_id = request_data.recording_id
        object_key = request_data.object_key
        
        print(f"📦 업로드 완료 알림: recording_id={recording_id}")
        print(f"   - Object Key: {object_key}")
        print(f"   - File Size: {request_data.file_size / 1024 / 1024:.1f}MB")
        
        # Recording 상태 업데이트
        from database import crud
        
        recording = crud.get_recording(db, recording_id)
        if not recording or recording.user_id != user_id:
            raise HTTPException(status_code=404, detail="Recording not found")
        
        # S3 URL 저장
        s3_service = get_s3_storage()
        s3_url = s3_service.get_public_url(object_key)
        
        crud.update_recording(
            db,
            recording_id,
            status="processing",
            audio_url=s3_url
        )
        
        # 오디오 길이 추정 (파일 크기 기반)
        from services.audio_metadata import estimate_audio_duration_from_size
        
        # 확장자 추출
        file_ext = request_data.object_key.rsplit('.', 1)[-1] if '.' in request_data.object_key else "webm"
        estimated_duration_sec = estimate_audio_duration_from_size(request_data.file_size, file_ext)
        
        print(f"⏱️  예상 오디오 길이: {estimated_duration_sec / 60:.1f}분")
        
        # Celery 작업 추가 (S3 URL 사용)
        from utils.audio_utils import should_use_parallel_processing
        
        file_size_mb = request_data.file_size / (1024 * 1024)
        use_parallel = should_use_parallel_processing(estimated_duration_sec, file_size_mb)
        
        if use_parallel and estimated_duration_sec >= 1800:
            # 대용량: 병렬 처리
            print(f"🚀 대용량 파일 - 병렬 처리")
            
            from tasks.stt_parallel_tasks import transcribe_orchestrator
            
            task = transcribe_orchestrator.delay(
                recording_id=recording_id,
                audio_url=s3_url,
                duration_sec=int(estimated_duration_sec),
                mode="ko"
            )
        else:
            # 일반: 단일 처리
            print(f"📤 일반 파일 - 단일 처리")
            
            # S3에서 다운로드 후 처리하는 태스크 필요
            from tasks.audio_tasks import process_audio_from_s3
            
            task = process_audio_from_s3.delay(
                recording_id=recording_id,
                s3_object_key=object_key,
                file_ext=file_ext
            )
        
        print(f"✅ Celery 작업 추가: {task.id}")
        
        return {
            "recording_id": recording_id,
            "task_id": task.id,
            "status": "processing",
            "message": "S3 업로드 완료. STT 처리가 시작되었습니다."
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 업로드 완료 처리 실패: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"처리 실패: {str(e)}")


