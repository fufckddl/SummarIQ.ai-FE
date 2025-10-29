"""
사용자 설정 API 라우터
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any

from database.connection import get_db
from utils.auth_dependency import get_current_user
from models.user import User

router = APIRouter(prefix="/api/user/settings", tags=["user-settings"])

# Pydantic 모델들
class AudioQualitySettings(BaseModel):
    noiseReduction: bool = True
    voiceAmplification: bool = True
    audioNormalization: bool = True
    autoCorrection: bool = True

class AudioQualitySettingsUpdate(BaseModel):
    enabled: bool
    settings: Optional[AudioQualitySettings] = None

# ==================== API 엔드포인트 ====================

@router.get("/audio-quality")
async def get_audio_quality_settings(
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    사용자의 음성 품질 설정을 조회합니다.
    """
    user_id = current_user["id"]
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # 기본 설정
    default_settings = {
        "noiseReduction": True,
        "voiceAmplification": True,
        "audioNormalization": True,
        "autoCorrection": True
    }
    
    return {
        "enabled": user.audio_quality_enabled if user.audio_quality_enabled is not None else True,
        "settings": user.audio_quality_settings if user.audio_quality_settings else default_settings
    }

@router.put("/audio-quality")
async def update_audio_quality_settings(
    settings_update: AudioQualitySettingsUpdate,
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    사용자의 음성 품질 설정을 업데이트합니다.
    """
    user_id = current_user["id"]
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # 설정 업데이트
    user.audio_quality_enabled = settings_update.enabled
    
    if settings_update.settings:
        user.audio_quality_settings = settings_update.settings.dict()
    
    db.commit()
    db.refresh(user)
    
    return {
        "message": "Audio quality settings updated successfully",
        "enabled": user.audio_quality_enabled,
        "settings": user.audio_quality_settings
    }

