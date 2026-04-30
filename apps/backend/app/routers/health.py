"""Health check and status endpoints."""

from fastapi import APIRouter, Depends

from app.database import db
from app.llm import LLMConfig, check_llm_health, get_llm_config
from app.schemas import HealthResponse, StatusResponse
from app.services.auth import get_current_user, is_shared_llm_role

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Lightweight liveness check for Docker HEALTHCHECK.

    Does NOT call the LLM provider. Use GET /status for full LLM health.
    """
    return HealthResponse(status="healthy")


@router.get("/status", response_model=StatusResponse)
async def get_status(user: dict = Depends(get_current_user)) -> StatusResponse:
    """Get comprehensive application status (user-specific).

    Returns:
        - LLM configuration status (role-aware)
        - Master resume existence
        - User-specific database statistics
    
    For admin/premium users: checks shared LLM config from settings/Firestore.
    For normal users: checks their own user-specific API key only.
    """
    # Load global/stored config (may include shared keys)
    stored_config = get_llm_config()
    db_stats = db.get_stats(user_id=str(user["user_id"]))

    # Determine role and build the effective config used for health checks
    user_role = str(user.get("role", "user"))
    if is_shared_llm_role(user_role):
        # Admin/Premium users use the shared/global config
        health_config = stored_config
        llm_configured = bool(stored_config.api_key) or stored_config.provider == "ollama"
    else:
        # Normal users: derive a config from any per-user overlay.
        # If the user hasn't set their own API key, ensure api_key is blank
        user_config = db.get_user_llm_config(str(user["user_id"])) or {}
        health_config = LLMConfig(
            provider=user_config.get("provider", stored_config.provider),
            model=stored_config.model,
            api_key=user_config.get("api_key", "") or "",
            api_base=user_config.get("api_base", stored_config.api_base),
            reasoning_effort=user_config.get("reasoning_effort", stored_config.reasoning_effort),
        )
        llm_configured = bool(user_config.get("api_key")) or (user_config.get("provider") == "ollama")

    llm_status = await check_llm_health(health_config)

    return StatusResponse(
        status="ready" if llm_status["healthy"] and db_stats["has_master_resume"] else "setup_required",
        llm_configured=llm_configured,
        llm_healthy=llm_status["healthy"],
        has_master_resume=db_stats["has_master_resume"],
        database_stats=db_stats,
    )
