import sys
from pathlib import Path
from contextlib import asynccontextmanager

# Ensure project root (FinLens) is in sys.path so 'backend' package is resolvable
# regardless of the working directory or execution method (e.g. VS Code 'Run' button)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.chat import router as chat_router
from backend.app.api.documents import router as documents_router
from backend.app.api.kpis import router as kpis_router
from backend.app.api.profile import router as profile_router
from backend.app.api.recommendations import router as recommendations_router
from backend.app.api.research import router as research_router
from backend.app.config import settings
from backend.app.database.connection import check_db_health, init_db
from backend.app.utils.logger import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events: startup and shutdown."""
    logger.info(f"Starting up {settings.APP_NAME} v{settings.APP_VERSION}...")
    try:
        await init_db()
        logger.info("Database initialized successfully on startup.")

        # Seed baseline verified financial research dataset
        from backend.app.data.company_data import seed_company_data
        from backend.app.data.mutual_fund_data import seed_mutual_fund_data
        from backend.app.database.connection import AsyncSessionLocal
        async with AsyncSessionLocal() as session:
            await seed_company_data(session)
            await seed_mutual_fund_data(session)
        logger.info("Financial research data layer initialized.")
    except Exception as e:
        logger.warning(f"Could not auto-initialize DB tables on startup: {e}")
    yield
    logger.info("FinLens application shut down gracefully.")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "Production-grade RAG-based financial intelligence and investment research platform. "
        "Compliant with deterministic candidate scoring and verifiable source citations."
    ),
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API v1 routers
app.include_router(documents_router, prefix="/api/v1")
app.include_router(kpis_router, prefix="/api/v1")
app.include_router(chat_router, prefix="/api/v1")
app.include_router(recommendations_router, prefix="/api/v1")
app.include_router(profile_router, prefix="/api/v1")
app.include_router(research_router, prefix="/api/v1")


from fastapi import HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

@app.get("/api/v1/health", tags=["Health"])
async def health_check():
    """System health check endpoint returning status of database and AI services."""
    db_ok = await check_db_health()
    return {
        "status": "healthy" if db_ok else "degraded",
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "database_connected": db_ok,
        "vector_store_backend": settings.VECTOR_STORE_BACKEND,
        "active_llm_provider": settings.LLM_PROVIDER,
        "active_llm_model": getattr(settings, f"{settings.LLM_PROVIDER.upper()}_MODEL", "default"),
        "disclaimer": (
            "This application provides educational/research information and is not "
            "personalized financial advice or a guarantee of investment returns."
        )
    }


@app.get("/api/v1/status", tags=["Root"])
async def api_status():
    """Root entrypoint returning application status."""
    return {
        "status": "online",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs_url": "/docs"
    }


# Mount and serve compiled React frontend if available
FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist"
if (FRONTEND_DIST / "index.html").exists():
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIST / "assets")), name="assets")

    @app.get("/", include_in_schema=False)
    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str = ""):
        # Never intercept API or Swagger documentation routes
        if full_path.startswith("api/") or full_path in ("docs", "redoc", "openapi.json"):
            raise HTTPException(status_code=404, detail="Endpoint not found")
        target_file = FRONTEND_DIST / full_path
        if full_path and target_file.exists() and target_file.is_file():
            return FileResponse(str(target_file))
        return FileResponse(str(FRONTEND_DIST / "index.html"))
else:
    @app.get("/", tags=["Root"])
    async def root():
        """Root entrypoint returning application status."""
        return {
            "status": "online",
            "app": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "docs_url": "/docs"
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)

