"""
텍스트 처리 유틸리티
"""
import re
from typing import List


def remove_consecutive_duplicates(text: str, min_length: int = 10) -> str:
    """
    연속된 중복 구문 제거
    
    예: "안녕하세요 안녕하세요" → "안녕하세요"
    
    Args:
        text: 원본 텍스트
        min_length: 최소 중복 감지 길이 (글자 수)
    
    Returns:
        중복이 제거된 텍스트
    """
    if not text or len(text) < min_length * 2:
        return text
    
    words = text.split()
    
    # 연속된 중복 구문 찾기
    i = 0
    cleaned_words = []
    
    while i < len(words):
        # 현재 위치에서 시작하는 구문들을 체크
        found_duplicate = False
        
        # 최대 절반 길이까지 체크 (구문 길이)
        for phrase_len in range(min_length, len(words) - i):
            if i + phrase_len * 2 > len(words):
                break
            
            # 현재 구문
            phrase1 = ' '.join(words[i:i+phrase_len])
            # 다음 구문
            phrase2 = ' '.join(words[i+phrase_len:i+phrase_len*2])
            
            # 완전 일치하면
            if phrase1 == phrase2:
                print(f"🔄 중복 구문 제거 ({phrase_len}단어): {phrase1[:50]}...")
                cleaned_words.extend(words[i:i+phrase_len])
                i += phrase_len * 2  # 중복 건너뛰기
                found_duplicate = True
                break
        
        if not found_duplicate:
            cleaned_words.append(words[i])
            i += 1
    
    return ' '.join(cleaned_words)


def remove_duplicate_sentences(text: str, threshold: float = 0.8) -> str:
    """
    연속된 중복 문장 제거 (단순 버전)
    
    Args:
        text: 원본 텍스트
        threshold: 사용 안 함 (호환성)
    
    Returns:
        중복이 제거된 텍스트
    """
    return remove_consecutive_duplicates(text, min_length=3)


def calculate_similarity(text1: str, text2: str) -> float:
    """
    두 텍스트의 유사도 계산 (Jaccard similarity)
    
    Returns:
        0.0 ~ 1.0 (1.0이 완전 동일)
    """
    # 단어 집합으로 변환
    words1 = set(text1.lower().split())
    words2 = set(text2.lower().split())
    
    if not words1 or not words2:
        return 0.0
    
    # Jaccard similarity
    intersection = words1 & words2
    union = words1 | words2
    
    return len(intersection) / len(union) if union else 0.0


def remove_exact_duplicates(segments_text: List[str]) -> List[str]:
    """
    연속된 완전 중복 세그먼트 제거
    
    Args:
        segments_text: 세그먼트 텍스트 리스트
    
    Returns:
        중복이 제거된 리스트
    """
    if not segments_text:
        return []
    
    cleaned = [segments_text[0]]
    
    for i in range(1, len(segments_text)):
        current = segments_text[i].strip()
        previous = cleaned[-1].strip()
        
        # 완전 동일하면 스킵
        if current != previous:
            cleaned.append(segments_text[i])
        else:
            print(f"🔄 세그먼트 중복 제거: {current[:50]}...")
    
    return cleaned


def normalize_whitespace(text: str) -> str:
    """공백 정규화"""
    # 연속 공백을 하나로
    text = re.sub(r'\s+', ' ', text)
    # 양쪽 공백 제거
    return text.strip()

