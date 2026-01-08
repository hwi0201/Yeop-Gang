# dh: Rate Limiting 미들웨어 추가
from pathlib import Path
import os
import shutil

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ai.routers import router as ai_router
from api.routers import router as api_router
from api.dh_routers import router as dh_router
from core.db import init_db
from core.dh_rate_limit import RateLimitMiddleware


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.
    Routers are split so backend A (ai) and backend B (api) can work independently.
    """
    # Load environment variables from project root .env before settings are instantiated
    try:
        project_root = Path(__file__).resolve().parent.parent  # .../server -> project root
        env_path = project_root / ".env"
        load_dotenv(dotenv_path=env_path)
    except Exception:
        # Ignore .env read errors (permission or missing); rely on process env instead
        pass

    app = FastAPI(title="Yeop-Gang API", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # dh: Rate Limiting 미들웨어 추가
    app.add_middleware(
        RateLimitMiddleware,
        max_requests=100,  # 시간당 최대 요청 수
        window_seconds=3600,  # 1시간
    )

    app.include_router(api_router, prefix="/api")
    app.include_router(ai_router, prefix="/ai")
    app.include_router(dh_router, prefix="/api")  # dh_routers의 엔드포인트들도 /api 접두사 사용

    @app.get("/")
    def root():
        return {
            "message": "옆강 (Yeop-Gang) API",
            "version": "0.1.0",
            "docs": "/docs",
            "health": "/api/health",
        }

    @app.on_event("startup")
    def _startup() -> None:
        # ffmpeg 경로를 환경 변수에 추가 (whisper 라이브러리가 사용)
        ffmpeg_path = shutil.which("ffmpeg")
        
        # PATH에서 찾지 못하면 일반적인 설치 경로 확인
        if not ffmpeg_path:
            possible_paths = [
                r"C:\ffmpeg\bin\ffmpeg.exe",
                r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
                r"C:\Program Files (x86)\ffmpeg\bin\ffmpeg.exe",
                r"C:\Users\HWI\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.0.1-full_build\bin\ffmpeg.exe",
            ]
            for path in possible_paths:
                if Path(path).exists():
                    ffmpeg_path = path
                    print(f"✅ Found ffmpeg at: {ffmpeg_path}")
                    break
        
        if ffmpeg_path:
            ffmpeg_path = str(Path(ffmpeg_path).resolve())
            ffmpeg_dir = str(Path(ffmpeg_path).parent)
            current_path = os.environ.get("PATH", "")
            if ffmpeg_dir not in current_path:
                os.environ["PATH"] = ffmpeg_dir + os.pathsep + current_path
                print(f"✅ Added ffmpeg to PATH: {ffmpeg_dir}")
        else:
            print("⚠️ Warning: ffmpeg not found in PATH. Whisper STT may fail.")
            print("💡 Please install ffmpeg: https://ffmpeg.org/download.html")
        
        # dh: 새로운 모델들도 초기화 (Student, CourseEnrollment)
        from core.dh_models import Student, CourseEnrollment
        init_db()

    return app


app = create_app()

