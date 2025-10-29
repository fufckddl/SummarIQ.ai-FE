"""
작업 상태 CRUD
"""
from sqlalchemy import text
from sqlalchemy.orm import Session
from typing import Optional, Dict
from datetime import datetime
import json


def create_task(
    db: Session,
    task_id: str,
    recording_id: str,
    task_type: str = 'stt',
    backend: str = 'celery'
) -> Dict:
    """작업 생성"""
    query = text("""
        INSERT INTO task_status 
        (id, recording_id, task_type, status, backend, created_at)
        VALUES 
        (:task_id, :recording_id, :task_type, 'pending', :backend, NOW())
    """)
    
    db.execute(query, {
        "task_id": task_id,
        "recording_id": recording_id,
        "task_type": task_type,
        "backend": backend
    })
    db.commit()
    
    return get_task(db, task_id)


def get_task(db: Session, task_id: str) -> Optional[Dict]:
    """작업 조회"""
    query = text("""
        SELECT * FROM task_status WHERE id = :task_id
    """)
    
    result = db.execute(query, {"task_id": task_id}).fetchone()
    
    if not result:
        return None
    
    return {
        "id": result.id,
        "recording_id": result.recording_id,
        "task_type": result.task_type,
        "status": result.status,
        "backend": result.backend,
        "progress": result.progress,
        "current_step": result.current_step,
        "created_at": result.created_at.isoformat() if result.created_at else None,
        "started_at": result.started_at.isoformat() if result.started_at else None,
        "completed_at": result.completed_at.isoformat() if result.completed_at else None,
        "error_message": result.error_message,
        "retry_count": result.retry_count,
    }


def update_task_status(
    db: Session,
    task_id: str,
    status: str,
    progress: Optional[int] = None,
    current_step: Optional[str] = None,
    error_message: Optional[str] = None
) -> bool:
    """작업 상태 업데이트"""
    updates = ["status = :status"]
    params = {"task_id": task_id, "status": status}
    
    if progress is not None:
        updates.append("progress = :progress")
        params["progress"] = progress
    
    if current_step is not None:
        updates.append("current_step = :current_step")
        params["current_step"] = current_step
    
    if error_message is not None:
        updates.append("error_message = :error_message")
        params["error_message"] = error_message
    
    if status == 'processing' and progress == 0:
        updates.append("started_at = NOW()")
    
    if status in ['completed', 'failed']:
        updates.append("completed_at = NOW()")
    
    query = text(f"""
        UPDATE task_status 
        SET {', '.join(updates)}
        WHERE id = :task_id
    """)
    
    db.execute(query, params)
    db.commit()
    
    return True


def get_recording_tasks(db: Session, recording_id: str):
    """녹음 관련 모든 작업 조회"""
    query = text("""
        SELECT * FROM task_status 
        WHERE recording_id = :recording_id
        ORDER BY created_at DESC
    """)
    
    results = db.execute(query, {"recording_id": recording_id}).fetchall()
    
    return [
        {
            "id": r.id,
            "task_type": r.task_type,
            "status": r.status,
            "backend": r.backend,
            "progress": r.progress,
            "current_step": r.current_step,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in results
    ]

