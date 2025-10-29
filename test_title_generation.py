#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import asyncio
from dotenv import load_dotenv
from services.summarizer import MeetingSummarizer

# 환경 변수 로드
load_dotenv()

# 테스트 회의 텍스트
test_transcript = """오늘 회의에서는 신제품 출시 일정과 마케팅 전략에 대해 집중적으로 논의했습니다.
먼저 개발팀에서 현재 진행 상황을 보고했습니다. 베타 버전은 지난주에 내부 테스트를 완료했으며, 주요 버그 12건 중 10건이 수정되었다고 합니다. 남은 2건은 결제 모듈 관련 API 응답 지연과 iOS 푸시 알림 실패 문제입니다. 두 이슈는 금주 내 해결을 목표로 하고 있습니다.

디자인팀은 신규 로고와 런칭 페이지 시안을 공유했습니다. 브랜드 색상은 기존 블루 계열 대신 신뢰감 있는 민트 톤으로 변경하기로 결정했습니다. 마케팅팀에서는 런칭 캠페인을 SNS 중심으로 진행하되, 첫 주에는 인플루언서 협업보다는 사용자 리뷰 확보에 집중하자는 의견이 나왔습니다. 또한, 프리런칭 이벤트로 "첫 가입자 500명 한정 프리미엄 기능 1개월 무료 제공" 프로모션을 진행하기로 했습니다.

서비스 운영팀은 사용자 피드백 채널 통합 방안을 제안했습니다. 현재 슬랙, 이메일, 폼이 분산되어 있어 응답 속도가 느리다는 지적이 있었고, 이를 "Notion + Zapier 자동 수집 시스템"으로 통합하기로 했습니다. 이로써 고객 요청이 실시간으로 태스크 보드에 등록될 예정입니다.

마지막으로, 전체 일정은 10월 25일 런칭을 목표로 유지하되, QA 완료 시점이 늦어질 경우 3일 정도의 유예를 두기로 합의했습니다. 다음 회의에서는 런칭 영상 콘셉트와 마케팅 문구 검토를 주요 안건으로 다루기로 했습니다."""

async def test_title_generation():
    try:
        print("🤖 AI 제목 생성 테스트 시작...")
        
        # 요약기 초기화
        summarizer = MeetingSummarizer()
        
        # 1단계: AI가 제목 생성
        ai_title = await summarizer.generate_meeting_title_from_content(test_transcript)
        
        print(f"\n✅ AI 생성 제목: '{ai_title}'")
        
        # 2단계: 생성된 제목으로 요약 생성
        result = await summarizer.summarize_and_extract(test_transcript, ai_title)
        
        print(f"\n📋 요약:")
        print(f"Summary: {result['summary']}")
        print(f"\n🎯 Decisions ({len(result['decisions'])}개):")
        for i, decision in enumerate(result['decisions'], 1):
            print(f"  {i}. {decision}")
        
        print(f"\n📝 Actions ({len(result['actions'])}개):")
        for i, action in enumerate(result['actions'], 1):
            print(f"  {i}. {action['task']}")
            if action['owner']:
                print(f"     담당자: {action['owner']}")
            if action['due']:
                print(f"     마감일: {action['due']}")
            print(f"     우선순위: {action['priority']}")
        
        return result
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    asyncio.run(test_title_generation())
