"""FastAPI application entry point."""

import asyncio
import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi import Request
from fastapi.responses import JSONResponse

from app.services.auth import decode_access_token

# Fix for Windows: Use ProactorEventLoop for subprocess support (Playwright)
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

logger = logging.getLogger(__name__)
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.config import settings
from app.database import db
from app.pdf import close_pdf_renderer, init_pdf_renderer
from app.routers import admin_router, auth_router, config_router, enrichment_router, health_router, jobs_router, resumes_router


def _configure_application_logging() -> None:
    """Set application log level from configuration."""
    numeric_level = getattr(logging, settings.log_level, logging.INFO)
    logging.getLogger("app").setLevel(numeric_level)


_configure_application_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    # PDF renderer uses lazy initialization - will initialize on first use
    # await init_pdf_renderer()
    yield
    # Shutdown - wrap each cleanup in try-except to ensure all resources are released
    try:
        await close_pdf_renderer()
    except Exception as e:
        logger.error(f"Error closing PDF renderer: {e}")

    try:
        db.close()
    except Exception as e:
        logger.error(f"Error closing database: {e}")


app = FastAPI(
    title="Resume Matcher API",
    description="AI-powered resume tailoring for job descriptions",
    version=__version__,
    lifespan=lifespan,
)


@app.middleware("http")
async def enforce_user_llm_key(request: Request, call_next):
    """For selected LLM-backed endpoints, ensure `user` role has a personal
    per-user LLM API key configured before the request proceeds.

    This avoids starting a long-running LLM call only to fail later when the
    user's configuration is missing. Premium/admin roles continue using the
    shared key path and are not blocked here.
    """
    # Only protect the resume-improve endpoints that trigger LLM work
    protected_prefixes = (
        "/api/v1/resumes/improve",
    )

    path = request.url.path
    if any(path.startswith(p) for p in protected_prefixes):
        # Expect Bearer token to identify the user; forward other auth errors
        auth = request.headers.get("authorization")
        if not auth:
            return JSONResponse({"detail": "Authentication required"}, status_code=401)

        try:
            token = auth.split(" ", 1)[1] if " " in auth else auth
            payload = decode_access_token(token)
            user_id = payload.get("sub")
            if not user_id:
                return JSONResponse({"detail": "Invalid token payload"}, status_code=401)

            # Lazy import db to avoid import ordering issues at module import time
            from app.database import db

            user = db.get_user(str(user_id))
            if not user:
                return JSONResponse({"detail": "User not found"}, status_code=401)

            role = user.get("role", "user")
            if role == "user":
                # Check per-user LLM config for an api_key or provider-specific key
                user_llm = db.get_user_llm_config(str(user_id)) or {}
                api_key = user_llm.get("api_key") or ""
                # Also support an `api_keys` dict with provider keys
                if not api_key and isinstance(user_llm.get("api_keys"), dict):
                    # Check common mapping keys (openai/openai_compatible etc.)
                    api_key = next((v for v in user_llm.get("api_keys").values() if v), "")

                if not api_key:
                    return JSONResponse({"detail": "Per-user LLM API key required for this operation."}, status_code=403)

        except Exception as exc:  # pragma: no cover - error paths are simple
            return JSONResponse({"detail": "Authentication failed"}, status_code=401)

    return await call_next(request)

# CORS middleware - origins configurable via CORS_ORIGINS env var
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.effective_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(config_router, prefix="/api/v1")
app.include_router(resumes_router, prefix="/api/v1")
app.include_router(jobs_router, prefix="/api/v1")
app.include_router(enrichment_router, prefix="/api/v1")
app.include_router(admin_router, prefix="/api/v1")


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
