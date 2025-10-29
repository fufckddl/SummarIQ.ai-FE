# MySQL 마이그레이션 가이드

## ✅ 완료된 작업

### 1. 데이터베이스 준비
- ✅ MySQL 설치 및 비밀번호 설정 (root/your-mysql-password)
- ✅ summariq 데이터베이스 생성 (utf8mb4)
- ✅ 4개 테이블 생성 (recordings, segments, decisions, actions)

### 2. 백엔드 구조
- ✅ models/ 폴더에 모델 분리
  - recording.py
  - segment.py
  - decision.py
  - action.py
- ✅ database/ 폴더 설정
  - config.py (MySQL 설정)
  - connection.py (연결 관리)
  - crud.py (CRUD 함수)
  - schema.sql (SQL 스키마)

### 3. API 엔드포인트 수정
- ✅ /stt/start - MySQL 연동 완료
- ✅ /stt/chunk - MySQL 연동 완료
- ⏳ 나머지 엔드포인트 수정 필요

---

## 🔧 수정이 필요한 엔드포인트

아래 엔드포인트들은 아직 `recordings_db` 딕셔너리를 사용 중입니다.
각 엔드포인트에 `db: Session = Depends(get_db)`를 추가하고,
`recordings_db` 대신 `crud` 함수를 사용하도록 수정해야 합니다.

### 1. /stt/commit
**현재**: `recordings_db[recordingId]` 사용
**변경**: 
```python
@router.post("/commit")
async def commit_recording(
    request: CommitRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)  # 추가
) -> dict:
    # recordings_db 대신 MySQL 사용
    recording = crud.get_recording(db, request.recordingId)
    if not recording:
        raise HTTPException(status_code=404, detail="Recording not found")
    
    # 세그먼트에서 전체 텍스트 합본
    segments = crud.get_segments(db, request.recordingId)
    transcript = " ".join([seg.text for seg in segments])
    
    # ... (나머지 로직)
    
    # 백그라운드 함수 내부에서도 DB 세션 사용
    async def generate_summary_background():
        from database.connection import get_db_context
        with get_db_context() as db:
            # AI 제목 생성
            ai_title = await summarizer.generate_meeting_title_from_content(transcript)
            
            # 요약 생성
            result = await summarizer.summarize_and_extract(transcript, ai_title)
            
            # MySQL 업데이트
            crud.update_recording(
                db, 
                request.recordingId,
                title=ai_title,
                summary=result["summary"],
                status="ready"
            )
            
            # Decisions 저장
            crud.create_decisions(db, request.recordingId, result["decisions"])
            
            # Actions 저장
            crud.create_actions(db, request.recordingId, result["actions"])
```

### 2. /stt/recordings (목록 조회)
**변경**:
```python
@router.get("/recordings")
async def list_recordings(db: Session = Depends(get_db)) -> List[dict]:
    recordings = crud.list_recordings(db)
    return [rec.to_dict() for rec in recordings]
```

### 3. GET /stt/recordings/{recording_id}
**변경**:
```python
@router.get("/recordings/{recording_id}")
async def get_recording(recording_id: str, db: Session = Depends(get_db)) -> dict:
    recording = crud.get_recording_with_details(db, recording_id)
    if not recording:
        raise HTTPException(status_code=404, detail="Recording not found")
    return recording
```

### 4. DELETE /stt/recordings/{recording_id}
**변경**:
```python
@router.delete("/recordings/{recording_id}")
async def delete_recording(recording_id: str, db: Session = Depends(get_db)) -> dict:
    success = crud.delete_recording(db, recording_id)
    if not success:
        raise HTTPException(status_code=404, detail="Recording not found")
    return {"message": "Recording deleted"}
```

### 5. POST /stt/recordings/{recording_id}/summarize
**변경**:
```python
@router.post("/recordings/{recording_id}/summarize")
async def summarize_recording(recording_id: str, db: Session = Depends(get_db)) -> dict:
    recording = crud.get_recording(db, recording_id)
    if not recording:
        raise HTTPException(status_code=404, detail="Recording not found")
    
    # ... (요약 생성 로직)
    
    # 결과 저장
    crud.update_recording(db, recording_id, title=ai_title, summary=result["summary"])
    crud.create_decisions(db, recording_id, result["decisions"])
    crud.create_actions(db, recording_id, result["actions"])
```

### 6. POST /stt/upload
**변경**:
```python
@router.post("/upload")
async def upload_audio_file(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db)  # 추가
) -> dict:
    # MySQL에 녹음 생성
    recording = crud.create_recording(db, title=file.filename.rsplit('.', 1)[0])
    recording_id = recording.id
    
    # ... (STT 변환 로직)
    
    # 세그먼트 저장
    crud.create_segment(
        db=db,
        recording_id=recording_id,
        seq=0,
        text=transcript,
        # ...
    )
    
    # 백그라운드에서 요약 생성 (위의 commit과 동일한 패턴)
```

### 7. POST /stt/test/add-transcript (테스트용)
**변경**:
```python
@router.post("/test/add-transcript")
async def add_test_transcript(
    recordingId: str = Form(...),
    transcript: str = Form(...),
    db: Session = Depends(get_db)  # 추가
) -> dict:
    recording = crud.get_recording(db, recordingId)
    if not recording:
        raise HTTPException(status_code=404, detail="Recording not found")
    
    # 세그먼트 생성
    segment = crud.create_segment(
        db=db,
        recording_id=recordingId,
        seq=0,
        text=transcript,
        # ...
    )
```

---

## 🚀 빠른 마이그레이션 스크립트

전체 파일을 한 번에 수정하는 Python 스크립트를 만들었습니다.

```bash
cd /Users/dlckdfuf/Desktop/SummarIQ/backend
python migrate_to_mysql.py
```

이 스크립트가:
1. 모든 `recordings_db` 참조를 찾아서
2. `crud` 함수 호출로 변경하고
3. `db: Session = Depends(get_db)` 파라미터 추가

---

## 🧪 테스트 방법

### 1. 서버 재시작
```bash
cd /Users/dlckdfuf/Desktop/SummarIQ/backend
./stop_server.sh
./start_server.sh
```

### 2. API 테스트
```bash
# 녹음 시작
curl -X POST "http://localhost:8000/stt/start"

# 녹음 목록
curl "http://localhost:8000/stt/recordings"

# 녹음 상세
curl "http://localhost:8000/stt/recordings/{id}"
```

### 3. MySQL 확인
```bash
mysql -u root -pyour-mysql-password -e "USE summariq; SELECT * FROM recordings;"
mysql -u root -pyour-mysql-password -e "USE summariq; SELECT * FROM segments;"
```

---

## 📋 체크리스트

- [x] MySQL 설치 및 설정
- [x] 데이터베이스 및 테이블 생성
- [x] 모델 분리 (models/)
- [x] CRUD 함수 작성 (database/crud.py)
- [x] /stt/start 수정
- [x] /stt/chunk 수정
- [ ] /stt/commit 수정
- [ ] /stt/recordings 수정
- [ ] GET /stt/recordings/{id} 수정
- [ ] DELETE /stt/recordings/{id} 수정
- [ ] POST /stt/recordings/{id}/summarize 수정
- [ ] POST /stt/upload 수정
- [ ] POST /stt/test/add-transcript 수정
- [ ] 오디오 파일 로컬 저장
- [ ] 프론트엔드 로컬 재생
- [ ] 통합 테스트

