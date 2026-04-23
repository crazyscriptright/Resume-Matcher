"""FastAPI application entry point."""

import asyncio
import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI

# Fix for Windows: Use ProactorEventLoop for subprocess support (Playwright)
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

logger = logging.getLogger(__name__)
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.config import settings
from app.database import db as tinydb_instance
from app.db_adapter import TinyDBAdapter
from app.db import init_postgres_db, get_db_session
from app.db_postgres import PostgreSQLAdapter
from app.pdf import close_pdf_renderer, init_pdf_renderer
from app.routers import auth_router, config_router, enrichment_router, health_router, jobs_router, resumes_router
from app.services.llm_initializer import LLMDatabaseInitializer

# Global database adapter - will be initialized based on DATABASE_URL
db_adapter = None


def _configure_application_logging() -> None:
    """Set application log level from configuration."""
    numeric_level = getattr(logging, settings.log_level, logging.INFO)
    logging.getLogger("app").setLevel(numeric_level)


_configure_application_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    global db_adapter
    settings.data_dir.mkdir(parents=True, exist_ok=True)

    # Initialize database adapter based on DATABASE_URL
    if settings.is_postgres:
        logger.info("Initializing PostgreSQL adapter...")
        init_postgres_db()
        from app.db import _SessionLocal
        db_adapter = PostgreSQLAdapter(_SessionLocal)
        
        # Initialize LLM database for PostgreSQL
        try:
            from app.db import _engine as pg_engine
            llm_initializer = LLMDatabaseInitializer(pg_engine)
            llm_initializer.create_tables()
            
            # Load LLM config from .env
            with get_db_session() as db:
                models_loaded = llm_initializer.load_models_from_env(db)
                keys_loaded = llm_initializer.load_provider_keys_from_env(db)
                logger.info(f"✅ LLM Configuration: {models_loaded} models, {keys_loaded} API keys")
        except Exception as e:
            logger.error(f"⚠️ LLM initialization error: {e}")
    else:
        logger.info("Initializing TinyDB adapter...")
        db_adapter = TinyDBAdapter(tinydb_instance)
        logger.info("⚠️ LLM multi-model routing requires PostgreSQL (DATABASE_URL set)")

    # PDF renderer uses lazy initialization - will initialize on first use
    # await init_pdf_renderer()
    yield
    # Shutdown - wrap each cleanup in try-except to ensure all resources are released
    try:
        await close_pdf_renderer()
    except Exception as e:
        logger.error(f"Error closing PDF renderer: {e}")

    try:
        if db_adapter:
            db_adapter.close()
    except Exception as e:
        logger.error(f"Error closing database adapter: {e}")

    try:
        tinydb_instance.close()
    except Exception as e:
        logger.error(f"Error closing TinyDB: {e}")


app = FastAPI(
    title="Resume Matcher API",
    description="AI-powered resume tailoring for job descriptions",
    version=__version__,
    lifespan=lifespan,
)

# CORS middleware - origins configurable via CORS_ORIGINS env var
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.effective_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router, prefix="/api/v1")
app.include_router(health_router, prefix="/api/v1")
app.include_router(config_router, prefix="/api/v1")
app.include_router(resumes_router, prefix="/api/v1")
app.include_router(jobs_router, prefix="/api/v1")
app.include_router(enrichment_router, prefix="/api/v1")


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "Resume Matcher API",
        "version": __version__,
        "docs": "/docs",
    }


def main():
    """Entry point for the project.scripts console script."""
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
    )


if __name__ == "__main__":
    main()
