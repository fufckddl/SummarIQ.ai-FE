"""
오디오 처리 유틸리티 함수
"""


def estimate_processing_time(duration_sec: float) -> int:
    """
    STT 처리 시간 예상
    
    Args:
        duration_sec: 오디오 길이 (초)
    
    Returns:
        예상 처리 시간 (초)
    """
    # AssemblyAI 처리 시간: 전체 길이의 약 30%
    return int(duration_sec * 0.3)

