"""
🎤 음성 품질 개선 API 라우터
실제 오디오 처리 및 품질 개선 기능
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
import tempfile
import os
import json
import logging

from database.connection import get_db
from routers.auth import get_current_user
from services.audio_enhancement import audio_enhancement_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/audio-enhancement", tags=["audio-enhancement"])

@router.post("/enhance")
async def enhance_audio(
    audio: UploadFile = File(...),
    enhancement_options: str = Form(...)
):
    """
    음성 품질 개선 API (인증 불필요)
    
    Args:
        audio: 업로드된 오디오 파일
        enhancement_options: 개선 옵션 (JSON 문자열)
        
    Returns:
        개선된 오디오 파일
    """
    try:
        logger.info(f"🎤 음성 품질 개선 요청 시작")
        
        # 옵션 파싱
        try:
            options = json.loads(enhancement_options)
        except json.JSONDecodeError:
            options = {
                'noise_reduction': True,
                'amplification': True,
                'normalization': True,
                'auto_correction': True
            }
        
        # 임시 파일로 저장
        with tempfile.NamedTemporaryFile(delete=False, suffix='.m4a') as temp_input:
            content = await audio.read()
            temp_input.write(content)
            temp_input_path = temp_input.name
        
        try:
            # 음성 품질 개선 처리
            logger.info(f"🎤 오디오 개선 시작 - 파일: {audio.filename}")
            
            enhanced_content = audio_enhancement_service.enhance_audio(
                audio_content=content,
                input_format="m4a",
                enhancement_options=options
            )
            
            # 개선된 파일을 임시로 저장
            with tempfile.NamedTemporaryFile(delete=False, suffix='_enhanced.m4a') as temp_output:
                temp_output.write(enhanced_content)
                temp_output_path = temp_output.name
            
            logger.info(f"✅ 오디오 개선 완료")
            
            # 개선된 파일 반환
            from starlette.background import BackgroundTask
            return FileResponse(
                path=temp_output_path,
                media_type='audio/mpeg',
                filename=f"enhanced_{audio.filename}",
                background=BackgroundTask(lambda: os.unlink(temp_output_path) if os.path.exists(temp_output_path) else None)
            )
            
        finally:
            # 입력 파일 정리
            if os.path.exists(temp_input_path):
                os.unlink(temp_input_path)
                
    except Exception as e:
        logger.error(f"❌ 음성 품질 개선 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=f"음성 품질 개선에 실패했습니다: {str(e)}")

@router.get("/test")
async def test_audio_enhancement():
    """
    음성 품질 개선 서비스 테스트
    """
    try:
        # 간단한 테스트 오디오 생성 (1초 무음)
        import numpy as np
        import soundfile as sf
        import io
        
        # 1초 무음 생성 (16kHz, 모노)
        sample_rate = 16000
        duration = 1.0
        silence = np.zeros(int(sample_rate * duration), dtype=np.float32)
        
        # WAV 형식으로 변환
        output_buffer = io.BytesIO()
        sf.write(output_buffer, silence, sample_rate, format='WAV')
        test_audio = output_buffer.getvalue()
        
        # 음성 품질 개선 테스트
        enhanced_audio = audio_enhancement_service.enhance_audio(
            audio_content=test_audio,
            input_format="wav",
            enhancement_options={
                'noise_reduction': True,
                'amplification': True,
                'normalization': True,
                'auto_correction': True
            }
        )
        
        return {
            "status": "success",
            "message": "음성 품질 개선 서비스가 정상 작동합니다",
            "original_size": len(test_audio),
            "enhanced_size": len(enhanced_audio)
        }
        
    except Exception as e:
        logger.error(f"❌ 음성 품질 개선 테스트 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=f"테스트 실패: {str(e)}")
