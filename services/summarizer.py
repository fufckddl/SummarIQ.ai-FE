"""
LLM 기반 회의 요약 및 액션 추출 서비스
"""
import os
from typing import List, Dict, Optional
from openai import OpenAI
import json

class MeetingSummarizer:
    """회의 요약 및 액션 추출"""
    
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    def generate_meeting_title_from_content_sync(self, transcript: str) -> str:
        """동기 버전 (Celery 워커용)"""
        import asyncio
        return asyncio.run(self.generate_meeting_title_from_content(transcript))
    
    def summarize_and_extract_sync(self, transcript: str, meeting_title: str = "회의") -> Dict:
        """동기 버전 (Celery 워커용)"""
        import asyncio
        return asyncio.run(self.summarize_and_extract(transcript, meeting_title))
    
    async def generate_meeting_title_from_content(self, transcript: str) -> str:
        """회의 내용으로부터 AI가 제목 생성"""
        
        prompt = f"""
다음 회의 내용을 분석하여 적절한 제목을 생성해주세요.

회의 내용:
{transcript}

제목 생성 가이드라인:
- 회의의 핵심 주제를 반영
- 20자 이내로 간결하게
- 구체적이고 명확하게
- 예: "신제품 출시 일정 논의", "사용자 피드백 채널 통합 방안", "사무실 시설 개선 요구사항"

제목만 반환 (따옴표 없이):
"""
        
        try:
            print(f"🤖 AI 제목 생성 시작...")
            
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "당신은 회의록 제목을 생성하는 전문가입니다. 회의 내용의 핵심을 파악하여 명확하고 구체적인 제목을 만들어주세요."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=50
            )
            
            title = response.choices[0].message.content.strip().replace('"', '').replace("'", '')
            print(f"✅ AI 제목 생성 완료: {title}")
            return title
            
        except Exception as e:
            print(f"❌ 제목 생성 오류: {e}")
            return "회의 요약"
        
    async def summarize_and_extract(
        self, 
        transcript: str,
        meeting_title: str = "회의",
        user_date: str = None
    ) -> Dict:
        """
        회의 전체 텍스트로부터 요약, 결정사항, 액션 추출
        
        Args:
            transcript: 전체 회의 텍스트
            meeting_title: 회의 제목
        
        Returns:
            {
                "meeting": {
                    "title": str,              # 노션 DB "제목"과 매핑
                    "participants": List[str], # "참석자"(multi_select)
                    "status": str              # "예정|진행중|완료"
                },
                "summary": str,
                "decisions": List[str],
                "actions": List[Dict]
            }
        """
        
        # 사용자 기기의 날짜 사용 (없으면 서버 날짜)
        from datetime import date, datetime
        if user_date:
            try:
                current_date = datetime.strptime(user_date, '%Y-%m-%d').date()
                print(f"📅 사용자 기기 날짜 사용: {user_date}")
            except:
                current_date = date.today()
                print(f"⚠️ 사용자 날짜 파싱 실패, 서버 날짜 사용: {current_date}")
        else:
            current_date = date.today()
            print(f"📅 서버 날짜 사용: {current_date}")
        
        # 요일 이름 (한국어)
        weekday_names = ['월요일', '화요일', '수요일', '목요일', '금요일', '토요일', '일요일']
        weekday_kr = weekday_names[current_date.weekday()]
        
        prompt = f"""
당신은 회의 내용을 분석하고 SummarIQ의 Notion 템플릿에 맞게 구조화하는 전문가입니다.

=== 현재 날짜 ===
{current_date.strftime('%Y-%m-%d')} ({weekday_kr})

=== 회의 제목(초기값) ===
{meeting_title}

=== 회의 전체 텍스트 ===
{transcript}
========================

아래 스키마에 '정확히' 맞춘 순수 JSON만 반환하세요(설명/마크다운/주석 금지).

스키마:
{{
  "meeting": {{
    "title": "최종 회의 제목(20자 내외, 구체적)",
    "participants": ["참석자1", "참석자2"],
    "status": "예정|진행중|완료|취소"
  }},
  "summary": "회의 핵심 요약 (3~5문장, 재구성)",
  "decisions": ["확정된 결정사항만"],
  "actions": [
    {{
      "task": "구체적 작업",
      "owner": "담당자 이름 또는 null",
      "due": "YYYY-MM-DD 또는 null",
      "priority": "high|medium|low"
    }}
  ],
  "questions_answers": [
    {{
      "question": "제기된 질문",
      "answer": "답변 내용 또는 null (미해결)",
      "asker": "질문자 이름 또는 null"
    }}
  ],
  "open_issues": [
    {{
      "issue": "미결 사항 설명",
      "context": "관련 맥락 또는 null",
      "priority": "high|medium|low"
    }}
  ],
  "key_insights": [
    {{
      "insight": "핵심 통찰 내용",
      "category": "기회|위험|패턴|제안",
      "confidence": "high|medium|low"
    }}
  ]
}}

지침:
- summary는 원문을 재구성(복붙 금지), 3~5문장
- decisions는 합의된 항목만
- actions는 실행 가능 문장, owner/due 있으면 채움
  * "다음 주", "내일", "이번 주 금요일" 등 상대적 날짜는 현재 날짜 기준으로 계산하여 YYYY-MM-DD 형식으로 변환
  * "10월 20일" → 연도 추가해서 YYYY-MM-DD로 변환
  * 날짜 언급 없으면 null
- **participants**: 실제 참석자 이름만 추출 (0~10명, 명확한 경우만)
- **status 판단 기준**:
  * "예정": 아직 시작 안 했거나, 계획/준비 단계인 내용 ("~할 예정", "다음 주 회의", "준비 중")
  * "진행중": 현재 진행 중이거나 논의 중인 내용 ("진행 중", "검토 중", "작업 중", "현재 ~하고 있음")
  * "완료": 이미 끝났거나 결론이 난 내용 (기본값, "완료했다", "결정했다", "끝났다", 과거형 표현)
  * "취소": 취소되거나 보류된 내용 ("취소", "보류", "중단", "무산")
- **questions_answers**: 회의 중 나온 질문과 답변만 추출 (없으면 빈 배열)
  * answer가 null이면 "미해결 질문"
  * 질문이 명확하지 않으면 생략
- **open_issues**: 결정되지 않았거나 추가 논의가 필요한 사항 (없으면 빈 배열)
  * 미결 사항이 명확할 때만 추가
  * priority는 맥락상 판단 (기본값: medium)
- **key_insights**: AI가 발견한 중요한 통찰/패턴/위험/기회 (0~3개)
  * 명확한 통찰이 있을 때만 추가
  * category: "기회" (새로운 기회), "위험" (잠재적 리스크), "패턴" (반복되는 패턴), "제안" (개선 제안)
  * confidence: AI의 확신도 (high/medium/low)
- 한국어로만 작성, 오직 JSON만 출력
"""

        try:
            print(f"🤖 OpenAI API 호출 시작...")
            print(f"📝 Transcript 길이: {len(transcript)} 문자")
            
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": """당신은 회의록을 전문적으로 작성하는 비서입니다.
                        
주요 역할:
1. 긴 회의 내용을 핵심만 추출하여 3-5문장으로 압축
2. 확정된 결정사항만 명확히 정리
3. 실행 가능한 액션 아이템 추출 (담당자, 마감일 포함)
원칙:
- 원문을 그대로 복사하지 말고 반드시 재구성할 것
- 중요하지 않은 잡담이나 인사말은 제외
- 핵심 논의 주제와 결론에 집중
- 구체적이고 실행 가능한 정보만 포함"""
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,  # 더 일관되고 정확한 태그 생성
                max_tokens=2000,  # 더 많은 태그 생성을 위해 증가
                response_format={"type": "json_object"}
            )
            
            print(f"✅ OpenAI API 응답 받음")
            raw_content = response.choices[0].message.content
            print(f"📝 OpenAI 원본 응답:\n{raw_content}")
            
            result = json.loads(raw_content)
            print(f"🔍 파싱된 결과: {json.dumps(result, ensure_ascii=False, indent=2)}")

            # 최소 필드 보정
            if "meeting" not in result:
                print("⚠️ meeting 필드가 없음 - 기본값 추가")
                result["meeting"] = {}
            meeting_obj = result["meeting"]
            meeting_obj.setdefault("title", meeting_title or "회의")
            meeting_obj.setdefault("participants", [])
            # status는 AI가 판단하도록, 없으면 "완료"로 폴백
            meeting_obj.setdefault("status", "완료")

            result.setdefault("summary", "")
            result.setdefault("decisions", [])
            result.setdefault("actions", [])
            result.setdefault("questions_answers", [])
            result.setdefault("open_issues", [])
            result.setdefault("key_insights", [])

            print(f"✅ 최종 결과 - participants: {result['meeting']['participants']}")
            print(f"✅ 1단계 필드 - Q&A: {len(result.get('questions_answers', []))}개, 미결: {len(result.get('open_issues', []))}개, 인사이트: {len(result.get('key_insights', []))}개")
            return result
            
        except Exception as e:
            print(f"❌ Summarization error: {e}")
            print(f"❌ Error type: {type(e)}")
            import traceback
            traceback.print_exc()
            # 폴백: 기본 구조 반환 (AI 판단 실패 시 기본값 "완료")
            return {
                "meeting": {
                    "title": meeting_title or "회의",
                    "participants": [],
                    "tags": [],
                    "status": "완료"  # AI 판단 실패 시 기본값
                },
                "summary": transcript[:500] + "..." if len(transcript) > 500 else transcript,
                "decisions": [],
                "actions": [],
                "questions_answers": [],
                "open_issues": [],
                "key_insights": []
            }
    
    async def extract_key_topics(self, transcript: str) -> List[str]:
        """주요 키워드/토픽 추출"""
        
        prompt = f"""
다음 회의 내용에서 주요 키워드/주제를 5개 이하로 추출해주세요.

{transcript}

JSON 배열 형식으로만 반환:
["키워드1", "키워드2", ...]
"""
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            return result.get("keywords", [])
            
        except Exception as e:
            print(f"Keyword extraction error: {e}")
            return []
    
    async def generate_meeting_title(self, transcript: str) -> str:
        """회의 내용으로부터 제목 생성"""
        
        prompt = f"""
다음 회의 내용의 핵심을 한 문장으로 요약한 제목을 만들어주세요.

{transcript[:1000]}

제목만 반환 (20자 이내):
"""
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.5,
                max_tokens=50
            )
            
            title = response.choices[0].message.content.strip()
            return title[:50]  # 최대 50자
            
        except Exception as e:
            print(f"Title generation error: {e}")
            return "회의 요약"
    
    def suggest_tags(self, transcript: str, summary: str = None) -> list:
        """
        AI가 내용 기반으로 태그 추천
        
        Args:
            transcript: 회의 전사 텍스트
            summary: 회의 요약 (선택)
            
        Returns:
            추천 태그 리스트 (최대 5개)
        """
        # 요약과 전사 텍스트 모두 활용 (더 정확한 컨텍스트)
        content_parts = []
        if summary:
            content_parts.append(f"[요약]\n{summary}")
        if transcript:
            content_parts.append(f"[전사 텍스트]\n{transcript[:1500]}")
        
        content = "\n\n".join(content_parts)
        
        prompt = f"""다음 회의 내용을 분석하여 회의의 핵심 주제와 맥락을 가장 잘 나타내는 태그 3-5개를 추천해주세요.

{content}

**태그 선택 가이드라인:**
1. 회의의 실제 주제와 내용을 반영하는 태그를 우선 선택
2. 구체적이고 의미 있는 태그 (너무 일반적인 태그 지양)
3. 다음 카테고리를 참고하되, 내용에 더 적합한 커스텀 태그도 가능:

**카테고리 예시:**
- 회의 유형: 기획회의, 개발미팅, 디자인리뷰, 팀회의, 고객미팅, 브레인스토밍, 1on1, 전사회의, 스탠드업, 회고
- 프로젝트/업무: 프로젝트명, 스프린트, 릴리즈, 기능개발, 버그픽스, 성능개선, 리팩토링
- 주제/도메인: 마케팅, 제품, 기술, 인사, 재무, 영업, 고객지원, 교육, 연구
- 산업/분야: 실제 회의에서 다룬 구체적 산업이나 분야 (예: 네일아트, 뷰티, 헬스케어 등)

**중요:** 회의 내용에 명시적으로 언급되지 않은 카테고리는 추천하지 마세요.

태그만 배열로 반환 (JSON 형식):
["태그1", "태그2", "태그3"]
"""
        
        try:
            print(f"🤖 AI 태그 추천 시작...")
            print(f"📝 전달된 컨텍스트 (첫 500자):\n{content[:500]}...")
            
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=100
            )
            
            result = response.choices[0].message.content.strip()
            print(f"🤖 AI 응답: {result}")
            
            # JSON 마크다운 제거 (```json ... ``` 형식)
            import json
            import re
            
            # ```json ... ``` 또는 ``` ... ``` 패턴 제거
            cleaned_result = re.sub(r'^```(?:json)?\s*\n?', '', result)
            cleaned_result = re.sub(r'\n?```\s*$', '', cleaned_result)
            cleaned_result = cleaned_result.strip()
            
            print(f"🧹 정리된 응답: {cleaned_result}")
            
            tags = json.loads(cleaned_result)
            
            # 빈 태그 제거 및 # 제거
            cleaned_tags = []
            for tag in tags:
                if isinstance(tag, str):
                    cleaned = tag.strip().replace('#', '')
                    if cleaned:
                        cleaned_tags.append(cleaned)
            
            print(f"✅ AI 추천 태그: {cleaned_tags}")
            
            # 최대 5개로 제한
            return cleaned_tags[:5]
            
        except Exception as e:
            print(f"❌ AI 태그 추천 실패: {e}")
            import traceback
            traceback.print_exc()
            return []  # 빈 배열 반환 (기본 태그 제거)

