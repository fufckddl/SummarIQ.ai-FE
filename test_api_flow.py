#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_recording_flow():
    """전체 녹음 플로우 테스트"""
    
    print("="*60)
    print("🎯 녹음 플로우 테스트 시작")
    print("="*60)
    
    # 1단계: 녹음 시작 (제목 없이)
    print("\n1️⃣ 녹음 시작 (제목 미지정)...")
    response = requests.post(f"{BASE_URL}/stt/start")
    data = response.json()
    recording_id = data["recordingId"]
    print(f"✅ Recording ID: {recording_id}")
    
    # 2단계: 테스트용 헬퍼로 텍스트 추가
    print("\n2️⃣ 테스트용 텍스트 추가...")
    
    test_transcript = """오늘 회의에서는 신제품 출시 일정과 마케팅 전략에 대해 집중적으로 논의했습니다.
먼저 개발팀에서 현재 진행 상황을 보고했습니다. 베타 버전은 지난주에 내부 테스트를 완료했으며, 주요 버그 12건 중 10건이 수정되었다고 합니다.
디자인팀은 신규 로고와 런칭 페이지 시안을 공유했습니다. 브랜드 색상은 기존 블루 계열 대신 신뢰감 있는 민트 톤으로 변경하기로 결정했습니다.
마케팅팀에서는 런칭 캠페인을 SNS 중심으로 진행하되, 첫 주에는 인플루언서 협업보다는 사용자 리뷰 확보에 집중하자는 의견이 나왔습니다.
서비스 운영팀은 사용자 피드백 채널 통합 방안을 제안했습니다. 현재 슬랙, 이메일, 폼이 분산되어 있어 응답 속도가 느리다는 지적이 있었고, 이를 Notion + Zapier 자동 수집 시스템으로 통합하기로 했습니다.
마지막으로, 전체 일정은 10월 25일 런칭을 목표로 유지하되, QA 완료 시점이 늦어질 경우 3일 정도의 유예를 두기로 합의했습니다."""
    
    response = requests.post(
        f"{BASE_URL}/stt/test/add-transcript",
        data={
            "recordingId": recording_id,
            "transcript": test_transcript
        }
    )
    print(f"✅ 세그먼트 추가 완료: {response.json()['message']}")
    
    # 3단계: 녹음 종료 및 요약 생성 요청
    print("\n3️⃣ 녹음 종료 및 AI 요약 요청...")
    response = requests.post(
        f"{BASE_URL}/stt/commit",
        json={"recordingId": recording_id}
    )
    commit_data = response.json()
    print(f"✅ 상태: {commit_data['status']}")
    print(f"📝 전사된 텍스트: {commit_data['transcript'][:100]}...")
    
    # 4단계: 백그라운드 작업 완료 대기
    print("\n4️⃣ AI 제목 생성 및 요약 처리 중...")
    max_wait = 30  # 최대 30초 대기
    for i in range(max_wait):
        time.sleep(1)
        response = requests.get(f"{BASE_URL}/stt/recordings/{recording_id}")
        recording = response.json()
        
        if recording["status"] == "ready" and recording.get("summary"):
            print(f"✅ 처리 완료! ({i+1}초 소요)")
            break
        
        print(f"⏳ 대기 중... ({i+1}초)", end="\r")
    
    # 5단계: 최종 결과 확인
    print("\n\n5️⃣ 최종 결과 확인...")
    response = requests.get(f"{BASE_URL}/stt/recordings/{recording_id}")
    final_data = response.json()
    
    print("\n" + "="*60)
    print("📊 최종 결과")
    print("="*60)
    
    print(f"\n🏷️  AI 생성 제목: '{final_data['title']}'")
    print(f"\n📋 요약:\n{final_data.get('summary', 'N/A')}")
    
    if final_data.get('decisions'):
        print(f"\n🎯 의사결정 사항 ({len(final_data['decisions'])}개):")
        for i, decision in enumerate(final_data['decisions'], 1):
            print(f"  {i}. {decision}")
    
    if final_data.get('actions'):
        print(f"\n📝 액션 아이템 ({len(final_data['actions'])}개):")
        for i, action in enumerate(final_data['actions'], 1):
            print(f"  {i}. {action['task']}")
            if action.get('owner'):
                print(f"     담당자: {action['owner']}")
            if action.get('due'):
                print(f"     마감일: {action['due']}")
            print(f"     우선순위: {action['priority']}")
    
    print("\n" + "="*60)
    print("✅ 테스트 완료!")
    print("="*60)

if __name__ == "__main__":
    test_recording_flow()

