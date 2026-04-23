"""Database models package."""

from app.models.llm_quota import (
    LLMBase,
    LLMModel,
    LLMProviderApiKey,
    LLMRequestQueue,
    LLMUserSession,
    LLMUsageTracking,
)

# Alias for compatibility
Base = LLMBase

__all__ = [
    "Base",
    "LLMBase",
    "LLMModel",
    "LLMProviderApiKey",
    "LLMUsageTracking",
    "LLMUserSession",
    "LLMRequestQueue",
]
