from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import stt, auth, notion, upload, notifications, fcm, audio_enhancement, user_settings, teams, subscriptions, tags, stats, users, teams_api, notifications_api, announcements, inquiries
from dotenv import load_dotenv
import os

# 모든 모델 import (SQLAlchemy 관계 해결을 위해)
from models import *

# 환경 변수 로드
load_dotenv()

# FastAPI 앱 생성
app = FastAPI(
    title="SummarIQ API",
    version="1.0.0",
    description="AI 회의 비서 - 하이브리드 녹음 및 AI 요약 API"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(stt.router)
app.include_router(auth.router)
app.include_router(notion.router)
app.include_router(upload.router)
app.include_router(notifications.router)
app.include_router(fcm.router)
app.include_router(audio_enhancement.router)
app.include_router(user_settings.router)
app.include_router(teams.router)
app.include_router(subscriptions.router)
app.include_router(tags.router)
app.include_router(stats.router)
app.include_router(users.router)
app.include_router(teams_api.router)
app.include_router(notifications_api.router)
app.include_router(announcements.router)
app.include_router(inquiries.router)


@app.get("/")
def root():
    """루트 엔드포인트"""
    return {
        "message": "SummarIQ API Server",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health")
def health_check():
    """헬스 체크"""
    return {
        "status": "healthy",
        "google_credentials": os.path.exists(
            os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")
        )
    }


if __name__ == "__main__":
    import uvicorn
    
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", 8000))
    
    print(f"🚀 Starting SummarIQ API Server on {host}:{port}")
    print(f"📖 API Docs: http://{host}:{port}/docs")
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=True
    )

