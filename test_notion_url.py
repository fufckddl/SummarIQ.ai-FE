#!/usr/bin/env python
"""Notion OAuth URL 테스트"""
import sys
sys.path.insert(0, '/Users/dlckdfuf/Desktop/SummarIQ/backend')

from services.jwt_service import JWTService
import requests
from urllib.parse import urlparse, parse_qs

# 토큰 생성
jwt = JWTService()
token = jwt.create_access_token(1, 'test@example.com')

print('🔐 테스트용 JWT 토큰 생성 완료')
print()

# API 호출
try:
    response = requests.get(
        'http://192.168.0.166:8000/notion/oauth/start',
        headers={'Authorization': f'Bearer {token}'},
        timeout=5
    )
    
    print(f'✅ 응답 상태: {response.status_code}')
    
    if response.status_code == 200:
        data = response.json()
        auth_url = data['authUrl']
        
        print('✅ OAuth URL 생성 성공')
        print()
        print('📋 전체 URL:')
        print(auth_url)
        print()
        
        # URL 파싱
        parsed = urlparse(auth_url)
        params = parse_qs(parsed.query)
        
        print('📊 파라미터 분석:')
        for key, value in params.items():
            print(f'  {key}: {value[0]}')
        
        print()
        print('🔍 state 파라미터 상세:')
        state_value = params['state'][0]
        print(f'  값: "{state_value}"')
        print(f'  타입: {type(state_value).__name__}')
        print(f'  길이: {len(state_value)}')
        print(f'  repr: {repr(state_value)}')
        print(f'  ASCII: {[ord(c) for c in state_value]}')
        
    else:
        print(f'❌ 에러 응답:')
        print(response.json())
        
except Exception as e:
    print(f'❌ 에러 발생: {e}')
    import traceback
    traceback.print_exc()

