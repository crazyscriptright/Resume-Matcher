"""LLM Gateway for intelligent multi-model routing with quota management."""

import logging
import time
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from sqlalchemy.orm import Session

from app.models.llm_quota import LLMUserSession
from app.services.model_selector import ModelSelector
from app.services.quota_tracker import QuotaTracker

if TYPE_CHECKING:
    from litellm import Coroutine

logger = logging.getLogger(__name__)


class LLMGateway:
    """Route LLM requests through intelligent model selection with quota tracking."""

    def __init__(self, db: Session) -> None:
        """Initialize gateway.
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db
        self.quota_tracker = QuotaTracker(db)
        self.model_selector = ModelSelector(db)

    def select_model_for_request(
        self, requested_model: str | None = None, estimated_tokens: int = 0, user_id: int | None = None
    ) -> tuple[str | None, str | None, list[str], str]:
        """Select best model for request with fallback chain.
        
        Args:
            requested_model: User-requested model or None for auto-selection
            estimated_tokens: Estimated tokens for request
            user_id: User ID for audit logging
        
        Returns:
            Tuple of (model_name, api_key, fallback_chain, status)
            - model_name: Selected model or None if all exhausted
            - api_key: Actual API key to use
            - fallback_chain: List of models tried
            - status: "success", "fallback_used", or "queued"
        """
        # Quota check function
        def quota_check(model_name: str, api_key: str, tokens: int) -> tuple[bool, str]:
            is_available, reason = self.quota_tracker.check_quota_available(
                model_name, api_key, tokens
            )
            return is_available, reason
        
        # Try to select model
        if requested_model:
            model, api_key, fallback_chain = self.model_selector.select_by_name(
                requested_model, quota_check, estimated_tokens
            )
        else:
            model, api_key, fallback_chain = self.model_selector.select_best_model(
                quota_check, estimated_tokens
            )
        
        # Determine status
        if not model:
            status = "queued"  # All models exhausted, would queue
        elif len(fallback_chain) > 1:
            status = "fallback_used"
        else:
            status = "success"
        
        model_name = model.name if model else None
        
        # Log to session table
        if model_name:
            session_log = LLMUserSession(
                user_id=user_id,
                model_attempted=requested_model or "auto-select",
                model_used=model_name,
                provider=model.provider,
                api_key_index=1,  # Not used with api_key tracking now, kept for compatibility
                status=status,
                fallback_chain=fallback_chain,
                tokens_predicted=estimated_tokens,
            )
            self.db.add(session_log)
            self.db.commit()
        
        return model_name, api_key, fallback_chain, status

    def track_completion(
        self,
        model_name: str,
        api_key: str,
        tokens_used: int,
        prompt_tokens: int | None = None,
        completion_tokens: int | None = None,
        duration_ms: int | None = None,
        error_message: str | None = None,
        user_id: int | None = None,
        fallback_chain: list[str] | None = None,
    ) -> None:
        """Track completion metrics.
        
        Args:
            model_name: Model that was used
            api_key: Actual API key that was used
            tokens_used: Total tokens used
            prompt_tokens: Tokens in prompt
            completion_tokens: Tokens in completion
            duration_ms: Request duration in ms
            error_message: Error if request failed
            user_id: User ID for audit
            fallback_chain: List of models tried before success
        """
        # Update quota tracker (tracks by actual api_key)
        self.quota_tracker.increment_usage(model_name, api_key, tokens_used, requests_count=1)

    def get_quota_status(self, model_name: str | None = None) -> dict[str, Any]:
        """Get current quota usage status.
        
        Args:
            model_name: Specific model or None for all models
        
        Returns:
            Dictionary with quota information
        """
        models = self.model_selector.get_active_models()
        
        if model_name:
            models = [m for m in models if m.name == model_name]
        
        status = {}
        for model in models:
            status[model.name] = {
                "provider": model.provider,
                "priority": model.priority,
                "limits": {
                    "tpm": model.tpm_limit,
                    "rpm": model.rpm_limit,
                    "rpd": model.rpd_limit,
                    "tpd": model.tpd_limit,
                },
                "is_active": model.active,
            }
        
        return status
