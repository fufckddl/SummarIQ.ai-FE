"""
인증 Dependency 함수
"""
from fastapi import Request, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import Dict

from database.connection import get_db
from services.jwt_service import JWTService

jwt_service = JWTService()


async def get_current_user(
    request: Request,
    db: Session = Depends(get_db)
) -> Dict:
    """
    현재 로그인한 사용자 정보 반환 (Dependency)
    
    Returns:
        {"id": user_id, "email": email, ...}
    """
    try:
        # Authorization 헤더에서 토큰 추출
        authorization = request.headers.get("Authorization")
        if not authorization:
            raise HTTPException(status_code=401, detail="Authorization 헤더가 필요합니다")
        
        token = authorization.replace("Bearer ", "")
        
        print(f"🔐 토큰 검증 시작... (토큰 길이: {len(token)})")
        
        # 토큰에서 user_id 추출
        user_id = jwt_service.get_user_id_from_token(token)
        
        print(f"🔐 토큰에서 추출된 user_id: {user_id}")
        
        if not user_id:
            print("❌ 토큰이 유효하지 않거나 만료되었습니다")
            raise HTTPException(status_code=401, detail="유효하지 않은 토큰입니다")
        
        # DB에서 사용자 조회
        from database import auth_crud
        user = auth_crud.get_user_by_id(db, user_id)
        
        if not user:
            raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다")
        
        # 사용자 정보 반환
        return user.to_dict()
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 인증 실패: {e}")
        raise HTTPException(status_code=401, detail="인증에 실패했습니다")

