from fastapi import APIRouter, UploadFile, Form, HTTPException, File, BackgroundTasks, Depends, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from services.assembly_ai_stt import AssemblyAISTTService
from services.audio_processor import AudioProcessor
from services.summarizer import MeetingSummarizer
from services.audio_storage import AudioStorage
from services.text_utils import remove_exact_duplicates, remove_duplicate_sentences
from services.push_notification_service import notify_stt_complete, notify_summary_complete, notify_processing_error
from services.notification_helper import notify_recording_complete, notify_summary_complete as notify_summary_fcm
from typing import Dict, List, Optional
import uuid
from datetime import datetime
import os
import librosa
import soundfile as sf

from database.connection import get_db
from database import crud, task_crud
from models.user import User
from models.recording import Recording


router = APIRouter(prefix="/stt", tags=["STT"])

def get_audio_duration(file_path: str) -> float:
    """
    오디오 파일의 실제 길이를 초 단위로 반환
    """
    try:
        # librosa를 사용하여 오디오 파일의 길이 계산
        duration = librosa.get_duration(path=file_path)
        print(f"🎵 librosa로 계산된 길이: {duration:.2f}초 ({duration/60:.2f}분)")
        return duration
    except Exception as e:
        print(f"❌ librosa 오디오 길이 계산 실패: {e}")
        try:
            # soundfile를 사용한 대안
            info = sf.info(file_path)
            duration = info.duration
            print(f"🎵 soundfile로 계산된 길이: {duration:.2f}초 ({duration/60:.2f}분)")
            return duration
        except Exception as e2:
            print(f"❌ soundfile로도 길이 계산 실패: {e2}")
            try:
                # pydub를 사용한 대안
                from pydub import AudioSegment
                audio = AudioSegment.from_file(file_path)
                duration = len(audio) / 1000.0  # 밀리초를 초로 변환
                print(f"🎵 pydub로 계산된 길이: {duration:.2f}초 ({duration/60:.2f}분)")
                return duration
            except Exception as e3:
                print(f"❌ pydub로도 길이 계산 실패: {e3}")
                return 0.0

# 서비스 초기화 (Lazy - 필요할 때 생성)
_stt_service = None
_audio_processor = None
_summarizer = None
_audio_storage = None


def get_stt_service():
    """STT 서비스 (Lazy initialization)"""
    global _stt_service
    if _stt_service is None:
        _stt_service = AssemblyAISTTService()
    return _stt_service


def get_audio_processor():
    """오디오 프로세서 (Lazy initialization)"""
    global _audio_processor
    if _audio_processor is None:
        _audio_processor = AudioProcessor()
    return _audio_processor


def get_summarizer():
    """요약기 (Lazy initialization)"""
    global _summarizer
    if _summarizer is None:
        _summarizer = MeetingSummarizer()
    return _summarizer


def get_audio_storage():
    """오디오 저장 서비스 (Lazy initialization)"""
    global _audio_storage
    if _audio_storage is None:
        _audio_storage = AudioStorage()
    return _audio_storage


class CommitRequest(BaseModel):
    recordingId: str


@router.post("/start")
async def start_recording(
    title: str = None, 
    request: Request = None,
    db: Session = Depends(get_db)
) -> dict:
    """
    새 녹음 세션 시작
    
    Args:
        title: 녹음 제목 (선택)
        db: 데이터베이스 세션
        
    Returns:
        {
            "recordingId": "uuid",
            "message": "Recording started"
        }
    """
    # 토큰에서 user_id 추출
    user_id = None
    try:
        from services.jwt_service import JWTService
        jwt_service = JWTService()
        
        authorization = request.headers.get("Authorization") if request else None
        if authorization:
            token = authorization.replace("Bearer ", "")
            user_id = jwt_service.get_user_id_from_token(token)
            print(f"🔐 인증된 사용자: user_id={user_id}")
    except Exception as e:
        print(f"⚠️  토큰 추출 실패 (비로그인 허용): {e}")
    
    # MySQL에 녹음 생성 (user_id 포함)
    recording = crud.create_recording(db, title=title, user_id=user_id)
    
    return {
        "recordingId": recording.id if hasattr(recording, 'id') else getattr(recording, 'id', ''),
        "message": "Recording started"
    }


@router.post("/chunk")
async def upload_chunk(
    recordingId: str = Form(...),
    seq: int = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
) -> dict:
    """
    2초 세그먼트 업로드 및 STT 변환
    
    Args:
        recordingId: 녹음 세션 ID
        seq: 세그먼트 순서 (0부터 시작)
        file: 오디오 파일 (M4A)
        db: 데이터베이스 세션
        
    Returns:
        {
            "recordingId": "uuid",
            "seq": 0,
            "text": "변환된 텍스트",
            "lang": "ko-KR",
            "confidence": 0.95,
            "startMs": 0,
            "endMs": 2000
        }
    """
    # 녹음 세션 확인
    recording = crud.get_recording(db, recordingId)
    if not recording:
        raise HTTPException(status_code=404, detail="Recording not found")
    
    try:
        # 파일 읽기
        m4a_content = await file.read()
        
        # 🎵 오디오 파일 로컬 저장
        local_path = await get_audio_storage().save_chunk(recordingId, seq, m4a_content)
        
        # 🎯 WAV LINEAR16 16kHz mono로 변환 (표준화)
        print(f"Converting audio segment {seq} to WAV LINEAR16...")
        wav_content = get_audio_processor().convert_to_wav_linear16(m4a_content, input_format="m4a")
        
        # 🎤 Google STT 호출 비활성화 (비용 절감)
        # 실시간 녹음 시에는 STT를 하지 않고, 녹음 완료 후 전체 파일만 한 번 STT 처리
        print(f"⚠️  청크 STT 비활성화됨 (비용 절감) - segment {seq}")
        
        # 더미 결과 생성 (STT 없이)
        result = {
            "text": f"[청크 {seq} - STT 비활성화됨]",
            "language": "ko-KR",
            "confidence": 0.0,
            "speakers": []
        }
        
        # 🎯 청크별로는 전체 텍스트만 저장 (15초 단위)
        # 화자별 세그먼트는 /commit에서 전체 녹음에 대해 한 번만 생성
        segment = crud.create_segment(
            db=db,
            recording_id=recordingId,
            seq=seq,
            text=result["text"],
            lang=result["language"],
            confidence=result["confidence"],
            start_ms=seq * 15000,
            end_ms=(seq + 1) * 15000,
            audio_url=f"/stt/audio/{recordingId}/chunk_{seq}.m4a",
            speakers=[]  # 🎯 청크에서는 화자 정보 저장 안함 (/commit에서만 저장)
        )
        
        print(f"Segment {seq} processed: {result['text'][:50]}...")
        
        return {
            "recordingId": recordingId,
            "seq": seq,
            "text": result["text"],
            "lang": result["language"],
            "confidence": result["confidence"],
            "startMs": seq * 15000,
            "endMs": (seq + 1) * 15000,
            "speakers": result.get("speakers", []),
        }
    
    except Exception as e:
        print(f"Error processing chunk {seq}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/commit")
async def commit_recording(
    request: CommitRequest, 
    db: Session = Depends(get_db)
) -> dict:
    """
    녹음 세션 종료 및 Celery 워커로 후처리 시작
    
    Args:
        request: {"recordingId": "uuid"}
        db: 데이터베이스 세션
        
    Returns:
        {
            "recordingId": "uuid",
            "status": "processing",
            "message": "처리 중..."
        }
    """
    recordingId = request.recordingId
    
    # MySQL에서 녹음 조회
    recording = crud.get_recording(db, recordingId)
    if not recording:
        raise HTTPException(status_code=404, detail="Recording not found")
    
    # 🔒 중복 STT 방지 가드
    if recording.status in ["processing", "stt_started"]:
        print(f"⚠️  이미 처리 중인 녹음: {recordingId} (status: {recording.status})")
        return {
            "recordingId": recordingId,
            "status": "already_processing",
            "message": "이미 처리 중입니다. 잠시 후 다시 시도해주세요."
        }
    
    # 세그먼트에서 전체 텍스트 합본
    segments = crud.get_segments(db, recordingId)
    if not segments:
        raise HTTPException(status_code=400, detail="No segments found")
    
    # 🔧 중복 제거하여 텍스트 합본
    segments_text = [seg.text for seg in segments]
    cleaned_segments_text = remove_exact_duplicates(segments_text)
    transcript = " ".join(cleaned_segments_text)
    
    # 🔧 문장 단위 중복 제거
    transcript = remove_duplicate_sentences(transcript)
    
    # 언어 자동 감지 (가장 많이 나온 언어)
    languages = [seg.lang for seg in segments]
    lang_auto = max(set(languages), key=languages.count) if languages else "ko-KR"
    
    # 청크 개수
    chunk_count = len(segments)
    
    # 🎯 실제 오디오 파일 길이 계산 (librosa/soundfile 사용)
    actual_duration_ms = 0
    try:
        # 최종 오디오 파일이 있는 경우 해당 파일의 길이 사용
        recording_folder = f"storage/audio/{recordingId}"
        final_audio_path = os.path.join(recording_folder, "final_audio.wav")
        
        print(f"🔍 오디오 파일 경로 확인: {final_audio_path}")
        print(f"🔍 파일 존재 여부: {os.path.exists(final_audio_path)}")
        
        if os.path.exists(final_audio_path):
            duration_seconds = get_audio_duration(final_audio_path)
            if duration_seconds > 0:
                actual_duration_ms = int(duration_seconds * 1000)
                print(f"🎵 최종 오디오 파일 길이: {duration_seconds:.1f}초 ({actual_duration_ms / 60000:.1f}분)")
                
                # 추가 검증: segments의 end_ms와 비교
                segments_max_end = max([seg.end_ms for seg in segments]) if segments else 0
                print(f"🔍 segments 최대 end_ms: {segments_max_end}ms ({segments_max_end/60000:.1f}분)")
                
                # segments와 실제 파일 길이 차이가 크면 경고
                if segments_max_end > 0:
                    diff_percent = abs(actual_duration_ms - segments_max_end) / max(actual_duration_ms, segments_max_end) * 100
                    if diff_percent > 20:  # 20% 이상 차이
                        print(f"⚠️  오디오 길이 차이 발견: 파일={actual_duration_ms}ms, segments={segments_max_end}ms (차이: {diff_percent:.1f}%)")
                        # 실제 파일 길이를 우선 사용
                        print(f"✅ 실제 파일 길이 사용: {actual_duration_ms}ms")
                    else:
                        print(f"✅ 오디오 길이 일치: 차이 {diff_percent:.1f}%")
            else:
                print("⚠️  오디오 길이 계산 결과가 0초")
                # 최종 파일이 있지만 길이를 읽을 수 없는 경우, 청크 파일들로 재계산 시도
                print("🔄 청크 파일들로 재계산 시도...")
                audio_dir = f"storage/audio/{recordingId}"
                if os.path.exists(audio_dir):
                    from pydub import AudioSegment
                    chunk_files = sorted([f for f in os.listdir(audio_dir) if f.startswith("chunk_") and f.endswith(".m4a")])
                    if chunk_files:
                        total_chunk_duration = 0
                        for chunk_file in chunk_files:
                            chunk_path = os.path.join(audio_dir, chunk_file)
                            try:
                                chunk_audio = AudioSegment.from_file(chunk_path)
                                total_chunk_duration += len(chunk_audio)
                            except Exception as e:
                                print(f"⚠️  청크 파일 읽기 실패: {chunk_file} - {e}")
                        
                        if total_chunk_duration > 0:
                            actual_duration_ms = total_chunk_duration
                            print(f"🎵 청크 파일들로 재계산된 길이: {actual_duration_ms / 1000:.1f}초 ({actual_duration_ms / 60000:.1f}분)")
        else:
            # 최종 파일이 없는 경우 청크 파일들을 합쳐서 계산
            audio_dir = f"storage/audio/{recordingId}"
            if os.path.exists(audio_dir):
                from pydub import AudioSegment
                
                # 모든 청크 파일 찾기
                chunk_files = sorted([f for f in os.listdir(audio_dir) if f.startswith("chunk_") and f.endswith(".m4a")])
                print(f"🔍 발견된 청크 파일 수: {len(chunk_files)}")
                
                if chunk_files:
                    # 모든 청크를 병합하여 총 길이 계산
                    combined_audio = None
                    total_duration = 0
                    
                    for chunk_file in chunk_files:
                        chunk_path = os.path.join(audio_dir, chunk_file)
                        try:
                            chunk_audio = AudioSegment.from_file(chunk_path)
                            chunk_duration = len(chunk_audio)
                            total_duration += chunk_duration
                            print(f"🔍 청크 {chunk_file}: {chunk_duration}ms ({chunk_duration/1000:.1f}초)")
                            
                            if combined_audio is None:
                                combined_audio = chunk_audio
                            else:
                                combined_audio += chunk_audio
                        except Exception as e:
                            print(f"⚠️  청크 파일 읽기 실패: {chunk_file} - {e}")
                    
                    if combined_audio:
                        actual_duration_ms = len(combined_audio)
                        print(f"🎵 청크 합친 오디오 길이: {actual_duration_ms / 1000:.1f}초 ({actual_duration_ms / 60000:.1f}분)")
                        print(f"🔍 개별 청크 합계: {total_duration / 1000:.1f}초 ({total_duration / 60000:.1f}분)")
                        
                        # 개별 청크 합계와 병합된 길이 비교
                        if abs(actual_duration_ms - total_duration) > 1000:  # 1초 이상 차이
                            print(f"⚠️  청크 길이 불일치: 병합={actual_duration_ms}ms, 합계={total_duration}ms")
                            # 더 정확한 값 사용
                            actual_duration_ms = max(actual_duration_ms, total_duration)
                            print(f"✅ 최대값 사용: {actual_duration_ms}ms ({actual_duration_ms/60000:.1f}분)")
        
        # 길이를 구하지 못한 경우 segments의 end_ms 사용
        if actual_duration_ms == 0:
            segments_max_end = max([seg.end_ms for seg in segments]) if segments else 0
            actual_duration_ms = segments_max_end
            print(f"⚠️  오디오 파일 읽기 실패, segments의 end_ms 사용: {actual_duration_ms}ms ({actual_duration_ms/60000:.1f}분)")
        else:
            # 실제 파일 길이를 찾았으므로 segments와 비교하여 검증
            segments_max_end = max([seg.end_ms for seg in segments]) if segments else 0
            if segments_max_end > 0:
                diff_percent = abs(actual_duration_ms - segments_max_end) / max(actual_duration_ms, segments_max_end) * 100
                if diff_percent > 10:  # 10% 이상 차이
                    print(f"🔍 실제 파일 vs segments 비교: 파일={actual_duration_ms}ms, segments={segments_max_end}ms (차이: {diff_percent:.1f}%)")
                    print(f"✅ 실제 파일 길이 우선 사용: {actual_duration_ms}ms ({actual_duration_ms/60000:.1f}분)")
                else:
                    print(f"✅ 오디오 길이 일치: 차이 {diff_percent:.1f}%")
    except Exception as e:
        print(f"⚠️  오디오 길이 계산 실패: {e}")
        segments_max_end = max([seg.end_ms for seg in segments]) if segments else 0
        actual_duration_ms = segments_max_end
    
    # 상태 업데이트 (처리 중) - STT 시작 표시
    crud.update_recording(
        db,
        recordingId,
        status="stt_started",  # STT 시작 상태로 변경
                transcript=transcript,
        duration=actual_duration_ms,  # 🎯 실제 오디오 파일 길이 (ms)
        lang_auto=lang_auto,
        audio_url=get_audio_storage().get_public_url(recordingId)
    )
    
    # 🚀 Celery 워커로 백그라운드 처리 시작
    from tasks.audio_tasks import process_hybrid_recording
    
    try:
        task = process_hybrid_recording.delay(recordingId)
        print(f"🚀 [Celery] 하이브리드 녹음 처리 태스크 시작: {task.id}")
        print(f"   Recording ID: {recordingId}")
        print(f"   청크 개수: {chunk_count}")
        
        return {
            "recordingId": recordingId,
            "status": "processing",
            "message": "처리 중... (백그라운드)",
            "task_id": task.id
        }
    except Exception as e:
        print(f"❌ Celery 태스크 시작 실패: {e}")
        # 실패 시 상태 롤백
        crud.update_recording(db, recordingId, status="failed")
        raise HTTPException(status_code=500, detail=f"백그라운드 처리 시작 실패: {str(e)}")


# ==================== 기존 백그라운드 함수 삭제 (Celery로 이동) ====================
# generate_summary_background 함수는 tasks/audio_tasks.py의 process_hybrid_recording으로 이동됨


@router.delete("/recordings/{recording_id}/cancel")
async def cancel_recording(
    recording_id: str,
    db: Session = Depends(get_db)
) -> dict:
    """
    녹음 처리 취소 및 정리
    - Celery 태스크 취소
    - DB 상태 업데이트
    - 오디오 파일 삭제
    
    Args:
        recording_id: 취소할 녹음 ID
        
    Returns:
        {
            "recordingId": str,
            "status": "cancelled"
        }
    """
    try:
        # 녹음 조회
        recording = crud.get_recording(db, recording_id)
        if not recording:
            raise HTTPException(status_code=404, detail="Recording not found")
        
        # 이미 완료된 녹음은 취소 불가
        if recording.status == "ready":
            raise HTTPException(status_code=400, detail="Cannot cancel completed recording")
        
        # Celery 태스크 취소 시도
        from celery_app import celery_app
        from celery.result import AsyncResult
        
        # 해당 녹음의 활성 태스크 찾기 (task_id 저장하지 않았으므로 모든 활성 태스크 확인)
        try:
            # Redis에서 활성 태스크 확인
            import redis
            redis_client = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))
            
            # stt 큐의 모든 태스크 확인
            tasks_in_queue = redis_client.lrange('stt', 0, -1)
            
            cancelled_tasks = 0
            for task_data in tasks_in_queue:
                try:
                    import json
                    task_dict = json.loads(task_data)
                    
                    # 태스크 내용에 recording_id가 포함되어 있는지 확인
                    if recording_id in str(task_dict):
                        # 태스크 취소
                        task_id = task_dict.get('headers', {}).get('id')
                        if task_id:
                            AsyncResult(task_id, app=celery_app).revoke(terminate=True)
                            cancelled_tasks += 1
                            print(f"   🚫 태스크 취소: {task_id}")
                except:
                    continue
            
            if cancelled_tasks > 0:
                print(f"✅ {cancelled_tasks}개 Celery 태스크 취소")
            else:
                print(f"⚠️  활성 태스크 없음 (이미 완료 또는 실패)")
            
        except Exception as e:
            print(f"⚠️  Celery 태스크 취소 실패: {e}")
        
        # DB 상태 업데이트
        crud.update_recording(db, recording_id, status="cancelled")
        
        # 오디오 파일 삭제
        try:
            import shutil
            audio_dir = f"storage/audio/{recording_id}"
            if os.path.exists(audio_dir):
                shutil.rmtree(audio_dir)
                print(f"   🗑️  오디오 파일 삭제: {audio_dir}")
        except Exception as e:
            print(f"   ⚠️  파일 삭제 실패: {e}")
        
        print(f"✅ 녹음 취소 완료: {recording_id}")
        
        return {
            "recordingId": recording_id,
            "status": "cancelled",
            "message": "녹음이 취소되었습니다"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 녹음 취소 실패: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"취소 실패: {str(e)}")


@router.get("/recordings")
async def list_recordings(
    request: Request,
    db: Session = Depends(get_db),
    tag: Optional[str] = None,
    favorite: Optional[bool] = None
) -> List[dict]:
    """
    녹음 목록 조회 (사용자별, 필터링 지원)
    
    Headers:
        Authorization: Bearer {access_token} (선택)
    
    Query Parameters:
        tag: 태그 이름으로 필터링
        favorite: True이면 즐겨찾기만 조회
    
    Returns:
        녹음 목록 배열 (본인 녹음만)
    """
    # 토큰에서 user_id 추출
    user_id = None
    try:
        from services.jwt_service import JWTService
        jwt_service = JWTService()
        
        authorization = request.headers.get("Authorization")
        if authorization:
            token = authorization.replace("Bearer ", "")
            print(f"🔍 토큰 파싱 시도: {token[:20]}...")
            user_id = jwt_service.get_user_id_from_token(token)
            print(f"🔐 녹음 목록 조회: user_id={user_id}")
        else:
            print(f"⚠️  Authorization 헤더 없음")
    except Exception as e:
        print(f"⚠️  토큰 파싱 실패: {e}")
        import traceback
        traceback.print_exc()
    
    # user_id로 필터링하여 조회
    query = db.query(Recording)
    
    if user_id:
        query = query.filter(Recording.user_id == user_id)
    
    # 즐겨찾기 필터
    if favorite is not None:
        query = query.filter(Recording.is_favorite == favorite)
    
    # 태그 필터
    if tag:
        from models.tag import Tag, recording_tags
        tag_obj = db.query(Tag).filter(Tag.name == tag).first()
        if tag_obj:
            query = query.join(recording_tags).filter(recording_tags.c.tag_id == tag_obj.id)
    
    # 관계를 미리 로드
    from sqlalchemy.orm import joinedload
    query = query.options(
        joinedload(Recording.recording_tags),
        joinedload(Recording.actions)
    )
    
    recordings = query.order_by(Recording.created_at.desc()).limit(100).all()
    print(f"📋 녹음 개수: {len(recordings)}개 (user_id={user_id}, tag={tag}, favorite={favorite})")
    
    # 응답 포맷팅 (목록에서는 segments 제외)
    try:
        return [rec.to_dict(include_segments=False) for rec in recordings]
    except Exception as e:
        print(f"❌ 녹음 목록 포맷팅 실패: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="녹음 목록 조회 실패")


@router.post("/recordings/{recording_id}/summarize")
async def summarize_recording(
    recording_id: str, 
    request: Request,
    db: Session = Depends(get_db)
) -> dict:
    """
    기존 녹음에 대해 AI 요약 생성
    
    Args:
        recording_id: 녹음 ID
        request: 요청 객체 (사용자 날짜/시간 정보 포함)
        db: 데이터베이스 세션
        
    Returns:
        요약 생성 결과
    """
    # 사용자 날짜/시간 정보 추출
    try:
        body = await request.json()
        user_date = body.get("userDate")  # YYYY-MM-DD
        user_time = body.get("userTime")  # HH:MM:SS
        user_timezone = body.get("userTimezone")  # Asia/Seoul
        
        print(f"📅 사용자 기기 날짜: {user_date} {user_time} ({user_timezone})")
    except:
        user_date = None
        user_time = None
        user_timezone = None
    
    # MySQL에서 녹음 조회
    recording = crud.get_recording(db, recording_id)
    if not recording:
        raise HTTPException(status_code=404, detail="Recording not found")
    
    # 이미 요약이 있는 경우
    if recording.summary:
        decisions = [d.decision for d in crud.get_decisions(db, recording_id)]
        actions = [a.to_dict() for a in crud.get_actions(db, recording_id)]
        
        return {
            "recordingId": recording_id,
            "status": "already_summarized",
            "message": "이미 요약이 생성되어 있습니다.",
            "summary": recording.summary,
            "decisions": decisions,
            "actions": actions
        }
    
    # 텍스트가 없는 경우
    if not recording.transcript:
        raise HTTPException(status_code=400, detail="No transcript available for summarization")
    
    try:
        # AI 요약 실행 (2단계 프로세스)
        transcript = recording.transcript
        
        # 1단계: AI가 제목 생성
        ai_generated_title = await get_summarizer().generate_meeting_title_from_content(transcript)
        
        # 2단계: 생성된 제목으로 요약 생성 (사용자 날짜 전달)
        result = await get_summarizer().summarize_and_extract(
            transcript, 
            ai_generated_title,
            user_date=user_date
        )
        
        # meeting 정보 추출
        meeting_info = result.get("meeting", {})
        
        # MySQL에 결과 저장
        crud.update_recording(
            db,
            recording_id,
            title=ai_generated_title,
            summary=result["summary"],
            participants=meeting_info.get("participants", []),
            tags=meeting_info.get("tags", []),
            meeting_status=meeting_info.get("status", "완료"),
            questions_answers=result.get("questions_answers", []),
            open_issues=result.get("open_issues", []),
            key_insights=result.get("key_insights", [])
        )
        
        # 의사결정 저장
        crud.create_decisions(db, recording_id, result["decisions"])
        
        # 액션 아이템 저장
        crud.create_actions(db, recording_id, result["actions"])
        
        print(f"✅ Recording {recording_id} summarized successfully")
        
        return {
            "recordingId": recording_id,
            "status": "success",
            "message": "요약이 성공적으로 생성되었습니다.",
            "summary": result["summary"],
            "decisions": result["decisions"],
            "actions": result["actions"]
        }
        
    except Exception as e:
        print(f"❌ Summarization failed for {recording_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Summarization failed: {str(e)}")


@router.get("/recordings/{recording_id}")
async def get_recording(
    recording_id: str,
    request: Request,
    db: Session = Depends(get_db)
) -> dict:
    """
    녹음 상세 조회 (권한 검증)
    
    Args:
        recording_id: 녹음 ID
    
    Headers:
        Authorization: Bearer {access_token} (선택)
        
    Returns:
        녹음 상세 정보
    """
    # MySQL에서 녹음 조회 (관련 데이터 포함)
    recording_dict = crud.get_recording_with_details(db, recording_id)
    if not recording_dict:
        raise HTTPException(status_code=404, detail="Recording not found")
    
    # 권한 검증: 로그인한 사용자만 자기 녹음 접근 가능
    recording_user_id = recording_dict.get("userId")  # dict 형식
    
    try:
        from services.jwt_service import JWTService
        jwt_service = JWTService()
        
        authorization = request.headers.get("Authorization")
        if authorization:
            token = authorization.replace("Bearer ", "")
            user_id = jwt_service.get_user_id_from_token(token)
            
            # 녹음에 user_id가 있고, 현재 사용자와 다르면 팀 권한 확인
            if recording_user_id is not None and recording_user_id != user_id:
                print(f"🔍 권한 검증: recording_user_id={recording_user_id}, current_user_id={user_id}")
                
                # 팀에 공유된 회의인지 확인
                from routers.teams_api import get_team_meetings_by_recording_id, get_team_members
                team_meetings = get_team_meetings_by_recording_id(db, recording_id)
                print(f"🔍 팀 회의록 조회 결과: {len(team_meetings)}개")
                
                if not team_meetings:
                    # 팀에 공유되지 않은 회의는 소유자만 접근 가능
                    print(f"❌ 팀에 공유되지 않은 회의 - 접근 거부")
                    raise HTTPException(
                        status_code=403, 
                        detail="접근 권한이 없습니다. 본인의 녹음만 조회할 수 있습니다."
                    )
                
                # 팀 멤버인지 확인
                user_has_access = False
                for team_meeting in team_meetings:
                    print(f"🔍 팀 {team_meeting.team_id} 멤버 확인 중...")
                    try:
                        team_members = get_team_members(db, team_meeting.team_id)
                        print(f"🔍 팀 멤버 수: {len(team_members)}")
                        for member in team_members:
                            print(f"🔍 멤버: user_id={member.user_id}, role={member.role}")
                            if member.user_id == user_id:
                                user_has_access = True
                                print(f"✅ 팀 멤버 확인됨 - 접근 허용")
                                break
                        if user_has_access:
                            break
                    except Exception as e:
                        print(f"❌ 팀 멤버 조회 실패: {e}")
                        import traceback
                        traceback.print_exc()
                        break
                
                print(f"🔍 최종 권한 확인: user_has_access={user_has_access}")
                
                if not user_has_access:
                    print(f"❌ 팀 멤버가 아님 - 접근 거부")
                    raise HTTPException(
                        status_code=403, 
                        detail="접근 권한이 없습니다. 팀 멤버만 조회할 수 있습니다."
                    )
    except HTTPException:
        raise
    except Exception as e:
        # 토큰 없으면 user_id가 null인 녹음만 접근 가능
        if recording_user_id is not None:
            raise HTTPException(
                status_code=401,
                detail="로그인이 필요합니다"
            )
    
    return recording_dict


@router.delete("/recordings/{recording_id}")
async def delete_recording(
    recording_id: str,
    request: Request,
    db: Session = Depends(get_db)
) -> dict:
    """
    녹음 삭제 (권한 검증)
    
    Args:
        recording_id: 녹음 ID
    
    Headers:
        Authorization: Bearer {access_token} (필수)
        
    Returns:
        {"message": "Recording deleted"}
    """
    # 녹음 조회 (객체로)
    recording_obj = crud.get_recording(db, recording_id)
    if not recording_obj:
        raise HTTPException(status_code=404, detail="Recording not found")
    
    # 권한 검증
    try:
        from services.jwt_service import JWTService
        jwt_service = JWTService()
        
        authorization = request.headers.get("Authorization")
        if not authorization:
            raise HTTPException(status_code=401, detail="로그인이 필요합니다")
        
        token = authorization.replace("Bearer ", "")
        user_id = jwt_service.get_user_id_from_token(token)
        
        # 본인 녹음만 삭제 가능
        if recording_obj.user_id is not None and recording_obj.user_id != user_id:
            raise HTTPException(
                status_code=403,
                detail="본인의 녹음만 삭제할 수 있습니다"
            )
        
        # user_id가 null인 녹음은 로그인하지 않아도 삭제 가능 (하위 호환)
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"⚠️  권한 검증 실패: {e}")
        if recording_obj.user_id is not None:
            raise HTTPException(status_code=401, detail="로그인이 필요합니다")
    
    # 🗑️ 팀 회의에서 해당 회의록 삭제
    try:
        from models.team_meeting import TeamMeeting
        
        print(f"🔍 팀 회의록 삭제: meeting_id={recording_id}")
        
        # UUID로 직접 조회
        team_meetings = db.query(TeamMeeting).filter(TeamMeeting.meeting_id == recording_id).all()
        if team_meetings:
            for tm in team_meetings:
                db.delete(tm)
                print(f"🗑️  팀 회의에서 삭제: team_id={tm.team_id}, meeting_id={recording_id}")
            db.commit()
            print(f"✅ 팀 회의록 {len(team_meetings)}개 삭제 완료")
        else:
            print(f"ℹ️  팀에 공유되지 않은 회의록입니다")
    except Exception as e:
        print(f"⚠️  팀 회의 삭제 중 오류 (무시): {e}")
        import traceback
        traceback.print_exc()
    
    # MySQL에서 녹음 삭제 (CASCADE로 관련 데이터도 자동 삭제)
    # - segments 테이블
    # - actions 테이블
    # - decisions 테이블
    # - recording_tags 관계
    success = crud.delete_recording(db, recording_id)
    if not success:
        raise HTTPException(status_code=404, detail="Recording not found")
    
    print(f"🗑️  녹음 삭제 완료: {recording_id} (user_id={recording_obj.user_id})")
    return {"message": "Recording deleted", "recording_id": recording_id}


# 🧪 테스트용 엔드포인트
@router.post("/test/add-transcript")
async def add_test_transcript(
    recordingId: str = Form(...),
    transcript: str = Form(...),
    db: Session = Depends(get_db)
) -> dict:
    """
    테스트용: 녹음에 직접 텍스트 추가
    """
    # MySQL에서 녹음 확인
    recording = crud.get_recording(db, recordingId)
    if not recording:
        raise HTTPException(status_code=404, detail="Recording not found")
    
    # 세그먼트 생성
    segment = crud.create_segment(
        db=db,
        recording_id=recordingId,
        seq=0,
        text=transcript,
        lang="ko-KR",
        confidence=0.95,
        start_ms=0,
        end_ms=10000,
        audio_url=f"/audio/{recordingId}/segment_0.m4a",
        speakers=[]
    )
    
    # 녹음에 transcript 업데이트
    crud.update_recording(db, recordingId, transcript=transcript)
    
    return {
        "message": "Transcript added",
        "recordingId": recordingId,
        "segments": 1
    }


@router.post("/upload", status_code=202)
async def upload_audio_file(
    file: UploadFile = File(...),
    request: Request = None,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db)
) -> dict:
    """
    오디오 파일 업로드 및 자동 요약 생성
    
    Args:
        file: 오디오 파일 (M4A, MP3, WAV 등)
        db: 데이터베이스 세션
        
    Returns:
        {
            "recordingId": "uuid",
            "status": "processing",
            "message": "파일이 업로드되었습니다. AI가 분석 중입니다."
        }
    """
    try:
        # 파일 읽기
        audio_content = await file.read()
        
        # 토큰에서 user_id 추출 (먼저 실행)
        user_id = None
        try:
            from services.jwt_service import JWTService
            jwt_service = JWTService()
            
            authorization = request.headers.get("Authorization") if request else None
            if authorization:
                token = authorization.replace("Bearer ", "")
                user_id = jwt_service.get_user_id_from_token(token)
                print(f"🔐 인증된 사용자: user_id={user_id}")
        except Exception as e:
            print(f"⚠️  토큰 추출 실패 (비로그인 허용): {e}")
        
        # 🎤 음성 품질 개선 적용 (사용자 설정 확인)
        should_enhance = True
        enhancement_options = {
            'noise_reduction': True,
            'amplification': True,
            'normalization': True,
            'auto_correction': True
        }
        
        # 사용자 설정 확인
        if user_id:
            try:
                user = db.query(User).filter(User.id == user_id).first()
                if user and not user.audio_quality_enabled:
                    should_enhance = False
                    print(f"⚙️ 사용자 설정: 음성 품질 개선 비활성화")
                elif user and user.audio_quality_settings:
                    enhancement_options = user.audio_quality_settings
                    print(f"⚙️ 사용자 설정: {enhancement_options}")
            except Exception as e:
                print(f"⚠️ 사용자 설정 확인 실패: {e}")
        
        if should_enhance:
            try:
                from services.audio_enhancement import audio_enhancement_service
                print(f"🎤 음성 품질 개선 시작... (원본 크기: {len(audio_content) / 1024:.1f}KB)")
                
                file_ext = file.filename.rsplit('.', 1)[-1] if file.filename and '.' in file.filename else "m4a"
                
                enhanced_audio = audio_enhancement_service.enhance_audio(
                    audio_content=audio_content,
                    input_format=file_ext,
                    enhancement_options=enhancement_options
                )
                
                print(f"✅ 음성 품질 개선 완료 (개선 크기: {len(enhanced_audio) / 1024:.1f}KB)")
                audio_content = enhanced_audio  # 개선된 오디오로 교체
            except Exception as e:
                print(f"⚠️ 음성 품질 개선 실패, 원본 사용: {e}")
        
        # 파일명에서 제목 추출 (URL 디코딩 + 길이 제한)
        import urllib.parse
        
        raw_title = file.filename.rsplit('.', 1)[0] if file.filename else "업로드된 녹음"
        
        # URL 디코딩
        try:
            decoded_title = urllib.parse.unquote(raw_title)
        except:
            decoded_title = raw_title
        
        # 길이 제한 (100자)
        title = decoded_title[:100] if len(decoded_title) > 100 else decoded_title
        
        print(f"📝 파일명: {file.filename}")
        print(f"✅ 처리된 제목: {title}")
        
        # MySQL에 녹음 생성 (user_id는 이미 위에서 추출됨)
        recording = crud.create_recording(db, title=title, user_id=user_id)
        recording_id = recording.id if hasattr(recording, 'id') else getattr(recording, 'id', '')
        
        # 🎵 오디오 압축 (AssemblyAI 업로드 최적화)
        # file_ext는 이미 839번 줄에서 정의됨
        # 개선된 오디오는 항상 M4A 형식
        save_ext = "m4a"  # 개선된 오디오는 M4A
        
        print(f"📊 파일 크기: {len(audio_content) / 1024 / 1024:.1f}MB")
        
        # 개선된 오디오 파일 로컬 저장 (M4A 형식)
        local_path = await get_audio_storage().save_full_audio(recording_id, audio_content, save_ext)
        print(f"✅ 개선된 오디오 저장: {local_path}")
        
        # 파일이 10MB 이상이면 압축 (Opus 우선, 폴백 MP3)
        compressed_path = None
        stt_file_path = local_path
        stt_file_ext = save_ext  # 개선된 오디오는 M4A
        
        if len(audio_content) > 10 * 1024 * 1024:
            from services.audio_processor import AudioProcessor
            from pathlib import Path
            
            print(f"📦 [업로드 API] 파일 압축 시작... (10MB 초과)")
            
            # Opus 압축 시도 (최고 압축률 80%+)
            try:
                compressed_audio = AudioProcessor.compress_audio_opus(audio_content, file_ext, target_bitrate="24k")
                compressed_ext = "webm"
            except Exception as e:
                print(f"⚠️  Opus 압축 실패, MP3로 폴백: {e}")
                compressed_audio = AudioProcessor.compress_audio(audio_content, file_ext, target_bitrate="32k")
                compressed_ext = "mp3"
            
            # 압축된 파일 저장
            recording_dir = Path(local_path).parent
            compressed_path = str(recording_dir / f"compressed.{compressed_ext}")
            
            with open(compressed_path, 'wb') as f:
                f.write(compressed_audio)
            
            print(f"✅ [업로드 API] 압축 완료: {compressed_path}")
            print(f"📊 [업로드 API] STT 업로드용 파일 크기: {len(compressed_audio) / 1024 / 1024:.1f}MB")
            
            # STT 처리에는 압축 파일 사용
            stt_file_path = compressed_path
            stt_file_ext = compressed_ext
        else:
            print(f"✅ [업로드 API] 10MB 이하 - 압축 건너뛰기, 원본 사용")
        
        # 🎯 오디오 길이 정확히 측정 (librosa/soundfile 사용)
        duration_seconds = get_audio_duration(local_path)
        print(f"🔍 계산된 오디오 길이: {duration_seconds:.2f}초")
        
        if duration_seconds > 0:
            estimated_duration_sec = duration_seconds
            print(f"✅ 실제 오디오 파일 길이 사용: {estimated_duration_sec:.1f}초 ({estimated_duration_sec/60:.1f}분)")
        else:
            # 파일 크기로 추정 (fallback)
            estimated_duration_sec = estimate_audio_duration_from_size(len(audio_content), file_ext)
            print(f"⚠️  오디오 길이 계산 실패, 파일 크기로 추정: {estimated_duration_sec:.1f}초")
        
        estimated_processing_time = max(2, int(estimated_duration_sec / 60))  # 최소 2분
        
        print(f"⏱️  최종 오디오 길이: {estimated_duration_sec / 60:.1f}분 ({estimated_duration_sec:.0f}초)")
        print(f"🕐 예상 처리 시간: {estimated_processing_time}분")
        print(f"🎯 병렬 처리 대상: {'YES (30분 이상)' if estimated_duration_sec >= 1800 else 'NO'}")
        
        # 녹음 초기 상태로 업데이트
        crud.update_recording(
            db,
            recording_id,
            status="processing",
            audio_url=get_audio_storage().get_public_url(recording_id),
            local_audio_path=local_path,
            duration=int(estimated_duration_sec * 1000)  # ms 단위
        )
        
        # 🎯 백그라운드에서 STT + AI 제목 생성 + 요약 생성
        async def process_audio_background():
            """백그라운드에서 STT, AI 제목 생성 및 요약"""
            from database.connection import get_db_context
            import tempfile
            import os as os_module
            
            try:
                print(f"🎤 백그라운드 STT 처리 시작: {recording_id}...")
                
                # 🎯 WAV LINEAR16 16kHz mono로 변환 (파일 경로 사용)
                print(f"🎵 Converting uploaded file to WAV LINEAR16...")
                
                # 임시 파일로 저장 후 변환 (AAC 파일 처리를 위해)
                with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_ext}") as temp_file:
                    with open(local_path, 'rb') as f:
                        temp_file.write(f.read())
                    temp_path = temp_file.name
                
                try:
                    # 파일 경로로 변환 (메모리 대신)
                    wav_content = get_audio_processor().convert_to_wav_linear16_from_file(temp_path)
                finally:
                    # 임시 파일 삭제
                    if os_module.path.exists(temp_path):
                        os_module.unlink(temp_path)
                
                # 🎤 Google STT로 전체 음성을 텍스트로 변환 + 화자 구분
                # (자동 분기: 60초 이상이면 long_running_recognize 사용)
                print(f"🎤 Transcribing uploaded file with speaker diarization...")
                result = await get_stt_service().transcribe_audio(
                    wav_content, 
                    use_wav=True,
                    min_speakers=2,  # 최소 화자 수
                    max_speakers=5   # 최대 화자 수
                )
                
                transcript = result["text"]
                language = result["language"]
                segments = result.get("segments", [])
                speaker_count = result.get("speaker_count", 0)
                speaker_ids = result.get("speaker_ids", [])
                
                print(f"🎤 업로드 파일 화자 구분 결과: {speaker_count}명 (IDs: {speaker_ids})")
                
                # 🎯 화자별 세그먼트 저장
                with get_db_context() as db:
                    if segments:
                        print(f"✅ {len(segments)}개 화자별 세그먼트 저장")
                        for idx, seg in enumerate(segments):
                            crud.create_segment(
                                db=db,
                                recording_id=recording_id,
                                seq=idx,
                                text=seg["text"],
                                lang=language,
                                confidence=seg.get("confidence", 0.0),
                                start_ms=int(seg["start"] * 1000),
                                end_ms=int(seg["end"] * 1000),
                                audio_url=f"/stt/audio/{recording_id}",
                                speaker=seg.get("speaker", 0)
                            )
                    else:
                        # 백업: 세그먼트가 없으면 전체 텍스트로 저장
                        print(f"⚠️  세그먼트 없음 - 전체 텍스트로 저장")
                        crud.create_segment(
                            db=db,
                            recording_id=recording_id,
                            seq=0,
                            text=transcript,
                            lang=language,
                            confidence=result["confidence"],
                            start_ms=0,
                            end_ms=len(transcript) * 100,
                            audio_url=f"/stt/audio/{recording_id}",
                            speaker=0
                        )
                    
                    # 녹음에 transcript 업데이트
                    crud.update_recording(
                        db,
                        recording_id,
                        transcript=transcript,
                        lang_auto=language,
                        duration=len(transcript) * 100,
                    )
                
                print(f"📝 Generating AI title and summary for uploaded file {recording_id}...")
                
                # 1단계: AI가 제목 생성
                ai_title = await get_summarizer().generate_meeting_title_from_content(transcript)
                
                # 2단계: 생성된 제목으로 요약 생성
                summary_result = await get_summarizer().summarize_and_extract(
                    transcript=transcript,
                    meeting_title=ai_title
                )
                
                # MySQL에 결과 저장
                with get_db_context() as db:
                    # meeting 정보 추출
                    meeting_info = summary_result.get("meeting", {})
                    
                    crud.update_recording(
                        db,
                        recording_id,
                        title=ai_title,
                        summary=summary_result["summary"],
                        participants=meeting_info.get("participants", []),
                        tags=meeting_info.get("tags", []),
                        meeting_status=meeting_info.get("status", "완료"),
                        questions_answers=summary_result.get("questions_answers", []),
                        open_issues=summary_result.get("open_issues", []),
                        key_insights=summary_result.get("key_insights", []),
                        status="ready"
                    )
                    
                    crud.create_decisions(db, recording_id, summary_result["decisions"])
                    crud.create_actions(db, recording_id, summary_result["actions"])
                
                print(f"✅ AI summary generated for uploaded file: {ai_title}")
                
            except Exception as e:
                print(f"❌ Summary generation failed for {recording_id}: {e}")
                import traceback
                traceback.print_exc()
                with get_db_context() as db:
                    crud.update_recording(db, recording_id, status="ready")
        
        # 🎯 Celery 작업 큐에 추가
        try:
            from tasks.audio_tasks import process_audio_task
            
            print(f"📤 [업로드 API] Celery 큐에 작업 추가:")
            print(f"   - 파일: {stt_file_path}")
            print(f"   - 형식: {stt_file_ext}")
            print(f"   - 길이: {estimated_duration_sec/60:.1f}분")
            
            task = process_audio_task.delay(recording_id, stt_file_path, stt_file_ext)
            
            # 작업 상태 DB에 기록
            task_crud.create_task(
                db,
                task_id=task.id,
                recording_id=recording_id,
                task_type='stt',
                backend='celery'
            )
            
            print(f"✅ Celery 작업 큐에 추가됨: task_id={task.id}")
            
            # 즉시 응답 (202 Accepted)
            return {
                "recordingId": recording_id,
                "taskId": task.id,
                "status": "processing",
                "message": "파일이 업로드되었습니다. AI가 분석 중입니다. 완료되면 알림을 보내드립니다.",
                "estimatedTime": f"{estimated_processing_time}분",
                "estimatedMinutes": estimated_processing_time,
                "fileDurationSeconds": int(estimated_duration_sec)
            }
            
        except ImportError:
            # Celery 없으면 백그라운드 태스크 사용 (폴백)
            print(f"⚠️  Celery 없음, BackgroundTasks 사용")
            background_tasks.add_task(process_audio_background)
            
            return {
                "recordingId": recording_id,
                "taskId": None,
                "status": "processing",
                "message": "파일이 업로드되었습니다. AI가 분석 중입니다.",
                "estimatedTime": f"{estimated_processing_time}분",
                "estimatedMinutes": estimated_processing_time,
                "fileDurationSeconds": int(estimated_duration_sec)
            }
        
    except Exception as e:
        print(f"❌ Upload failed: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.get("/audio/{recording_id}")
@router.head("/audio/{recording_id}")
async def get_audio_file(recording_id: str, request: Request, db: Session = Depends(get_db)):
    """
    오디오 파일 다운로드/스트리밍 (iOS Range 요청 지원)
    
    Args:
        recording_id: 녹음 ID
        request: HTTP 요청 (Range 헤더 확인용)
        db: 데이터베이스 세션
        
    Returns:
        오디오 파일 (스트리밍 지원)
    """
    from fastapi.responses import StreamingResponse
    import mimetypes
    
    # 녹음 확인
    recording = crud.get_recording(db, recording_id)
    if not recording:
        raise HTTPException(status_code=404, detail="Recording not found")
    
    # 로컬 파일 경로 가져오기
    try:
        file_path = get_audio_storage().get_audio_path(recording_id)
        
        if not os.path.exists(file_path):
            print(f"❌ 파일 없음: {file_path}")
            raise HTTPException(status_code=404, detail="Audio file not found")
        
        # 파일 정보
        file_size = os.path.getsize(file_path)
        file_ext = file_path.rsplit('.', 1)[-1].lower()
        
        print(f"🎵 오디오 파일 정보:")
        print(f"   파일 경로: {file_path}")
        print(f"   파일 크기: {file_size} bytes")
        print(f"   파일 확장자: {file_ext}")
        print(f"   파일 존재: {os.path.exists(file_path)}")
        
        # MIME 타입 결정
        mime_types_map = {
            "m4a": "audio/mp4",
            "aac": "audio/aac", 
            "mp3": "audio/mpeg",
            "wav": "audio/wav",
            "ogg": "audio/ogg",
            "webm": "audio/webm"
        }
        media_type = mime_types_map.get(file_ext, "audio/mp4")
        
        # HEAD 요청 처리 (파일 존재 여부만 확인)
        if request.method == "HEAD":
            from fastapi.responses import Response
            return Response(
                status_code=200,
                headers={
                    "Content-Type": media_type,
                    "Content-Length": str(file_size),
                    "Accept-Ranges": "bytes"
                }
            )
        
        # Range 요청 처리 (iOS 스트리밍 필수)
        range_header = request.headers.get("range")
        
        if range_header:
            # Range 요청 파싱
            range_match = range_header.replace("bytes=", "").split("-")
            start = int(range_match[0]) if range_match[0] else 0
            end = int(range_match[1]) if len(range_match) > 1 and range_match[1] else file_size - 1
            
            # 범위 검증
            if start >= file_size or end >= file_size:
                raise HTTPException(status_code=416, detail="Range not satisfiable")
            
            chunk_size = end - start + 1
            
            def iterfile():
                with open(file_path, "rb") as f:
                    f.seek(start)
                    remaining = chunk_size
                    while remaining > 0:
                        read_size = min(8192, remaining)
                        data = f.read(read_size)
                        if not data:
                            break
                        remaining -= len(data)
                        yield data
            
            headers = {
                "Content-Range": f"bytes {start}-{end}/{file_size}",
                "Accept-Ranges": "bytes",
                "Content-Length": str(chunk_size),
            }
            
            return StreamingResponse(
                iterfile(),
                media_type=media_type,
                status_code=206,
                headers=headers
            )
        else:
            # 전체 파일 응답
            return FileResponse(
                path=file_path,
                media_type=media_type,
                filename=f"{recording.title}.{file_ext}",
                headers={"Accept-Ranges": "bytes"}
            )
    
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Audio file not found")
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Audio file retrieval failed: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to retrieve audio: {str(e)}")


@router.get("/audio/{recording_id}/chunk_{seq}.m4a")
async def get_audio_chunk(recording_id: str, seq: int):
    """
    개별 청크 파일 다운로드
    
    Args:
        recording_id: 녹음 ID
        seq: 청크 순서
        
    Returns:
        청크 오디오 파일
    """
    recording_dir = get_audio_storage().get_recording_dir(recording_id)
    chunk_path = recording_dir / f"chunk_{seq:04d}.m4a"
    
    if not chunk_path.exists():
        raise HTTPException(status_code=404, detail="Chunk file not found")
    
    return FileResponse(
        path=str(chunk_path),
        media_type="audio/mp4",
        filename=f"chunk_{seq}.m4a"
    )


# ==================== 작업 상태 조회 ====================

@router.get("/tasks/{task_id}")
async def get_task_status(task_id: str, db: Session = Depends(get_db)):
    """
    작업 상태 조회 (Celery 또는 SQS)
    
    Args:
        task_id: 작업 ID (Celery task.id 또는 SQS MessageId)
    
    Returns:
        {
            "taskId": str,
            "recordingId": str,
            "status": "pending|processing|completed|failed",
            "progress": int,
            "currentStep": str,
            "backend": "celery|sqs"
        }
    """
    try:
        # DB에서 작업 조회
        task = task_crud.get_task(db, task_id)
        
        if not task:
            # Celery에서 직접 조회 시도
            try:
                from celery_app import celery_app
                celery_task = celery_app.AsyncResult(task_id)
                
                # Celery 상태를 표준 상태로 매핑
                status_mapping = {
                    'PENDING': 'pending',
                    'STARTED': 'processing',
                    'PROGRESS': 'processing',
                    'SUCCESS': 'completed',
                    'FAILURE': 'failed',
                    'RETRY': 'processing',
                }
                
                return {
                    "taskId": task_id,
                    "status": status_mapping.get(celery_task.state, 'unknown'),
                    "backend": "celery",
                    "celeryState": celery_task.state,
                    "result": celery_task.result if celery_task.ready() else None
                }
            except ImportError:
                raise HTTPException(status_code=404, detail="Task not found")
        
        return {
            "taskId": task["id"],
            "recordingId": task["recording_id"],
            "taskType": task["task_type"],
            "status": task["status"],
            "progress": task["progress"],
            "currentStep": task["current_step"],
            "backend": task["backend"],
            "createdAt": task["created_at"],
            "startedAt": task["started_at"],
            "completedAt": task["completed_at"],
            "errorMessage": task["error_message"],
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 작업 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"작업 조회 실패: {str(e)}")


@router.get("/recordings/{recording_id}/tasks")
async def get_recording_tasks(recording_id: str, db: Session = Depends(get_db)):
    """
    녹음 관련 모든 작업 조회
    """
    tasks = task_crud.get_recording_tasks(db, recording_id)
    return {"recordingId": recording_id, "tasks": tasks}


class UpdateActionItemRequest(BaseModel):
    action_index: int
    completed: bool


@router.patch("/recordings/{recording_id}/actions")
async def update_action_item(
    recording_id: str,
    request: UpdateActionItemRequest,
    auth_request: Request,
    db: Session = Depends(get_db)
) -> dict:
    """
    액션 아이템 완료 상태 업데이트
    
    Args:
        recording_id: 녹음 ID
        request: {"action_index": 0, "completed": true}
        
    Headers:
        Authorization: Bearer {access_token} (필수)
        
    Returns:
        {"message": "Action item updated", "actions": [...]}
    """
    import json
    
    # 녹음 조회
    recording = crud.get_recording(db, recording_id)
    if not recording:
        raise HTTPException(status_code=404, detail="Recording not found")
    
    # 권한 검증
    try:
        from services.jwt_service import JWTService
        jwt_service = JWTService()
        
        authorization = auth_request.headers.get("Authorization")
        if not authorization:
            raise HTTPException(status_code=401, detail="로그인이 필요합니다")
        
        token = authorization.replace("Bearer ", "")
        user_id = jwt_service.get_user_id_from_token(token)
        
        # 본인 녹음만 수정 가능
        if recording.user_id is not None and recording.user_id != user_id:
            raise HTTPException(
                status_code=403,
                detail="본인의 녹음만 수정할 수 있습니다"
            )
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 토큰 검증 실패: {e}")
        raise HTTPException(status_code=401, detail="유효하지 않은 토큰입니다")
    
    # 액션 아이템 업데이트
    if not recording.actions:
        raise HTTPException(status_code=404, detail="No action items found")
    
    try:
        # 액션 리스트 가져오기 (SQLAlchemy relationship)
        actions_list = recording.actions
        
        print(f"🔍 액션 리스트 타입: {type(actions_list)}, 길이: {len(actions_list)}")
        
        # 인덱스 검증
        if request.action_index < 0 or request.action_index >= len(actions_list):
            raise HTTPException(status_code=400, detail="Invalid action index")
        
        # action_order로 정렬하여 올바른 순서 유지
        sorted_actions = sorted(actions_list, key=lambda x: x.action_order)
        
        # 해당 인덱스의 액션 가져오기
        target_action = sorted_actions[request.action_index]
        
        print(f"🔍 대상 액션: id={target_action.id}, task={target_action.task}, 현재 completed={target_action.completed}")
        
        # 완료 상태 업데이트
        target_action.completed = request.completed
        
        # 데이터베이스 커밋
        db.commit()
        db.refresh(target_action)
        
        print(f"✅ 액션 아이템 업데이트 완료: recording_id={recording_id}, action_id={target_action.id}, index={request.action_index}, completed={request.completed}")
        
        # 응답용 액션 리스트 생성
        response_actions = [
            {
                'task': action.task,
                'priority': action.priority,
                'due': action.due_date.isoformat() if action.due_date else None,
                'owner': action.owner,
                'completed': action.completed
            }
            for action in sorted_actions
        ]
        
        return {
            "message": "Action item updated",
            "actions": response_actions
        }
        
    except Exception as e:
        db.rollback()
        print(f"❌ 액션 아이템 업데이트 실패: {e}")
        print(f"❌ 오류 타입: {type(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to update action item: {str(e)}")


class UpdateTagsRequest(BaseModel):
    tags: list[str]


@router.put("/recordings/{recording_id}/tags")
async def update_recording_tags(
    recording_id: str,
    request: UpdateTagsRequest,
    auth_request: Request,
    db: Session = Depends(get_db)
) -> dict:
    """
    회의록 태그 업데이트
    
    Args:
        recording_id: 회의록 ID
        request: 업데이트할 태그 목록
        
    Returns:
        {"message": "Tags updated", "tags": [...]}
    """
    import json
    
    # 녹음 조회
    recording = crud.get_recording(db, recording_id)
    if not recording:
        raise HTTPException(status_code=404, detail="Recording not found")
    
    # 권한 검증
    try:
        from services.jwt_service import JWTService
        jwt_service = JWTService()
        
        authorization = auth_request.headers.get("Authorization")
        if not authorization:
            raise HTTPException(status_code=401, detail="로그인이 필요합니다")
        
        token = authorization.replace("Bearer ", "")
        user_id = jwt_service.get_user_id_from_token(token)
        
        # 본인 녹음만 수정 가능
        if recording.user_id is not None and recording.user_id != user_id:
            raise HTTPException(
                status_code=403,
                detail="본인의 회의록만 수정할 수 있습니다"
            )
    except Exception as e:
        print(f"❌ 권한 검증 실패: {e}")
        raise HTTPException(status_code=401, detail="권한 검증 실패")
    
    try:
        # 기존 태그 관계 삭제
        from models.tag import recording_tags
        db.execute(recording_tags.delete().where(recording_tags.c.recording_id == recording_id))
        
        # 새 태그들 처리
        tag_objects = []
        for tag_name in request.tags:
            if not tag_name.strip():
                continue
                
            # 태그가 이미 존재하는지 확인
            from models.tag import Tag
            existing_tag = db.query(Tag).filter(Tag.name == tag_name.strip()).first()
            
            if existing_tag:
                tag_objects.append(existing_tag)
                # 사용 횟수 증가
                existing_tag.usage_count += 1
            else:
                # 새 태그 생성
                new_tag = Tag(
                    name=tag_name.strip(),
                    color=None,  # 기본 색상
                    usage_count=1,
                    created_by=user_id
                )
                db.add(new_tag)
                db.flush()  # ID 생성
                tag_objects.append(new_tag)
        
        # 새로운 태그를 JSON 형태로 저장
        import json
        tags_json = json.dumps([{"name": tag.name, "color": tag.color} for tag in tag_objects], ensure_ascii=False)
        
        # recording_tags에 JSON 데이터 저장 (개인 회의용)
        if tag_objects:
            db.execute(recording_tags.insert().values(
                recording_id=recording_id,
                tag_id=tag_objects[0].id,
                tags=tags_json
            ))
        
        db.commit()
        
        print(f"✅ 태그 업데이트 완료: {recording_id} - {len(request.tags)}개 태그")
        
        return {
            "message": "Tags updated successfully",
            "tags": [{"id": tag.id, "name": tag.name, "color": tag.color} for tag in tag_objects]
        }
        
    except Exception as e:
        db.rollback()
        print(f"❌ 태그 업데이트 실패: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to update tags: {str(e)}")

