"""
Certifica — FastAPI Application Entrypoint.

Hub multi-tenant de preparação para certificações Databricks (simulados +
flashcards), com banco em Postgres (Lakebase/RDS) e geração de questões via
Foundation Model API.
"""
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.config import get_settings
from app.api import certifications, tests, generate, auth, tracking, tenants

logging.basicConfig(
    level=getattr(logging, get_settings().LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

limiter = Limiter(key_func=get_remote_address, default_limits=["300/minute"])
STATIC_DIR = Path(__file__).parent.parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    s = get_settings()
    logger.info(f"{s.APP_NAME} iniciando em modo {'MOCK' if s.MOCK_MODE else 'DB'}")
    if not s.MOCK_MODE:
        try:
            from app.db import is_db_ready
            logger.info(f"Postgres pronto: {is_db_ready()}")
        except Exception as e:
            logger.warning(f"Postgres não inicializou: {e}")
        if s.SEED_ON_STARTUP:
            try:
                from seed.seed_db import run_seed
                logger.info("SEED_ON_STARTUP=true — semeando schema/dados (idempotente)...")
                run_seed()
            except Exception as e:
                logger.warning(f"Seed no startup falhou: {e}")
    yield
    logger.info(f"{s.APP_NAME} encerrando")


def create_app() -> FastAPI:
    s = get_settings()
    app = FastAPI(
        title=s.APP_NAME,
        description="Multi-tenant hub for Databricks certification prep",
        version="1.0.0",
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=s.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
    app.include_router(tenants.router, prefix="/api", tags=["tenants"])
    app.include_router(certifications.router, prefix="/api/certifications", tags=["certifications"])
    app.include_router(tests.router, prefix="/api/tests", tags=["tests"])
    app.include_router(generate.router, prefix="/api/generate", tags=["generate"])
    app.include_router(tracking.router, prefix="/api", tags=["tracking"])

    @app.get("/api/health")
    async def health():
        return {
            "status": "ok",
            "mode": "mock" if s.MOCK_MODE else "lakebase",
            "llm_endpoint": s.LLM_ENDPOINT,
            "version": "1.0.0",
        }

    # Serve React SPA (produção)
    if STATIC_DIR.exists():
        assets_dir = STATIC_DIR / "assets"
        if assets_dir.exists():
            app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

        @app.get("/{full_path:path}")
        async def spa_catch_all(request: Request, full_path: str):
            if full_path.startswith("api/"):
                return JSONResponse({"error": "Not found"}, status_code=404)
            # arquivos estáticos da raiz (logo, favicon, etc.)
            if full_path:
                candidate = (STATIC_DIR / full_path).resolve()
                if candidate.is_file() and str(candidate).startswith(str(STATIC_DIR.resolve())):
                    return FileResponse(str(candidate))
            index = STATIC_DIR / "index.html"
            if index.exists():
                return FileResponse(str(index))
            return JSONResponse({"error": "Frontend não encontrado"}, status_code=404)
    else:
        logger.warning("Static não encontrado — apenas API disponível")

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8005, reload=True)
