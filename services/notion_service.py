"""
Notion API 서비스
"""
import os
import httpx
from typing import Dict, List, Optional
from cryptography.fernet import Fernet

class NotionService:
    def __init__(self, access_token_enc: str = None):
        """
        Notion API 서비스 초기화
        
        Args:
            access_token_enc: 암호화된 액세스 토큰 (옵션)
        """
        self.base_url = "https://api.notion.com/v1"
        self.notion_version = "2022-06-28"
        
        # 암호화 키 설정
        encryption_key = os.getenv("ENCRYPTION_KEY") or os.getenv("NOTION_ENCRYPTION_KEY")
        if not encryption_key:
            raise ValueError("ENCRYPTION_KEY 또는 NOTION_ENCRYPTION_KEY 환경 변수가 설정되지 않았습니다")
        
        self.cipher = Fernet(encryption_key.encode())
        
        # 토큰이 제공된 경우 복호화
        if access_token_enc:
            try:
                self.access_token = self._decrypt_token(access_token_enc)
            except Exception as e:
                print(f"❌ 토큰 복호화 실패: {e}")
                raise
        else:
            self.access_token = None
    
    def _encrypt_token(self, token: str) -> str:
        """토큰 암호화"""
        return self.cipher.encrypt(token.encode()).decode()
    
    def _decrypt_token(self, encrypted_token: str) -> str:
        """토큰 복호화"""
        return self.cipher.decrypt(encrypted_token.encode()).decode()
    
    def _get_headers(self) -> Dict:
        """Notion API 요청 헤더 생성"""
        if not self.access_token:
            raise ValueError("Access token이 설정되지 않았습니다")
        
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Notion-Version": self.notion_version,
            "Content-Type": "application/json"
        }
    
    async def exchange_code_for_token(self, code: str, redirect_uri: str) -> Dict:
        """
        OAuth code를 access token으로 교환
        
        Args:
            code: OAuth authorization code
            redirect_uri: 리다이렉트 URI
        
        Returns:
            토큰 정보
        """
        client_id = os.getenv("NOTION_CLIENT_ID")
        client_secret = os.getenv("NOTION_CLIENT_SECRET")
        
        if not client_id or not client_secret:
            raise ValueError("Notion OAuth 설정이 없습니다")
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.notion.com/v1/oauth/token",
                headers={
                    "Authorization": f"Basic {self._get_basic_auth(client_id, client_secret)}",
                    "Content-Type": "application/json"
                },
                json={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": redirect_uri
                },
                timeout=30.0
            )
            
            if response.status_code != 200:
                raise Exception(f"토큰 교환 실패: {response.status_code} {response.text}")
            
            data = response.json()
            
            # 토큰 암호화
            access_token = data.get("access_token")
            access_token_enc = self._encrypt_token(access_token)
            
            return {
                "access_token_enc": access_token_enc,
                "workspace_id": data.get("workspace_id"),
                "workspace_name": data.get("workspace_name"),
                "bot_id": data.get("bot_id")
            }
    
    def _get_basic_auth(self, client_id: str, client_secret: str) -> str:
        """Basic Auth 헤더 생성"""
        import base64
        credentials = f"{client_id}:{client_secret}"
        return base64.b64encode(credentials.encode()).decode()
    
    async def search_notion(
        self,
        query: str = "",
        filter_type: str = None
    ) -> Dict:
        """
        Notion에서 페이지/데이터베이스 검색
        
        Args:
            query: 검색 쿼리
            filter_type: 필터 타입 ('database' 또는 'page')
        
        Returns:
            검색 결과
        """
        async with httpx.AsyncClient() as client:
            payload = {}
            
            if query:
                payload["query"] = query
            
            if filter_type:
                payload["filter"] = {
                    "property": "object",
                    "value": filter_type
                }
            
            response = await client.post(
                f"{self.base_url}/search",
                headers=self._get_headers(),
                json=payload,
                timeout=30.0
            )
            
            if response.status_code != 200:
                raise Exception(f"Notion 검색 실패: {response.status_code} {response.text}")
            
            data = response.json()
            results = []
            
            for item in data.get("results", []):
                result = {
                    "id": item.get("id"),
                    "type": item.get("object"),
                    "url": item.get("url")
                }
                
                # 제목 추출
                if item.get("object") == "database":
                    title_list = item.get("title", [])
                    result["title"] = title_list[0].get("plain_text", "제목 없음") if title_list else "제목 없음"
                elif item.get("object") == "page":
                    properties = item.get("properties", {})
                    for prop_name, prop_value in properties.items():
                        if prop_value.get("type") == "title":
                            title_list = prop_value.get("title", [])
                            result["title"] = title_list[0].get("plain_text", "제목 없음") if title_list else "제목 없음"
                            break
                    else:
                        result["title"] = "제목 없음"
                
                results.append(result)
            
            return {"results": results}
    
    def build_meeting_properties(
        self,
        title: str,
        started_at: str = None,
        participants: List[str] = None,
        tags: List[str] = None
    ) -> Dict:
        """
        회의 페이지 속성 생성
        
        Returns:
            Notion properties 딕셔너리
        """
        properties = {
            "제목": {
                "title": [{"text": {"content": title}}]
            }
        }
        
        if started_at:
            # 날짜 속성은 date 타입으로 처리
            properties["날짜"] = {
                "date": {"start": started_at}
            }
        
        if participants:
            properties["참석자"] = {
                "multi_select": [{"name": p} for p in participants]
            }
        
        if tags:
            properties["태그"] = {
                "multi_select": [{"name": t} for t in tags]
            }
        
        return properties
    
    async def create_page(
        self,
        parent_id: str,
        parent_type: str,
        properties: Dict,
        content_blocks: List[Dict] = None
    ) -> Dict:
        """
        Notion 페이지 생성
        
        Args:
            parent_id: 부모 ID (database_id 또는 page_id)
            parent_type: 부모 타입 ('database' 또는 'page')
            properties: 페이지 속성
            content_blocks: 페이지 내용 블록들
        
        Returns:
            생성된 페이지 정보
        """
        async with httpx.AsyncClient() as client:
            payload = {
                "parent": {
                    f"{parent_type}_id": parent_id
                },
                "properties": properties
            }
            
            if content_blocks:
                payload["children"] = content_blocks
            
            response = await client.post(
                f"{self.base_url}/pages",
                headers=self._get_headers(),
                json=payload,
                timeout=30.0
            )
            
            if response.status_code != 200:
                raise Exception(f"Notion 페이지 생성 실패: {response.status_code} {response.text}")
            
            data = response.json()
            return {
                "page_id": data.get("id"),
                "url": data.get("url")
            }
    
    def build_summary_blocks(
        self,
        summary: str = None,
        decisions: List[str] = None,
        actions: List[Dict] = None
    ) -> List[Dict]:
        """
        요약 콘텐츠를 Notion 블록으로 변환
        
        Returns:
            Notion blocks 리스트
        """
        blocks = []
        
        # 요약
        if summary:
            blocks.append({
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"type": "text", "text": {"content": "요약"}}]
                }
            })
            blocks.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": summary}}]
                }
            })
        
        # 결정사항
        if decisions:
            blocks.append({
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"type": "text", "text": {"content": "결정사항"}}]
                }
            })
            for decision in decisions:
                blocks.append({
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {
                        "rich_text": [{"type": "text", "text": {"content": decision}}]
                    }
                })
        
        # 액션 아이템
        if actions:
            blocks.append({
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"type": "text", "text": {"content": "액션 아이템"}}]
                }
            })
            for action in actions:
                task_text = action.get("task", "")
                if action.get("owner"):
                    task_text += f" (담당: {action['owner']})"
                if action.get("due"):
                    task_text += f" [마감: {action['due']}]"
                
                blocks.append({
                    "object": "block",
                    "type": "to_do",
                    "to_do": {
                        "rich_text": [{"type": "text", "text": {"content": task_text}}],
                        "checked": False
                    }
                })
        
        return blocks
    
    async def append_blocks(
        self,
        page_id: str,
        blocks: List[Dict]
    ) -> Dict:
        """
        페이지에 블록 추가
        
        Args:
            page_id: 페이지 ID
            blocks: 추가할 블록 리스트
        
        Returns:
            결과
        """
        async with httpx.AsyncClient() as client:
            response = await client.patch(
                f"{self.base_url}/blocks/{page_id}/children",
                headers=self._get_headers(),
                json={"children": blocks},
                timeout=30.0
            )
            
            if response.status_code != 200:
                raise Exception(f"블록 추가 실패: {response.status_code} {response.text}")
            
            return {"success": True}
    
    async def create_meeting_database(
        self,
        parent_page_id: str = None,
        database_title: str = "회의록"
    ) -> Dict:
        """
        회의록용 데이터베이스 자동 생성
        
        Args:
            parent_page_id: 부모 페이지 ID (없으면 루트에 생성)
            database_title: 데이터베이스 제목
        
        Returns:
            생성된 데이터베이스 정보
        """
        async with httpx.AsyncClient() as client:
            # 부모 페이지 설정
            if parent_page_id:
                parent = {"page_id": parent_page_id}
            else:
                # 사용자의 루트 페이지를 찾아서 사용
                # 먼저 사용자가 접근 가능한 페이지를 검색
                search_response = await client.post(
                    f"{self.base_url}/search",
                    headers=self._get_headers(),
                    json={"filter": {"property": "object", "value": "page"}},
                    timeout=30.0
                )
                
                if search_response.status_code != 200:
                    raise Exception(f"페이지 검색 실패: {search_response.status_code} {search_response.text}")
                
                search_data = search_response.json()
                pages = search_data.get("results", [])
                
                if not pages:
                    raise Exception("사용자가 접근 가능한 페이지가 없습니다. Notion에서 페이지를 생성해주세요.")
                
                # 첫 번째 페이지를 부모로 사용
                parent = {"page_id": pages[0]["id"]}
            
            # 데이터베이스 속성 정의
            properties = {
                "제목": {
                    "title": {}
                },
                "날짜": {
                    "date": {}
                },
                "참석자": {
                    "multi_select": {}
                },
                "태그": {
                    "multi_select": {}
                },
                "상태": {
                    "select": {
                        "options": [
                            {"name": "예정", "color": "blue"},
                            {"name": "진행중", "color": "yellow"},
                            {"name": "완료", "color": "green"},
                            {"name": "취소", "color": "red"}
                        ]
                    }
                },
                "중요도": {
                    "select": {
                        "options": [
                            {"name": "낮음", "color": "gray"},
                            {"name": "보통", "color": "blue"},
                            {"name": "높음", "color": "red"},
                            {"name": "긴급", "color": "red"}
                        ]
                    }
                },
                "소요시간": {
                    "number": {"format": "number"}
                },
                "생성일": {
                    "created_time": {}
                }
            }
            
            payload = {
                "parent": parent,
                "title": [
                    {
                        "type": "text",
                        "text": {"content": database_title}
                    }
                ],
                "properties": properties,
                "description": [
                    {
                        "type": "text",
                        "text": {"content": "SummarIQ에서 자동 생성된 회의록 데이터베이스입니다."}
                    }
                ]
            }
            
            response = await client.post(
                f"{self.base_url}/databases",
                headers=self._get_headers(),
                json=payload,
                timeout=30.0
            )
            
            if response.status_code != 200:
                raise Exception(f"데이터베이스 생성 실패: {response.status_code} {response.text}")
            
            data = response.json()
            return {
                "database_id": data.get("id"),
                "database_url": data.get("url"),
                "title": data.get("title", [{}])[0].get("plain_text", database_title),
                "success": True
            }
    
    async def get_page_template(self, page_url: str) -> Dict:
        """
        Notion 페이지에서 템플릿 구조 추출
        
        Args:
            page_url: Notion 페이지 URL
        
        Returns:
            페이지 템플릿 정보
        """
        # URL에서 페이지 ID 추출
        import re
        page_id_match = re.search(r'notion\.so/(?:[^\/]+\/)?([a-f0-9\-]+)', page_url)
        if not page_id_match:
            raise ValueError("올바른 Notion URL이 아닙니다")
        
        page_id = page_id_match.group(1)
        
        async with httpx.AsyncClient() as client:
            # 페이지 정보 조회
            page_response = await client.get(
                f"{self.base_url}/pages/{page_id}",
                headers=self._get_headers(),
                timeout=30.0
            )
            
            if page_response.status_code != 200:
                raise Exception(f"페이지 조회 실패: {page_response.status_code} {page_response.text}")
            
            page_data = page_response.json()
            
            # 페이지 블록 조회
            blocks_response = await client.get(
                f"{self.base_url}/blocks/{page_id}/children",
                headers=self._get_headers(),
                timeout=30.0
            )
            
            if blocks_response.status_code != 200:
                raise Exception(f"블록 조회 실패: {blocks_response.status_code} {blocks_response.text}")
            
            blocks_data = blocks_response.json()
            
            # 템플릿 구조 분석
            template_structure = self._analyze_template_structure(blocks_data.get("results", []))
            
            return {
                "page_id": page_id,
                "page_url": page_url,
                "page_title": self._extract_page_title(page_data),
                "template_structure": template_structure,
                "blocks_count": len(blocks_data.get("results", [])),
                "success": True
            }
    
    def _extract_page_title(self, page_data: Dict) -> str:
        """페이지 제목 추출"""
        try:
            properties = page_data.get("properties", {})
            for prop_name, prop_value in properties.items():
                if prop_value.get("type") == "title":
                    title_list = prop_value.get("title", [])
                    if title_list:
                        return title_list[0].get("plain_text", "제목 없음")
            return "제목 없음"
        except:
            return "제목 없음"
    
    def _analyze_template_structure(self, blocks: List[Dict]) -> Dict:
        """템플릿 구조 분석"""
        structure = {
            "headings": [],
            "paragraphs": [],
            "lists": [],
            "tables": [],
            "callouts": [],
            "other_blocks": []
        }
        
        for block in blocks:
            block_type = block.get("type")
            
            if block_type == "heading_1":
                structure["headings"].append({
                    "level": 1,
                    "text": self._extract_block_text(block, "heading_1")
                })
            elif block_type == "heading_2":
                structure["headings"].append({
                    "level": 2,
                    "text": self._extract_block_text(block, "heading_2")
                })
            elif block_type == "heading_3":
                structure["headings"].append({
                    "level": 3,
                    "text": self._extract_block_text(block, "heading_3")
                })
            elif block_type == "paragraph":
                structure["paragraphs"].append({
                    "text": self._extract_block_text(block, "paragraph")
                })
            elif block_type in ["bulleted_list_item", "numbered_list_item"]:
                structure["lists"].append({
                    "type": block_type,
                    "text": self._extract_block_text(block, block_type)
                })
            elif block_type == "table":
                structure["tables"].append({
                    "text": "테이블"
                })
            elif block_type == "callout":
                structure["callouts"].append({
                    "text": self._extract_block_text(block, "callout")
                })
            else:
                structure["other_blocks"].append({
                    "type": block_type,
                    "text": self._extract_block_text(block, block_type)
                })
        
        return structure
    
    def _extract_block_text(self, block: Dict, block_type: str) -> str:
        """블록에서 텍스트 추출"""
        try:
            block_content = block.get(block_type, {})
            rich_text = block_content.get("rich_text", [])
            if rich_text:
                return rich_text[0].get("plain_text", "")
            return ""
        except:
            return ""
    
    def get_predefined_templates(self) -> Dict:
        """미리 정의된 템플릿 목록 반환"""
        return {
            "meeting_list": {
                "name": "회의목록",
                "description": "회의 목록을 관리하는 데이터베이스 템플릿",
                "url": "https://summariq.notion.site/28bf6d107d45806581e0dc018d9e1d09",
                "page_id": "28bf6d10-7d45-8065-81e0-dc018d9e1d09",
                "type": "database",
                "features": ["회의 일정", "참석자", "상태 관리", "태그 분류"]
            },
            "meeting_summary": {
                "name": "회의요약",
                "description": "회의 내용을 요약하는 페이지 템플릿",
                "url": "https://summariq.notion.site/28bf6d107d4580838236d22855c83522",
                "page_id": "28bf6d10-7d45-8083-8236-d22855c83522",
                "type": "page",
                "features": ["회의 개요", "주요 논의사항", "결정사항", "다음 단계"]
            },
            "action_board": {
                "name": "액션 아이템 보드",
                "description": "액션 아이템을 관리하는 칸반 보드 템플릿",
                "url": "https://summariq.notion.site/28bf6d107d458009979ad8fdf8fa0aee",
                "page_id": "28bf6d10-7d45-8009-979a-d8fdf8fa0aee",
                "type": "database",
                "features": ["할 일", "진행중", "완료", "담당자", "우선순위"]
            }
        }
    
    async def duplicate_template_database(
        self,
        template_page_id: str,
        database_title: str = "회의목록"
    ) -> Dict:
        """
        템플릿 데이터베이스를 사용자 워크스페이스에 복제
        
        Args:
            template_page_id: 템플릿 페이지 ID
            database_title: 새 데이터베이스 제목
        
        Returns:
            복제된 데이터베이스 정보
        """
        async with httpx.AsyncClient() as client:
            # 1. 템플릿 페이지 정보 조회
            template_response = await client.get(
                f"{self.base_url}/pages/{template_page_id}",
                headers=self._get_headers(),
                timeout=30.0
            )
            
            if template_response.status_code != 200:
                raise Exception(f"템플릿 조회 실패: {template_response.status_code} {template_response.text}")
            
            # 2. 사용자의 루트 페이지 찾기
            search_response = await client.post(
                f"{self.base_url}/search",
                headers=self._get_headers(),
                json={"filter": {"property": "object", "value": "page"}},
                timeout=30.0
            )
            
            if search_response.status_code != 200:
                raise Exception(f"페이지 검색 실패: {search_response.status_code} {search_response.text}")
            
            search_data = search_response.json()
            pages = search_data.get("results", [])
            
            if not pages:
                raise Exception("사용자가 접근 가능한 페이지가 없습니다. Notion에서 페이지를 생성해주세요.")
            
            parent = {"page_id": pages[0]["id"]}
            
            # 3. 회의목록 데이터베이스 생성 (템플릿과 동일한 구조)
            properties = {
                "제목": {
                    "title": {}
                },
                "날짜": {
                    "date": {}
                },
                "참석자": {
                    "multi_select": {}
                },
                "태그": {
                    "multi_select": {}
                },
                "상태": {
                    "select": {
                        "options": [
                            {"name": "예정", "color": "blue"},
                            {"name": "진행중", "color": "yellow"},
                            {"name": "완료", "color": "green"},
                            {"name": "취소", "color": "red"}
                        ]
                    }
                },
                "회의 요약": {
                    "rich_text": {}  # 일단 rich_text로 URL 저장
                }
            }
            
            payload = {
                "parent": parent,
                "title": [
                    {
                        "type": "text",
                        "text": {"content": database_title}
                    }
                ],
                "properties": properties,
                "description": [
                    {
                        "type": "text",
                        "text": {"content": "SummarIQ에서 자동 생성된 회의목록 데이터베이스입니다."}
                    }
                ]
            }
            
            response = await client.post(
                f"{self.base_url}/databases",
                headers=self._get_headers(),
                json=payload,
                timeout=30.0
            )
            
            if response.status_code != 200:
                raise Exception(f"데이터베이스 복제 실패: {response.status_code} {response.text}")
            
            data = response.json()
            return {
                "database_id": data.get("id"),
                "database_url": data.get("url"),
                "title": data.get("title", [{}])[0].get("plain_text", database_title),
                "success": True
            }
    
    async def create_meeting_entry_with_summary(
        self,
        database_id: str,
        meeting_data: Dict,
        summary_content: Dict
    ) -> Dict:
        """
        회의목록 데이터베이스에 항목 추가 + 회의요약 페이지 생성
        
        Args:
            database_id: 회의목록 데이터베이스 ID
            meeting_data: 회의 정보 (title, date, participants, tags)
            summary_content: 요약 내용 (summary, decisions, actions)
        
        Returns:
            생성된 페이지 정보
        """
        # 디버깅: meeting_data 확인
        print(f"📊 Notion 업로드 데이터:")
        print(f"  - 제목: {meeting_data.get('title')}")
        print(f"  - 참석자: {meeting_data.get('participants')}")
        print(f"  - 태그: {meeting_data.get('tags')}")
        print(f"  - 상태: {meeting_data.get('status')}")
        
        async with httpx.AsyncClient() as client:
            # 1. 회의요약 페이지 먼저 생성 (데이터베이스 항목의 자식으로)
            summary_page_payload = {
                "parent": {"database_id": database_id},
                "properties": {
                    "제목": {
                        "title": [{"text": {"content": meeting_data.get("title", "회의")}}]
                    },
                    "날짜": {
                        "date": {"start": meeting_data.get("date")} if meeting_data.get("date") else None
                    },
                    "참석자": {
                        "multi_select": [{"name": p} for p in meeting_data.get("participants", [])]
                    },
                    "태그": {
                        "multi_select": [{"name": t} for t in meeting_data.get("tags", [])]
                    },
                    "상태": {
                        "select": {"name": meeting_data.get("status", "완료")}
                    }
                },
                "children": self._build_summary_blocks(summary_content)
            }
            
            print(f"📤 Notion API 전송 데이터:")
            print(f"  - 참석자 multi_select: {summary_page_payload['properties']['참석자']}")
            print(f"  - 태그 multi_select: {summary_page_payload['properties']['태그']}")
            
            # None 값 제거
            if summary_page_payload["properties"]["날짜"]["date"] is None:
                del summary_page_payload["properties"]["날짜"]
            
            response = await client.post(
                f"{self.base_url}/pages",
                headers=self._get_headers(),
                json=summary_page_payload,
                timeout=30.0
            )
            
            print(f"🔍 Notion API 응답 상태: {response.status_code}")
            
            if response.status_code != 200:
                error_detail = response.text
                print(f"❌ Notion API 에러 응답: {error_detail}")
                raise Exception(f"회의 항목 생성 실패: {response.status_code} {error_detail}")
            
            data = response.json()
            
            # 생성된 페이지의 실제 속성 확인
            created_properties = data.get("properties", {})
            print(f"✅ Notion 페이지 생성 완료:")
            print(f"  - 페이지 ID: {data.get('id')}")
            print(f"  - 참석자 속성: {created_properties.get('참석자', {})}")
            print(f"  - 태그 속성: {created_properties.get('태그', {})}")
            
            return {
                "page_id": data.get("id"),
                "page_url": data.get("url"),
                "success": True
            }
    
    def _build_summary_blocks(self, summary_content: Dict) -> List[Dict]:
        """회의요약 페이지 블록 생성"""
        blocks = []
        
        # 회의 요약
        if summary_content.get("summary"):
            blocks.append({
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"type": "text", "text": {"content": "📋 회의 요약"}}]
                }
            })
            blocks.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": summary_content["summary"]}}]
                }
            })
        
        # 주요 결정사항
        if summary_content.get("decisions"):
            blocks.append({
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"type": "text", "text": {"content": "✅ 주요 결정사항"}}]
                }
            })
            for decision in summary_content["decisions"]:
                blocks.append({
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {
                        "rich_text": [{"type": "text", "text": {"content": decision}}]
                    }
                })
        
        # 액션 아이템
        if summary_content.get("actions"):
            blocks.append({
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"type": "text", "text": {"content": "🎯 액션 아이템"}}]
                }
            })
            for action in summary_content["actions"]:
                task_text = action.get("task", "")
                if action.get("owner"):
                    task_text += f" (담당: {action['owner']})"
                if action.get("due"):
                    task_text += f" [마감: {action['due']}]"
                
                # 체크 상태 반영 (completed 필드 확인)
                is_checked = action.get("completed", False)
                
                blocks.append({
                    "object": "block",
                    "type": "to_do",
                    "to_do": {
                        "rich_text": [{"type": "text", "text": {"content": task_text}}],
                        "checked": is_checked
                    }
                })
        
        # Q&A
        if summary_content.get("questions_answers"):
            blocks.append({
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"type": "text", "text": {"content": "❓ 질문 & 답변"}}]
                }
            })
            for qa in summary_content["questions_answers"]:
                qa_text = f"Q. {qa.get('question', '')}"
                if qa.get("answer"):
                    qa_text += f"\nA. {qa['answer']}"
                else:
                    qa_text += "\nA. (미해결)"
                
                blocks.append({
                    "object": "block",
                    "type": "callout",
                    "callout": {
                        "rich_text": [{"type": "text", "text": {"content": qa_text}}],
                        "icon": {"emoji": "💬"}
                    }
                })
        
        # 미결 사항
        if summary_content.get("open_issues"):
            blocks.append({
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"type": "text", "text": {"content": "⏳ 미결 사항"}}]
                }
            })
            for issue in summary_content["open_issues"]:
                issue_text = issue.get("issue", "")
                if issue.get("priority"):
                    priority_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(issue["priority"], "⚪")
                    issue_text = f"{priority_emoji} {issue_text}"
                if issue.get("context"):
                    issue_text += f"\n└ {issue['context']}"
                
                blocks.append({
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {
                        "rich_text": [{"type": "text", "text": {"content": issue_text}}]
                    }
                })
        
        # 핵심 인사이트
        if summary_content.get("key_insights"):
            blocks.append({
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"type": "text", "text": {"content": "💡 핵심 인사이트"}}]
                }
            })
            for insight in summary_content["key_insights"]:
                category = insight.get("category", "제안")
                confidence = insight.get("confidence", "medium")
                insight_text = insight.get("insight", "")
                
                # 카테고리별 이모지
                category_emoji = {
                    "기회": "🟢",
                    "위험": "🔴",
                    "패턴": "🔵",
                    "제안": "🟡"
                }.get(category, "⚪")
                
                # 확신도 표시
                confidence_text = {
                    "high": "높음",
                    "medium": "보통",
                    "low": "낮음"
                }.get(confidence, "보통")
                
                full_text = f"{category_emoji} [{category}] {insight_text}\n└ 확신도: {confidence_text}"
                
                blocks.append({
                    "object": "block",
                    "type": "callout",
                    "callout": {
                        "rich_text": [{"type": "text", "text": {"content": full_text}}],
                        "icon": {"emoji": "💡"},
                        "color": "blue_background" if confidence == "high" else "gray_background"
                    }
                })
        
        return blocks
