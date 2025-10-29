"""
숫자 표현 검증 서비스
- 회의록에서 숫자 표현 감지
- AI 기반 맥락 분석 및 검증
- 불확실한 숫자 표시
"""

import re
from typing import List, Dict, Optional
from openai import OpenAI
import os
import json

class NumberVerifier:
    """숫자 표현 검증 및 대안 제시"""
    
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        
        # 한글 숫자 패턴
        self.korean_number_pattern = re.compile(
            r'[일이삼사오육칠팔구십백천만억조]+(만|천|백|십|억|조)?\s*(달러|원|개|명|시간|분|초|건|대|권)',
            re.IGNORECASE
        )
        
        # 아라비아 숫자 패턴
        self.arabic_number_pattern = re.compile(
            r'\d{1,3}(,\d{3})*(\.\d+)?\s*(달러|원|개|명|시간|분|초|건|대|권|만|천|억)',
            re.IGNORECASE
        )
    
    def detect_numbers(self, text: str) -> List[Dict]:
        """
        텍스트에서 숫자 표현 찾기
        
        Returns:
            [
                {
                    'text': '만 달러',
                    'start': 10,
                    'end': 15,
                    'type': 'korean_number',
                    'unit': '달러'
                }
            ]
        """
        numbers = []
        
        # 한글 숫자
        for match in self.korean_number_pattern.finditer(text):
            numbers.append({
                'text': match.group(),
                'start': match.start(),
                'end': match.end(),
                'type': 'korean_number',
                'needs_verification': self._needs_verification(match.group())
            })
        
        # 아라비아 숫자
        for match in self.arabic_number_pattern.finditer(text):
            numbers.append({
                'text': match.group(),
                'start': match.start(),
                'end': match.end(),
                'type': 'arabic_number',
                'needs_verification': False  # 명확함
            })
        
        return numbers
    
    def _needs_verification(self, number_text: str) -> bool:
        """
        검증이 필요한 숫자인지 판단
        
        예: "만 달러" → True (이만? 삼만? 불명확)
            "이만 달러" → False (명확)
        """
        # "만", "천", "억" 등이 단독으로 나오면 검증 필요
        ambiguous_patterns = [
            r'^만\s',      # "만 달러"
            r'^천\s',      # "천 원"
            r'^억\s',      # "억 원"
            r'^백\s',      # "백 명"
        ]
        
        for pattern in ambiguous_patterns:
            if re.match(pattern, number_text):
                return True
        
        return False
    
    async def verify_numbers_with_ai(
        self, 
        transcript: str, 
        detected_numbers: List[Dict],
        context_window: int = 100
    ) -> List[Dict]:
        """
        AI를 사용하여 숫자 검증
        
        Args:
            transcript: 전체 회의록
            detected_numbers: 감지된 숫자 목록
            context_window: 전후 맥락 글자 수
            
        Returns:
            검증된 숫자 정보
        """
        if not detected_numbers:
            return []
        
        # 검증이 필요한 숫자만 필터링
        numbers_to_verify = [n for n in detected_numbers if n.get('needs_verification')]
        
        if not numbers_to_verify:
            return detected_numbers
        
        # 각 숫자에 대한 맥락 추출
        verification_requests = []
        for num in numbers_to_verify:
            start = max(0, num['start'] - context_window)
            end = min(len(transcript), num['end'] + context_window)
            context = transcript[start:end]
            
            verification_requests.append({
                'number': num['text'],
                'context': context,
                'position': num['start']
            })
        
        # AI에게 검증 요청
        prompt = f"""다음은 회의 녹음을 STT로 변환한 텍스트입니다.
일부 숫자 표현이 불명확하게 인식되었을 수 있습니다.

각 숫자에 대해 전후 맥락을 분석하여:
1. 가장 가능성 높은 정확한 값
2. 신뢰도 (high/medium/low)
3. 가능한 대안 값들 (최대 3개)

검증 대상:
{json.dumps(verification_requests, ensure_ascii=False, indent=2)}

JSON 형식으로 반환:
[
  {{
    "original": "만 달러",
    "verified": "이만 달러",
    "confidence": "medium",
    "alternatives": ["만 달러", "이만 달러", "삼만 달러"],
    "reasoning": "가격 협상 맥락에서 '이만 달러'가 가장 자연스러움"
  }}
]
"""
        
        try:
            print(f"🔍 AI 숫자 검증 시작... ({len(numbers_to_verify)}개)")
            
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,  # 낮은 온도 (일관성 중요)
                max_tokens=500
            )
            
            result = response.choices[0].message.content.strip()
            print(f"🤖 AI 검증 응답: {result[:200]}...")
            
            # JSON 파싱
            import re as regex
            cleaned_result = regex.sub(r'^```(?:json)?\s*\n?', '', result)
            cleaned_result = regex.sub(r'\n?```\s*$', '', cleaned_result)
            
            verifications = json.loads(cleaned_result.strip())
            
            # 원본 숫자 목록에 검증 결과 병합
            verified_numbers = detected_numbers.copy()
            for i, num in enumerate(verified_numbers):
                if num.get('needs_verification'):
                    # 해당 숫자의 검증 결과 찾기
                    verification = next(
                        (v for v in verifications if v.get('original') == num['text']),
                        None
                    )
                    if verification:
                        verified_numbers[i]['verification'] = verification
            
            print(f"✅ AI 숫자 검증 완료")
            return verified_numbers
            
        except Exception as e:
            print(f"❌ AI 숫자 검증 실패: {e}")
            import traceback
            traceback.print_exc()
            return detected_numbers  # 실패 시 원본 반환
    
    def format_verification_for_frontend(self, verified_numbers: List[Dict]) -> List[Dict]:
        """
        프론트엔드용 포맷으로 변환
        """
        return [{
            'text': num['text'],
            'start': num['start'],
            'end': num['end'],
            'needs_verification': num.get('needs_verification', False),
            'verified_value': num.get('verification', {}).get('verified'),
            'confidence': num.get('verification', {}).get('confidence'),
            'alternatives': num.get('verification', {}).get('alternatives', []),
            'reasoning': num.get('verification', {}).get('reasoning')
        } for num in verified_numbers]


# 싱글톤 인스턴스
number_verifier = NumberVerifier()

