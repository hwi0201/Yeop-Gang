# dh: Rate Limiting 미들웨어 추가
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ai.routers import router as ai_router
from api.routers import router as api_router
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
        # dh: 새로운 모델들도 초기화 (Student, CourseEnrollment)
        from core.dh_models import Student, CourseEnrollment
        init_db()

    return app


app = create_app()

