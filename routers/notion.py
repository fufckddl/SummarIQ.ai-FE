"""
Notion 연동 라우터
"""
from fastapi import APIRouter, HTTPException, Depends, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List, Dict
import os

from database.connection import get_db
from database import crud, notion_crud
from database.notion_crud import get_notion_connection, update_notion_default_target
from services.jwt_service import JWTService
from services.notion_service import NotionService


router = APIRouter(prefix="/notion", tags=["Notion"])
jwt_service = JWTService()


# ==================== Request Models ====================

class SetTargetRequest(BaseModel):
    target_type: str  # 'database' or 'page'
    target_id: str
    target_name: Optional[str] = None
    as_default: bool = True


class UploadSummaryRequest(BaseModel):
    recording_id: str
    target_type: Optional[str] = None  # 지정하지 않으면 기본 대상 사용
    target_id: Optional[str] = None


# ==================== Helper Functions ====================

def get_current_user_id(request: Request) -> int:
    """요청에서 user_id 추출 (필수)"""
    try:
        authorization = request.headers.get("Authorization")
        if not authorization:
            raise HTTPException(status_code=401, detail="로그인이 필요합니다")
        
        token = authorization.replace("Bearer ", "")
        user_id = jwt_service.get_user_id_from_token(token)
        
        if not user_id:
            raise HTTPException(status_code=401, detail="유효하지 않은 토큰입니다")
        
        return user_id
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ JWT 토큰 검증 오류: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=401, detail="토큰 검증 실패")


# ==================== OAuth ====================

@router.get("/oauth/start")
async def start_notion_oauth(request: Request):
    """
    Notion OAuth 시작 (브라우저로 리다이렉트)
    
    https://api.notion.com/v1/oauth/authorize?
      client_id={CLIENT_ID}&
      response_type=code&
      owner=user&
      redirect_uri={REDIRECT_URI}
    """
    user_id = get_current_user_id(request)
    
    client_id = os.getenv("NOTION_CLIENT_ID")
    redirect_uri = os.getenv("NOTION_REDIRECT_URI", "http://localhost:8000/notion/oauth/callback")
    
    if not client_id:
        raise HTTPException(status_code=500, detail="Notion OAuth가 설정되지 않았습니다")
    
    # OAuth URL 생성 (URL 인코딩 적용)
    from urllib.parse import urlencode, quote
    
    params = {
        "client_id": client_id,
        "response_type": "code",
        "owner": "user",
        "redirect_uri": redirect_uri,
        "state": f"user_{user_id}"  # 더 명확한 문자열 형식
    }
    
    auth_url = f"https://api.notion.com/v1/oauth/authorize?{urlencode(params)}"
    
    return {
        "authUrl": auth_url,
        "message": "브라우저에서 Notion 로그인을 완료하세요"
    }


@router.get("/oauth/callback")
async def notion_oauth_callback(
    code: str,
    state: str,  # user_id
    db: Session = Depends(get_db)
):
    """
    Notion OAuth 콜백
    
    Args:
        code: Authorization code
        state: user_id
    """
    try:
        # state 형식: "user_{user_id}"
        if state.startswith("user_"):
            user_id = int(state.replace("user_", ""))
        else:
            user_id = int(state)  # 하위 호환성
        
        client_id = os.getenv("NOTION_CLIENT_ID")
        client_secret = os.getenv("NOTION_CLIENT_SECRET")
        redirect_uri = os.getenv("NOTION_REDIRECT_URI", "http://localhost:8000/notion/oauth/callback")
        
        if not client_id or not client_secret:
            raise HTTPException(status_code=500, detail="Notion OAuth가 설정되지 않았습니다")
        
        # Access token 교환
        import httpx
        import base64
        
        auth_string = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.notion.com/v1/oauth/token",
                headers={
                    "Authorization": f"Basic {auth_string}",
                    "Content-Type": "application/json"
                },
                json={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": redirect_uri
                }
            )
            
            if response.status_code != 200:
                raise Exception(f"Notion OAuth 실패: {response.status_code} {response.text}")
            
            data = response.json()
        
        # 토큰 및 워크스페이스 정보 추출
        access_token = data["access_token"]
        workspace_id = data.get("workspace_id")
        workspace_name = data.get("workspace_name")
        bot_id = data.get("bot_id")
        
        # 토큰 암호화 및 저장
        notion_service = NotionService()
        encrypted_token = notion_service._encrypt_token(access_token)
        
        notion_crud.create_or_update_notion_connection(
            db,
            user_id=user_id,
            access_token_enc=encrypted_token,
            workspace_id=workspace_id,
            workspace_name=workspace_name,
            bot_id=bot_id
        )
        
        print(f"✅ Notion 연동 완료: user_id={user_id}, workspace={workspace_name}")
        
        # 성공 페이지로 리다이렉트 (앱에서 딥링크로 처리)
        return {
            "success": True,
            "message": "Notion 연동이 완료되었습니다!",
            "workspaceName": workspace_name
        }
        
    except Exception as e:
        print(f"❌ Notion OAuth 콜백 실패: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"OAuth 실패: {str(e)}")


# ==================== 연결 상태 ====================

@router.get("/status")
async def get_notion_status(
    request: Request,
    db: Session = Depends(get_db)
):
    """Notion 연결 상태 조회"""
    user_id = get_current_user_id(request)
    
    connection = notion_crud.get_notion_connection(db, user_id)
    
    if not connection:
        return {
            "connected": False,
            "message": "Notion에 연결되지 않았습니다"
        }
    
    return connection.to_dict()


@router.delete("/disconnect")
async def disconnect_notion(
    request: Request,
    db: Session = Depends(get_db)
):
    """Notion 연동 해제"""
    user_id = get_current_user_id(request)
    
    success = notion_crud.delete_notion_connection(db, user_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="연결된 Notion이 없습니다")
    
    print(f"✅ Notion 연동 해제: user_id={user_id}")
    return {"message": "Notion 연동이 해제되었습니다"}


# ==================== 대상 검색/설정 ====================

@router.get("/search")
async def search_notion_targets(
    request: Request,
    q: str = "",
    type: str = None,
    db: Session = Depends(get_db)
):
    """
    Notion 페이지/데이터베이스 검색
    
    Args:
        q: 검색어
        type: 'database' 또는 'page'
    """
    user_id = get_current_user_id(request)
    
    # Notion 연결 확인
    connection = notion_crud.get_notion_connection(db, user_id)
    if not connection:
        raise HTTPException(status_code=404, detail="Notion에 연결되지 않았습니다. 먼저 연결하세요.")
    
    # 토큰 복호화
    notion_service = NotionService()
    access_token = notion_service.decrypt_token(connection.access_token_enc)
    notion_service.access_token = access_token
    
    # Notion 검색
    try:
        results = await notion_service.search(query=q, filter_type=type)
        
        # 결과 포맷팅
        formatted_results = []
        for item in results:
            formatted_results.append({
                "id": item["id"],
                "type": item["object"],  # 'database' or 'page'
                "title": _extract_title(item),
                "url": item.get("url"),
                "icon": item.get("icon")
            })
        
        return {"results": formatted_results}
        
    except Exception as e:
        print(f"❌ Notion 검색 실패: {e}")
        raise HTTPException(status_code=500, detail=f"검색 실패: {str(e)}")


@router.post("/target")
async def set_default_target(
    body: SetTargetRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """기본 업로드 대상 설정"""
    user_id = get_current_user_id(request)
    
    # Notion 연결 확인
    connection = notion_crud.get_notion_connection(db, user_id)
    if not connection:
        raise HTTPException(status_code=404, detail="Notion에 연결되지 않았습니다")
    
    # 기본 대상 설정
    success = notion_crud.update_default_target(
        db,
        user_id=user_id,
        target_type=body.target_type,
        target_id=body.target_id,
        target_name=body.target_name
    )
    
    if not success:
        raise HTTPException(status_code=500, detail="대상 설정 실패")
    
    print(f"✅ 기본 대상 설정: user_id={user_id}, type={body.target_type}, id={body.target_id}")
    
    return {
        "message": "기본 대상이 설정되었습니다",
        "targetType": body.target_type,
        "targetId": body.target_id,
        "targetName": body.target_name
    }


# ==================== 요약 업로드 ====================

@router.post("/upload-summary")
async def upload_summary_to_notion(
    body: UploadSummaryRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    회의 요약을 Notion에 업로드
    """
    user_id = get_current_user_id(request)
    
    # Notion 연결 확인
    connection = notion_crud.get_notion_connection(db, user_id)
    if not connection:
        raise HTTPException(status_code=404, detail="Notion에 연결되지 않았습니다")
    
    # 녹음 조회
    recording = crud.get_recording_with_details(db, body.recording_id)
    if not recording:
        raise HTTPException(status_code=404, detail="녹음을 찾을 수 없습니다")
    
    # 권한 확인
    if recording.get("userId") != user_id:
        raise HTTPException(status_code=403, detail="본인의 녹음만 업로드할 수 있습니다")
    
    # 대상 결정
    target_type = body.target_type or connection.default_target_type
    target_id = body.target_id or connection.default_target_id
    
    if not target_id:
        raise HTTPException(status_code=400, detail="업로드 대상이 설정되지 않았습니다")
    
    # 업로드 이력 생성
    upload = notion_crud.create_notion_upload(
        db,
        user_id=user_id,
        recording_id=body.recording_id,
        target_type=target_type,
        target_id=target_id,
        status='pending'
    )
    
    try:
        # Notion 서비스 초기화
        notion_service = NotionService()
        access_token = notion_service.decrypt_token(connection.access_token_enc)
        notion_service.access_token = access_token
        
        # 회의 데이터 준비
        meeting_data = {
            "title": recording.get("title", "회의 요약"),
            "summary": recording.get("summary", ""),
            "decisions": recording.get("decisions", []),
            "actions": recording.get("actions", []),
            "started_at": recording.get("createdAt"),
        }
        
        # Notion에 업로드
        print(f"📤 Notion 업로드 시작: {target_type}/{target_id}")
        result = await notion_service.upload_meeting_summary(
            target_type=target_type,
            target_id=target_id,
            meeting_data=meeting_data
        )
        
        # 성공 상태 업데이트
        notion_crud.update_notion_upload_status(
            db,
            upload_id=upload.id,
            status='success',
            notion_page_id=result["page_id"],
            notion_page_url=result["page_url"]
        )
        
        print(f"✅ Notion 업로드 완료: {result['page_url']}")
        
        return {
            "success": True,
            "message": "Notion에 업로드되었습니다",
            "notionPageUrl": result["page_url"],
            "notionPageId": result["page_id"]
        }
        
    except Exception as e:
        # 실패 상태 업데이트
        notion_crud.update_notion_upload_status(
            db,
            upload_id=upload.id,
            status='failed',
            error_message=str(e)
        )
        
        print(f"❌ Notion 업로드 실패: {e}")
        
        # 403 에러면 권한 안내
        if "403" in str(e) or "Forbidden" in str(e):
            raise HTTPException(
                status_code=403,
                detail="Notion 봇을 해당 데이터베이스/페이지에 초대해주세요"
            )
        
        raise HTTPException(status_code=500, detail=f"업로드 실패: {str(e)}")


# ==================== Helper Functions ====================

def _extract_title(notion_object: Dict) -> str:
    """Notion 객체에서 제목 추출"""
    try:
        if notion_object["object"] == "database":
            title_prop = notion_object.get("title", [])
            if title_prop:
                return title_prop[0].get("plain_text", "제목 없음")
        elif notion_object["object"] == "page":
            properties = notion_object.get("properties", {})
            for prop_name, prop_value in properties.items():
                if prop_value.get("type") == "title":
                    title_list = prop_value.get("title", [])
                    if title_list:
                        return title_list[0].get("plain_text", "제목 없음")
        
        return "제목 없음"
    except:
        return "제목 없음"


@router.post("/create-database")
async def create_meeting_database(
    request: Request,
    db: Session = Depends(get_db)
):
    """회의록용 데이터베이스 자동 생성"""
    try:
        user_id = get_current_user_id(request)
        
        # 사용자의 Notion 연결 정보 조회
        notion_connection = get_notion_connection(db, user_id)
        if not notion_connection:
            raise HTTPException(status_code=400, detail="Notion이 연결되지 않았습니다")
        
        # Notion 서비스 초기화
        notion_service = NotionService(notion_connection.access_token_enc)
        
        # 데이터베이스 생성
        result = await notion_service.create_meeting_database(
            database_title="회의록"
        )
        
        # 생성된 데이터베이스를 기본 대상으로 설정
        update_notion_default_target(
            db, 
            user_id,
            default_target_type="database",
            default_target_id=result["database_id"],
            default_target_name=result["title"]
        )
        
        return {
            "success": True,
            "message": "회의록 데이터베이스가 생성되고 기본 대상으로 설정되었습니다",
            "database_id": result["database_id"],
            "database_url": result["database_url"],
            "title": result["title"]
        }
        
    except Exception as e:
        print(f"❌ 데이터베이스 생성 실패: {e}")
        raise HTTPException(status_code=500, detail=f"데이터베이스 생성 실패: {str(e)}")


@router.post("/extract-template")
async def extract_page_template(
    request: Request,
    page_url: str,
    db: Session = Depends(get_db)
):
    """Notion 페이지에서 템플릿 구조 추출"""
    try:
        user_id = get_current_user_id(request)
        
        # 사용자의 Notion 연결 정보 조회
        notion_connection = get_notion_connection(db, user_id)
        if not notion_connection:
            raise HTTPException(status_code=400, detail="Notion이 연결되지 않았습니다")
        
        # Notion 서비스 초기화
        notion_service = NotionService(notion_connection.access_token_enc)
        
        # 템플릿 추출
        result = await notion_service.get_page_template(page_url)
        
        return {
            "success": True,
            "message": "템플릿 구조를 성공적으로 추출했습니다",
            "template": result
        }
        
    except Exception as e:
        print(f"❌ 템플릿 추출 실패: {e}")
        raise HTTPException(status_code=500, detail=f"템플릿 추출 실패: {str(e)}")


@router.get("/templates")
async def get_predefined_templates():
    """미리 정의된 템플릿 목록 조회"""
    try:
        notion_service = NotionService()
        templates = notion_service.get_predefined_templates()
        
        return {
            "success": True,
            "templates": templates
        }
        
    except Exception as e:
        print(f"❌ 템플릿 목록 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"템플릿 목록 조회 실패: {str(e)}")


@router.post("/auto-upload-summary")
async def auto_upload_summary(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    회의 요약 자동 업로드 (액션 아이템 체크 상태 포함)
    - 첫 업로드: 회의목록 데이터베이스 생성
    - 이후: 기존 데이터베이스에 항목 추가
    """
    try:
        user_id = get_current_user_id(request)
        
        # 요청 본문에서 recording_id와 completed_action_indices 추출
        body = await request.json()
        recording_id = body.get("recording_id")
        completed_action_indices = body.get("completed_action_indices", [])
        
        if not recording_id:
            raise HTTPException(status_code=400, detail="recording_id가 필요합니다")
        
        # 1. 사용자의 Notion 연결 정보 조회
        notion_connection = get_notion_connection(db, user_id)
        if not notion_connection:
            raise HTTPException(status_code=400, detail="Notion이 연결되지 않았습니다")
        
        # 2. 녹음 정보 조회
        from database.crud import get_recording
        recording = get_recording(db, recording_id)
        if not recording or recording.user_id != user_id:
            raise HTTPException(status_code=404, detail="녹음을 찾을 수 없습니다")
        
        # 3. Notion 서비스 초기화
        notion_service = NotionService(notion_connection.access_token_enc)
        
        # 4. 회의목록 데이터베이스 ID 확인
        meeting_list_db_id = notion_connection.default_target_id
        
        # 첫 업로드인 경우: 회의목록 데이터베이스 생성
        if not meeting_list_db_id or notion_connection.default_target_type != "database":
            print("📝 첫 업로드: 회의목록 데이터베이스 생성 중...")
            
            # 템플릿 복제 대신 기본 데이터베이스 생성
            db_result = await notion_service.create_meeting_database(
                database_title="회의목록"
            )
            
            meeting_list_db_id = db_result["database_id"]
            
            # 기본 대상으로 설정
            update_notion_default_target(
                db,
                user_id,
                default_target_type="database",
                default_target_id=meeting_list_db_id,
                default_target_name="회의목록"
            )
            
            print(f"✅ 회의목록 데이터베이스 생성 완료: {meeting_list_db_id}")
        
        # 5. 회의 데이터 준비
        meeting_data = {
            "title": recording.title or "회의",
            "date": recording.created_at.isoformat() if recording.created_at else None,
            "participants": recording.participants if recording.participants else [],
            "tags": recording.tags if recording.tags else [],
            "status": recording.meeting_status or "완료"
        }
        
        # 6. 요약 데이터 준비 (액션 아이템 체크 상태 반영)
        decisions_list = [dec.decision for dec in recording.decisions] if recording.decisions else []
        
        # 액션 아이템에 체크 상태 적용
        actions_list = []
        if recording.actions:
            for i, act in enumerate(recording.actions):
                action_dict = act.to_dict()
                # 완료된 액션 아이템 인덱스에 포함되어 있으면 completed=True
                action_dict['completed'] = i in completed_action_indices
                actions_list.append(action_dict)
        
        print(f"📋 액션 아이템 체크 상태 적용: {len(completed_action_indices)}개 완료")
        
        summary_content = {
            "summary": recording.summary or "요약 없음",
            "decisions": decisions_list,
            "actions": actions_list,
            "questions_answers": recording.questions_answers if recording.questions_answers else [],
            "open_issues": recording.open_issues if recording.open_issues else [],
            "key_insights": recording.key_insights if recording.key_insights else []
        }
        
        # 7. 회의 항목 + 요약 페이지 생성
        result = await notion_service.create_meeting_entry_with_summary(
            database_id=meeting_list_db_id,
            meeting_data=meeting_data,
            summary_content=summary_content
        )
        
        # 8. 업로드 기록 저장
        from database.notion_crud import create_notion_upload
        upload_record = create_notion_upload(
            db,
            user_id=user_id,
            recording_id=recording_id,
            target_type="database",
            target_id=meeting_list_db_id,
            notion_page_id=result["page_id"],
            notion_page_url=result["page_url"],
            status="success"
        )
        
        # 📬 푸시 알림 전송 (Notion 업로드 완료 알림)
        from models.user import User
        from services.notification_helper import notify_notion_upload_complete
        
        user = db.query(User).filter(User.id == user_id).first()
        if user and (user.fcm_token or user.push_token):
            try:
                import asyncio
                asyncio.create_task(notify_notion_upload_complete(
                    user_id=user.id,
                    fcm_token=user.fcm_token,
                    push_token=user.push_token,
                    platform=user.platform,
                    recording_title=recording.title or "회의",
                    notion_page_url=result["page_url"]
                ))
                print(f"📬 Notion upload notification sent to user {user_id}")
            except Exception as notif_error:
                print(f"⚠️ Failed to send Notion upload notification: {notif_error}")
        
        return {
            "success": True,
            "message": "회의 요약이 Notion에 업로드되었습니다",
            "page_url": result["page_url"],
            "database_id": meeting_list_db_id
        }
        
    except Exception as e:
        print(f"❌ 자동 업로드 실패: {e}")
        
        # 실패 기록 저장
        try:
            from database.notion_crud import create_notion_upload
            create_notion_upload(
                db,
                user_id=user_id,
                recording_id=recording_id,
                target_type="database",
                target_id=meeting_list_db_id if 'meeting_list_db_id' in locals() else None,
                notion_page_id=None,
                status="failed",
                error_message=str(e)
            )
        except:
            pass
        
        raise HTTPException(status_code=500, detail=f"자동 업로드 실패: {str(e)}")

