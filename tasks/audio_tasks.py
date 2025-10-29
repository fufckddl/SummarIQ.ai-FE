"""
오디오 처리 백그라운드 작업
Celery 워커에서 실행됨 (FastAPI 서버와 분리)
"""
from celery_app import celery_app
from sqlalchemy.orm import Session
import os
import tempfile
import asyncio

# 워커에서 실행되므로 직접 import
from services.assembly_ai_stt import AssemblyAISTTService
from services.audio_processor import AudioProcessor
from services.summarizer import MeetingSummarizer
from database.connection import get_db_context
from database import crud

# ⚠️ 모든 모델 명시적으로 임포트 (SQLAlchemy relationship 해결)
from models.recording import Recording
from models.segment import Segment
from models.user import User
from models.subscription import Subscription
from models.team import Team, TeamMember
from models.tag import Tag
from models.action import Action
from models.decision import Decision


@celery_app.task(
    name='tasks.audio_tasks.process_audio_task',
    bind=True,
    max_retries=3,
    default_retry_delay=60  # 실패 시 60초 후 재시도
)
def process_audio_task(self, recording_id: str, local_path: str, file_ext: str):
    """
    오디오 파일 STT + 요약 처리 (워커 전용)
    
    Args:
        recording_id: 녹음 ID
        local_path: 로컬 오디오 파일 경로
        file_ext: 파일 확장자
    
    Returns:
        {
            "recording_id": str,
            "status": "completed",
            "title": str,
            "transcript": str
        }
    """
    try:
        print(f"🎤 [Celery Worker] STT 처리 시작: {recording_id}")
        print(f"   파일: {local_path}")
        
        # 서비스 초기화
        stt_service = AssemblyAISTTService()
        audio_processor = AudioProcessor()
        summarizer = MeetingSummarizer()
        
        # 0️⃣ FK 가드: recording 존재 확인 (없으면 재시도)
        try:
            with get_db_context() as db:
                rec = crud.get_recording(db, recording_id)
                if not rec:
                    print(f"⚠️  recording 미존재로 재시도: {recording_id}")
                    raise self.retry(exc=Exception("recording not found"), countdown=30)
        except Exception:
            # retry가 raise되면 여기서 종료됨
            raise
        
        # 1️⃣ 오디오 파일 읽기 (이미 백엔드에서 압축된 파일)
        print(f"📁 [Celery] STT용 파일 로드: {local_path}")
        print(f"   형식: {file_ext}")
        
        with open(local_path, 'rb') as f:
            audio_content = f.read()
        
        file_size_mb = len(audio_content) / (1024 * 1024)
        print(f"📊 [Celery] 로드된 파일 크기: {file_size_mb:.1f}MB (AssemblyAI 업로드용)")
        
        # 2️⃣ AssemblyAI STT 호출 (압축된 파일 직접 전송)
        print(f"🎤 Transcribing with speaker diarization...")
        print(f"🎤 Assembly AI STT 시작 (Celery Worker) ...")
        
        # 작업 진행률 업데이트 (Celery 기능)
        self.update_state(state='PROGRESS', meta={'step': 'stt', 'progress': 30})
        
        # Assembly AI는 비동기이므로 동기 래퍼 사용
        # WAV 변환하지 않고 압축된 MP3 직접 전송 (AssemblyAI가 자동 처리)
        result = asyncio.run(stt_service.transcribe_audio(
            audio_content, 
            use_wav=False,  # WAV 변환 건너뛰기
            min_speakers=2,
            max_speakers=5
        ))
        
        transcript = result["text"]
        language = result["language"]
        segments = result.get("segments", [])
        speaker_count = result.get("speaker_count", 0)
        speaker_ids = result.get("speaker_ids", [])
        
        print(f"✅ STT 완료: {speaker_count}명, {len(segments)}개 세그먼트")
        
        # 3️⃣ 화자별 세그먼트 저장
        self.update_state(state='PROGRESS', meta={'step': 'save_segments', 'progress': 60})
        
        with get_db_context() as db:
            if segments:
                print(f"📝 {len(segments)}개 화자별 세그먼트 저장")
                for idx, seg in enumerate(segments):
                    try:
                        # FK 보장: 세그먼트 저장 전 recording 재확인
                        if not crud.get_recording(db, recording_id):
                            print(f"⚠️  세그먼트 저장 시 recording 없음 → 재시도")
                            raise self.retry(exc=Exception("recording missing while saving segments"), countdown=30)
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
                    except Exception as e:
                        print(f"❌ 세그먼트 저장 실패(idx={idx}): {e}")
                        raise
            else:
                # 백업: 세그먼트 없으면 전체 텍스트
                # FK 보장
                if not crud.get_recording(db, recording_id):
                    print(f"⚠️  백업 세그먼트 저장 전 recording 없음 → 재시도")
                    raise self.retry(exc=Exception("recording missing while saving fallback segment"), countdown=30)
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
            
            # transcript 업데이트
            crud.update_recording(
                db,
                recording_id,
                transcript=transcript,
                lang_auto=language,
                duration=len(transcript) * 100,
            )
        
        # 4️⃣ AI 제목 생성
        self.update_state(state='PROGRESS', meta={'step': 'generate_title', 'progress': 70})
        
        print(f"📝 AI 제목 생성 중...")
        ai_title = summarizer.generate_meeting_title_from_content_sync(transcript)
        print(f"✅ AI 제목: {ai_title}")
        
        # 5️⃣ 요약 생성
        self.update_state(state='PROGRESS', meta={'step': 'generate_summary', 'progress': 85})
        
        print(f"🧠 요약 생성 중...")
        summary_result = summarizer.summarize_and_extract_sync(
            transcript=transcript,
            meeting_title=ai_title
        )
        
        # 6️⃣ DB 저장
        self.update_state(state='PROGRESS', meta={'step': 'save_results', 'progress': 95})
        
        # meeting 정보 추출
        meeting_info = summary_result.get("meeting", {})
        
        with get_db_context() as db:
            # AI 태그 추천
            from services.summarizer import MeetingSummarizer
            summarizer = MeetingSummarizer()
            suggested_tags = summarizer.suggest_tags(
                transcript=transcript,
                summary=summary_result["summary"]
            )
            
            print(f"🏷️ AI 추천 태그: {suggested_tags}")
            
            crud.update_recording(
                db,
                recording_id,
                title=ai_title,
                summary=summary_result["summary"],
                participants=meeting_info.get("participants", []),
                tags=suggested_tags,  # AI 추천 태그 자동 저장
                meeting_status=meeting_info.get("status", "완료"),
                questions_answers=summary_result.get("questions_answers", []),
                open_issues=summary_result.get("open_issues", []),
                key_insights=summary_result.get("key_insights", []),
                status="ready"
            )
            
            crud.create_decisions(db, recording_id, summary_result["decisions"])
            crud.create_actions(db, recording_id, summary_result["actions"])
            
            # 태그를 recording_tags 테이블에 저장
            if suggested_tags:
                from models.tag import recording_tags
                import json
                
                # 기존 태그 관계 삭제
                db.execute(recording_tags.delete().where(recording_tags.c.recording_id == recording_id))
                
                # 태그 객체 생성 또는 조회
                tag_objects = []
                for tag_name in suggested_tags:
                    if not tag_name.strip():
                        continue
                    
                    # 태그가 이미 존재하는지 확인
                    from models.tag import Tag
                    existing_tag = db.query(Tag).filter(Tag.name == tag_name.strip()).first()
                    
                    if existing_tag:
                        tag_objects.append(existing_tag)
                    else:
                        # 새 태그 생성
                        new_tag = Tag(
                            name=tag_name.strip(),
                            color="#8B5CF6"  # 기본 색상
                        )
                        db.add(new_tag)
                        db.flush()  # ID 생성
                        tag_objects.append(new_tag)
                
                # recording_tags에 JSON 데이터 저장
                if tag_objects:
                    tags_json = json.dumps([{"name": tag.name, "color": tag.color} for tag in tag_objects], ensure_ascii=False)
                    db.execute(recording_tags.insert().values(
                        recording_id=recording_id,
                        tag_id=tag_objects[0].id,
                        tags=tags_json
                    ))
                
                db.commit()
                print(f"✅ 태그 저장 완료: {len(suggested_tags)}개")
        
        print(f"✅ [Celery Worker] 처리 완료: {recording_id}")
        print(f"   제목: {ai_title}")
        print(f"   요약 길이: {len(summary_result['summary'])} 문자")
        
        return {
            "recording_id": recording_id,
            "status": "completed",
            "title": ai_title,
            "transcript_length": len(transcript)
        }
        
    except Exception as e:
        print(f"❌ [Celery Worker] 작업 실패: {recording_id}")
        print(f"   오류: {e}")
        import traceback
        traceback.print_exc()
        
        # DB 상태 업데이트
        try:
            with get_db_context() as db:
                crud.update_recording(db, recording_id, status="error")
        except:
            pass
        
        # 재시도 (최대 3회)
        raise self.retry(exc=e, countdown=60)


@celery_app.task(name='tasks.audio_tasks.process_summary_task')
def process_summary_task(recording_id: str):
    """
    기존 녹음의 요약 재생성
    """
    try:
        print(f"🧠 [Celery Worker] 요약 재생성: {recording_id}")
        
        summarizer = MeetingSummarizer()
        
        with get_db_context() as db:
            recording = crud.get_recording(db, recording_id)
            if not recording or not recording.transcript:
                raise Exception("녹음 또는 텍스트를 찾을 수 없습니다")
            
            # AI 제목 생성
            ai_title = summarizer.generate_meeting_title_from_content_sync(recording.transcript)
            
            # 요약 생성
            summary_result = summarizer.summarize_and_extract_sync(
                transcript=recording.transcript,
                meeting_title=ai_title
            )
            
            # meeting 정보 추출
            meeting_info = summary_result.get("meeting", {})
            
            # DB 저장
            # AI 태그 추천
            from services.summarizer import MeetingSummarizer
            summarizer = MeetingSummarizer()
            suggested_tags = summarizer.suggest_tags(
                transcript=transcript,
                summary=summary_result["summary"]
            )
            
            print(f"🏷️ AI 추천 태그: {suggested_tags}")
            
            crud.update_recording(
                db,
                recording_id,
                title=ai_title,
                summary=summary_result["summary"],
                participants=meeting_info.get("participants", []),
                tags=suggested_tags,  # AI 추천 태그 자동 저장
                meeting_status=meeting_info.get("status", "완료"),
                questions_answers=summary_result.get("questions_answers", []),
                open_issues=summary_result.get("open_issues", []),
                key_insights=summary_result.get("key_insights", []),
                status="ready"
            )
            
            # 기존 결정사항/액션 삭제 후 새로 생성
            from sqlalchemy import text
            db.execute(text(f"DELETE FROM decisions WHERE recording_id = '{recording_id}'"))
            db.execute(text(f"DELETE FROM actions WHERE recording_id = '{recording_id}'"))
            db.commit()
            
            crud.create_decisions(db, recording_id, summary_result["decisions"])
            crud.create_actions(db, recording_id, summary_result["actions"])
        
        print(f"✅ [Celery Worker] 요약 재생성 완료: {recording_id}")
        
        return {
            "recording_id": recording_id,
            "status": "completed",
            "title": ai_title
        }
        
    except Exception as e:
        print(f"❌ [Celery Worker] 요약 재생성 실패: {recording_id}")
        print(f"   오류: {e}")
        import traceback
        traceback.print_exc()
        raise


@celery_app.task(
    name='tasks.audio_tasks.process_hybrid_recording',
    bind=True,
    max_retries=2,  # 재시도 2회로 줄임
    default_retry_delay=30,  # 30초 후 재시도
    queue='stt',  # STT 큐 사용
    time_limit=1800,  # 30분 하드 타임아웃 (강제 종료)
    soft_time_limit=1500,  # 25분 소프트 타임아웃 (예외 발생)
    acks_late=True,  # 작업 완료 후 ACK (실패 시 재시도 가능)
    reject_on_worker_lost=True  # 워커 다운 시 재시도
)
def process_hybrid_recording(self, recording_id: str):
    """
    하이브리드 녹음 후처리 (Celery Worker)
    - 오디오 청크 병합
    - STT (화자 분리)
    - 요약 생성
    - 숫자 검증
    
    Args:
        recording_id: 녹음 ID
    
    Returns:
        처리 결과
    """
    try:
        print(f"🎤 [Celery Worker] 하이브리드 녹음 처리 시작: {recording_id}")
        
        from services.audio_processor import AudioProcessor
        from services.summarizer import MeetingSummarizer
        from services.assembly_ai_stt import AssemblyAISTTService
        from services.number_verifier import NumberVerifier
        from services.audio_enhancement import audio_enhancement_service
        
        audio_processor = AudioProcessor()
        summarizer = MeetingSummarizer()
        stt_service = AssemblyAISTTService()
        number_verifier = NumberVerifier()
        
        # 진행률 업데이트
        self.update_state(state='PROGRESS', meta={'step': 'merge_audio', 'progress': 10})
        
        # 1️⃣ 오디오 청크 병합
        with get_db_context() as db:
            recording = crud.get_recording(db, recording_id)
            if not recording:
                raise Exception(f"Recording not found: {recording_id}")
            
            # 기존 세그먼트 개수 확인
            chunk_count = db.query(Segment).filter(Segment.recording_id == recording_id).count()
            
            print(f"🎵 Merging {chunk_count} audio chunks...")
        
        merged_path = None
        actual_duration = None
        
        try:
            from services.audio_storage import AudioStorage
            audio_storage = AudioStorage()
            merged_path, actual_duration = asyncio.run(
                audio_storage.merge_chunks(recording_id, chunk_count)
            )
            print(f"✅ Audio chunks merged: {merged_path}")
            print(f"   실제 길이: {actual_duration}ms ({actual_duration/1000:.1f}초)")
        except Exception as e:
            print(f"⚠️  Audio merge failed: {e}")
            raise
        
        # 2️⃣ 병합된 오디오 STT (화자 분리)
        self.update_state(state='PROGRESS', meta={'step': 'transcribe', 'progress': 30})
        
        print(f"🎤 Re-transcribing merged audio with speaker diarization...")
        
        with open(merged_path, 'rb') as f:
            m4a_content = f.read()
        
        # 🎤 음성 품질 개선
        try:
            print(f"🎤 병합된 오디오 품질 개선 시작...")
            enhanced_audio = audio_enhancement_service.enhance_audio(
                audio_content=m4a_content,
                input_format="m4a",
                enhancement_options={
                    'noise_reduction': True,
                    'amplification': True,
                    'normalization': True,
                    'auto_correction': True
                }
            )
            print(f"✅ 병합된 오디오 품질 개선 완료")
            m4a_content = enhanced_audio
            
            # 개선된 오디오 저장
            with open(merged_path, 'wb') as f:
                f.write(m4a_content)
            print(f"💾 개선된 오디오 저장: {merged_path}")
        except Exception as e:
            print(f"⚠️ 병합된 오디오 품질 개선 실패, 원본 사용: {e}")
        
        # AssemblyAI STT
        result = asyncio.run(stt_service.transcribe_audio(
            m4a_content,
            use_wav=False,
            min_speakers=2,
            max_speakers=5
        ))
        
        final_transcript = result["text"]
        language = result["language"]
        segments = result.get("segments", [])
        speaker_count = result.get("speaker_count", 0)
        
        print(f"✅ STT 완료: {speaker_count}명, {len(segments)}개 세그먼트")
        
        # 3️⃣ 기존 세그먼트 삭제 후 새 세그먼트 저장
        self.update_state(state='PROGRESS', meta={'step': 'save_segments', 'progress': 50})
        
        with get_db_context() as db:
            # 기존 세그먼트 삭제
            db.query(Segment).filter(Segment.recording_id == recording_id).delete()
            db.commit()
            
            # 새 세그먼트 저장
            if segments:
                print(f"📝 {len(segments)}개 화자별 세그먼트 저장")
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
        
        # 4️⃣ AI 제목 생성
        self.update_state(state='PROGRESS', meta={'step': 'generate_title', 'progress': 60})
        
        print(f"📝 AI 제목 생성 중...")
        ai_title = summarizer.generate_meeting_title_from_content_sync(final_transcript)
        print(f"✅ AI 제목: {ai_title}")
        
        # 5️⃣ 요약 생성
        self.update_state(state='PROGRESS', meta={'step': 'generate_summary', 'progress': 75})
        
        print(f"🧠 요약 생성 중...")
        summary_result = summarizer.summarize_and_extract_sync(
            transcript=final_transcript,
            meeting_title=ai_title
        )
        
        # 6️⃣ 숫자 검증
        self.update_state(state='PROGRESS', meta={'step': 'verify_numbers', 'progress': 90})
        
        print(f"🔢 숫자 검증 중...")
        detected_numbers = number_verifier.detect_numbers(final_transcript)
        verified_numbers = None
        
        if detected_numbers:
            verified_numbers = asyncio.run(number_verifier.verify_numbers_with_ai(
                final_transcript,
                detected_numbers
            ))
            verified_numbers = number_verifier.format_verification_for_frontend(verified_numbers)
        
        # 7️⃣ DB 저장
        self.update_state(state='PROGRESS', meta={'step': 'save_results', 'progress': 95})
        
        meeting_info = summary_result.get("meeting", {})
        
        with get_db_context() as db:
            # AI 태그 추천
            from services.summarizer import MeetingSummarizer
            summarizer = MeetingSummarizer()
            suggested_tags = summarizer.suggest_tags(
                transcript=final_transcript,
                summary=summary_result["summary"]
            )
            
            print(f"🏷️ AI 추천 태그: {suggested_tags}")
            
            crud.update_recording(
                db,
                recording_id,
                title=ai_title,
                summary=summary_result["summary"],
                transcript=final_transcript,
                participants=meeting_info.get("participants", []),
                tags=suggested_tags,  # AI 추천 태그 자동 저장
                meeting_status=meeting_info.get("status", "완료"),
                questions_answers=summary_result.get("questions_answers", []),
                open_issues=summary_result.get("open_issues", []),
                key_insights=summary_result.get("key_insights", []),
                verified_numbers=verified_numbers,
                duration=actual_duration,
                lang_auto=language,
                status="ready"
            )
            
            # 기존 결정사항/액션 삭제 후 새로 생성
            from sqlalchemy import text
            db.execute(text(f"DELETE FROM decisions WHERE recording_id = '{recording_id}'"))
            db.execute(text(f"DELETE FROM actions WHERE recording_id = '{recording_id}'"))
            db.commit()
            
            crud.create_decisions(db, recording_id, summary_result["decisions"])
            crud.create_actions(db, recording_id, summary_result["actions"])
        
        print(f"✅ [Celery Worker] 하이브리드 녹음 처리 완료: {recording_id}")
        print(f"   제목: {ai_title}")
        print(f"   요약 길이: {len(summary_result['summary'])} 문자")
        
        return {
            "recording_id": recording_id,
            "status": "completed",
            "title": ai_title,
            "transcript_length": len(final_transcript)
        }
        
    except Exception as e:
        print(f"❌ [Celery Worker] 하이브리드 녹음 처리 실패: {recording_id}")
        print(f"   오류: {e}")
        import traceback
        traceback.print_exc()
        
        # 현재 재시도 횟수 확인
        retry_count = self.request.retries
        max_retries = self.max_retries
        
        print(f"   재시도: {retry_count}/{max_retries}")
        
        # DB 상태 업데이트
        try:
            with get_db_context() as db:
                # 마지막 재시도 실패 시 완전히 실패 처리
                if retry_count >= max_retries:
                    crud.update_recording(db, recording_id, status="failed")
                    print(f"   💀 최종 실패 처리: {recording_id}")
                    
                    # 실패한 오디오 파일 정리 (선택적)
                    try:
                        import os
                        import shutil
                        audio_dir = f"storage/audio/{recording_id}"
                        if os.path.exists(audio_dir):
                            shutil.rmtree(audio_dir)
                            print(f"   🗑️  오디오 파일 삭제: {audio_dir}")
                    except Exception as cleanup_error:
                        print(f"   ⚠️  파일 정리 실패: {cleanup_error}")
                else:
                    # 재시도 중...
                    crud.update_recording(db, recording_id, status="processing")
                    print(f"   🔄 재시도 예정...")
        except Exception as db_error:
            print(f"   ⚠️  DB 업데이트 실패: {db_error}")
        
        # 최종 실패 시 예외 던지지 않음 (재시도 안함)
        if retry_count >= max_retries:
            return {
                "recording_id": recording_id,
                "status": "failed",
                "error": str(e)
            }
        
        # 재시도 (30초 후)
        raise self.retry(exc=e, countdown=30)


@celery_app.task(
    name='tasks.audio_tasks.process_audio_from_s3',
    bind=True,
    max_retries=3,
    default_retry_delay=60
)
def process_audio_from_s3(self, recording_id: str, s3_object_key: str, file_ext: str):
    """
    S3에서 오디오 다운로드 후 STT 처리
    
    Args:
        recording_id: 녹음 ID
        s3_object_key: S3 객체 키
        file_ext: 파일 확장자
    
    Returns:
        처리 결과
    """
    import boto3
    import os
    
    try:
        print(f"📥 [S3 STT] S3에서 다운로드 시작: {recording_id}")
        print(f"   Object Key: {s3_object_key}")
        
        # S3 클라이언트
        from services.s3_storage import get_s3_storage
        s3_service = get_s3_storage()
        
        # 임시 파일로 다운로드
        with tempfile.NamedTemporaryFile(suffix=f".{file_ext}", delete=False) as tmp_file:
            local_path = tmp_file.name
            
            print(f"📥 S3 다운로드 중: {s3_object_key}")
            s3_service.s3_client.download_file(
                s3_service.bucket_name,
                s3_object_key,
                local_path
            )
            
            file_size = os.path.getsize(local_path)
            print(f"✅ 다운로드 완료: {file_size / 1024 / 1024:.1f}MB")
        
        # 기존 process_audio_task 로직 재사용
        result = process_audio_task(recording_id, local_path, file_ext)
        
        # 임시 파일 삭제
        try:
            os.remove(local_path)
            print(f"🗑️  임시 파일 삭제: {local_path}")
        except:
            pass
        
        return result
        
    except Exception as e:
        print(f"❌ [S3 STT] 처리 실패: {recording_id}")
        print(f"   오류: {e}")
        import traceback
        traceback.print_exc()
        
        # 상태 업데이트
        with get_db_context() as db:
            crud.update_recording(db, recording_id, status="failed")
        
        raise self.retry(exc=e, countdown=60)

