"""
오디오 메타데이터 추출 서비스
"""
from pydub import AudioSegment
from pathlib import Path


def estimate_audio_duration_from_size(file_size_bytes: int, file_ext: str = "m4a") -> float:
    """
    파일 크기로부터 오디오 길이 추정 (빠른 계산)
    
    Args:
        file_size_bytes: 파일 크기 (바이트)
        file_ext: 파일 확장자
    
    Returns:
        추정 길이 (초)
    """
    # 형식별 평균 비트레이트 (kbps)
    avg_bitrates = {
        "m4a": 128,    # AAC 평균
        "aac": 128,
        "mp3": 128,
        "wav": 1411,   # 16bit 44.1kHz stereo
        "ogg": 96,
        "opus": 64,
    }
    
    # 비트레이트 가져오기 (기본값: 128kbps)
    bitrate_kbps = avg_bitrates.get(file_ext.lower(), 128)
    
    # 길이 계산: 파일 크기(bytes) / (비트레이트(kbps) * 1000 / 8)
    duration_sec = (file_size_bytes * 8) / (bitrate_kbps * 1000)
    
    return duration_sec


def estimate_processing_time(audio_duration_sec: float) -> int:
    """
    오디오 길이로부터 처리 시간 추정
    
    Args:
        audio_duration_sec: 오디오 길이 (초)
    
    Returns:
        예상 처리 시간 (분)
    """
    # STT 처리 시간 = 오디오 길이의 약 1/3 ~ 1/2
    # 요약 생성 = 약 30초~1분
    # 총 = 오디오 길이의 1/2 + 1분
    
    stt_time_min = (audio_duration_sec / 60) * 0.5  # 오디오 길이의 50%
    summary_time_min = 1  # 요약 1분
    
    total_min = stt_time_min + summary_time_min
    
    return max(2, int(total_min))  # 최소 2분


def get_audio_duration_ms(file_path: str) -> int:
    """
    오디오 파일의 실제 길이를 밀리초로 반환
    
    Args:
        file_path: 오디오 파일 경로
        
    Returns:
        길이 (밀리초)
    """
    try:
        audio = AudioSegment.from_file(file_path)
        return len(audio)  # pydub은 밀리초 단위로 반환
    except Exception as e:
        print(f"⚠️  오디오 길이 추출 실패: {e}")
        return 0


def get_audio_info(file_path: str) -> dict:
    """
    오디오 파일의 상세 정보 반환
    
    Args:
        file_path: 오디오 파일 경로
        
    Returns:
        {
            "duration_ms": 90000,
            "duration_sec": 90.0,
            "channels": 1,
            "sample_rate": 44100,
            "bitrate": 128000
        }
    """
    try:
        audio = AudioSegment.from_file(file_path)
        duration_ms = len(audio)
        
        return {
            "duration_ms": duration_ms,
            "duration_sec": duration_ms / 1000,
            "channels": audio.channels,
            "sample_rate": audio.frame_rate,
            "bitrate": audio.frame_rate * audio.frame_width * 8 * audio.channels,
        }
    except Exception as e:
        print(f"⚠️  오디오 정보 추출 실패: {e}")
        return {
            "duration_ms": 0,
            "duration_sec": 0.0,
            "channels": 0,
            "sample_rate": 0,
            "bitrate": 0,
        }

