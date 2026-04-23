"""Service to select best LLM model with round-robin API key rotation."""

import functools
from typing import TYPE_CHECKING

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.models.llm_quota import LLMModel, LLMProviderApiKey
from app.services.config_loader import load_all_models, load_all_provider_keys

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


# In-memory cache for round-robin key index per provider
_PROVIDER_KEY_INDEX_CACHE: dict[str, int] = {}


class ModelSelector:
    """Select best LLM model and API key with intelligent fallback."""

    def __init__(self, db: Session):
        """Initialize model selector.
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db

    def get_active_models(self) -> list[LLMModel]:
        """Get all active models sorted by priority.
        
        Returns:
            List of LLMModel objects sorted by priority (1 first)
        """
        stmt = select(LLMModel).where(LLMModel.active == True).order_by(LLMModel.priority)
        return self.db.execute(stmt).scalars().all()

    def get_active_models_by_provider(self, provider: str) -> list[LLMModel]:
        """Get all active models for a provider sorted by priority.
        
        Args:
            provider: Provider name ("openai", "gemini")
        
        Returns:
            List of LLMModel objects for provider
        """
        stmt = (
            select(LLMModel)
            .where(and_(LLMModel.active == True, LLMModel.provider == provider))
            .order_by(LLMModel.priority)
        )
        return self.db.execute(stmt).scalars().all()

    def get_api_keys_for_provider(self, provider: str) -> list[str]:
        """Get all active API keys for provider.
        
        Args:
            provider: Provider name
        
        Returns:
            List of API keys in order (key_index 1, 2, 3...)
        """
        stmt = (
            select(LLMProviderApiKey)
            .where(
                and_(
                    LLMProviderApiKey.provider == provider,
                    LLMProviderApiKey.is_active == True,
                )
            )
            .order_by(LLMProviderApiKey.key_index)
        )
        keys = self.db.execute(stmt).scalars().all()
        return [key.api_key for key in keys]

    def get_next_api_key(self, provider: str) -> str | None:
        """Get next API key using round-robin rotation.
        
        Args:
            provider: Provider name
        
        Returns:
            Actual API key value or None if no active keys
        """
        keys = self.get_api_keys_for_provider(provider)
        if not keys:
            return None
        
        # Get current index from cache
        current_index = _PROVIDER_KEY_INDEX_CACHE.get(provider, 0)
        
        # Rotate to next
        next_index = (current_index + 1) % len(keys)
        _PROVIDER_KEY_INDEX_CACHE[provider] = next_index
        
        return keys[next_index]  # Return actual API key

    def select_best_model(
        self, quota_check_func, estimated_tokens: int = 0
    ) -> tuple[LLMModel | None, str | None, list[str]]:
        """Select best available model with fallback chain.
        
        Args:
            quota_check_func: Function that checks if model quota available
                             Signature: (model_name, api_key, tokens) -> (bool, reason)
            estimated_tokens: Estimated tokens for this request
        
        Returns:
            Tuple of (model, api_key, fallback_chain)
            - model: Selected LLMModel or None if all exhausted
            - api_key: Actual API key to use or None
            - fallback_chain: List of attempted models in order
        """
        fallback_chain = []
        models = self.get_active_models()
        
        for model in models:
            fallback_chain.append(model.name)
            
            # Get round-robin API key for this provider
            api_key = self.get_next_api_key(model.provider)
            if not api_key:
                continue  # No keys available for this provider
            
            # Check if quota available
            is_available, reason = quota_check_func(model.name, api_key, estimated_tokens)
            
            if is_available:
                return model, api_key, fallback_chain
        
        # All models exhausted
        return None, None, fallback_chain

    def select_by_name(
        self, model_name: str, quota_check_func, estimated_tokens: int = 0
    ) -> tuple[LLMModel | None, str | None, list[str]]:
        """Try specific model first, then fallback chain.
        
        Args:
            model_name: Requested model name
            quota_check_func: Function to check quota
            estimated_tokens: Estimated tokens for request
        
        Returns:
            Tuple of (model, api_key, fallback_chain)
        """
        fallback_chain = []
        
        # Try requested model first
        stmt = select(LLMModel).where(LLMModel.name == model_name)
        requested_model = self.db.execute(stmt).scalar_one_or_none()
        
        if requested_model and requested_model.active:
            fallback_chain.append(requested_model.name)
            api_key = self.get_next_api_key(requested_model.provider)
            if api_key:
                is_available, _ = quota_check_func(requested_model.name, api_key, estimated_tokens)
                
                if is_available:
                    return requested_model, api_key, fallback_chain
        
        # Fallback to best available
        remaining_model, remaining_api_key, remaining_chain = self.select_best_model(
            quota_check_func, estimated_tokens
        )
        
        fallback_chain.extend(remaining_chain)
        return remaining_model, remaining_api_key, fallback_chain

    def get_model_info(self, model_name: str) -> dict | None:
        """Get model configuration info.
        
        Args:
            model_name: Model name
        
        Returns:
            Dictionary with model info or None
        """
        stmt = select(LLMModel).where(LLMModel.name == model_name)
        model = self.db.execute(stmt).scalar_one_or_none()
        
        if not model:
            return None
        
        return {
            "name": model.name,
            "provider": model.provider,
            "priority": model.priority,
            "tpm_limit": model.tpm_limit,
            "rpm_limit": model.rpm_limit,
            "rpd_limit": model.rpd_limit,
            "tpd_limit": model.tpd_limit,
            "active": model.active,
        }
