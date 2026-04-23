"""Service to load and parse LLM model configuration from .env with flexible limits."""

import os
from dataclasses import dataclass
from typing import Any


@dataclass
class ModelConfig:
    """Configuration for a single LLM model."""

    name: str
    provider: str  # "openai", "gemini"
    priority: int  # 1=highest, 8=lowest
    tpm_limit: int | None  # tokens/min, None=unlimited
    rpm_limit: int | None  # requests/min, None=unlimited
    rpd_limit: int | None  # requests/day, None=unlimited
    tpd_limit: int | None  # tokens/day, None=unlimited

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "provider": self.provider,
            "priority": self.priority,
            "tpm_limit": self.tpm_limit,
            "rpm_limit": self.rpm_limit,
            "rpd_limit": self.rpd_limit,
            "tpd_limit": self.tpd_limit,
        }


@dataclass
class ProviderApiKeys:
    """API keys for a provider."""

    provider: str  # "openai", "gemini"
    keys: list[str]  # [key1, key2, key3, ...]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {"provider": self.provider, "keys": self.keys}


def parse_limit(env_key: str) -> int | None:
    """Parse limit from env variable.
    
    Returns:
        - None if env var not set, empty, or value is "0" (treated as unlimited)
        - int if valid positive integer
    
    Args:
        env_key: Environment variable name
    
    Returns:
        Parsed limit or None for unlimited
    """
    value = os.getenv(env_key, "").strip()
    
    if not value:  # Empty string or not set
        return None  # Unlimited
    
    try:
        int_value = int(value)
        return None if int_value == 0 else int_value
    except ValueError:
        # Invalid value → treat as unlimited to avoid breaking
        return None


def load_model_config(model_num: int) -> ModelConfig | None:
    """Load configuration for a single model from .env.
    
    Expected env vars:
    - LLM_MODEL_N_NAME=model-name
    - LLM_MODEL_N_PROVIDER=openai|gemini
    - LLM_MODEL_N_PRIORITY=1-8
    - LLM_MODEL_N_TPM=123456 (optional, default unlimited)
    - LLM_MODEL_N_RPM=5000 (optional, default unlimited)
    - LLM_MODEL_N_RPD=200000 (optional, default unlimited)
    - LLM_MODEL_N_TPD=1000000 (optional, default unlimited)
    
    Args:
        model_num: Model number (1-8)
    
    Returns:
        ModelConfig if all required fields present, None otherwise
    """
    name = os.getenv(f"LLM_MODEL_{model_num}_NAME", "").strip()
    provider = os.getenv(f"LLM_MODEL_{model_num}_PROVIDER", "").strip()
    priority_str = os.getenv(f"LLM_MODEL_{model_num}_PRIORITY", "").strip()
    
    # Required fields
    if not name or not provider or not priority_str:
        return None
    
    try:
        priority = int(priority_str)
    except ValueError:
        return None
    
    # Optional limits (None = unlimited)
    tpm_limit = parse_limit(f"LLM_MODEL_{model_num}_TPM")
    rpm_limit = parse_limit(f"LLM_MODEL_{model_num}_RPM")
    rpd_limit = parse_limit(f"LLM_MODEL_{model_num}_RPD")
    tpd_limit = parse_limit(f"LLM_MODEL_{model_num}_TPD")
    
    return ModelConfig(
        name=name,
        provider=provider,
        priority=priority,
        tpm_limit=tpm_limit,
        rpm_limit=rpm_limit,
        rpd_limit=rpd_limit,
        tpd_limit=tpd_limit,
    )


def load_all_models() -> list[ModelConfig]:
    """Load all LLM models (1-8) from .env.
    
    Returns:
        List of ModelConfig objects, sorted by priority (1 first)
    """
    models = []
    
    # Try loading models 1-8
    for model_num in range(1, 9):
        config = load_model_config(model_num)
        if config:
            models.append(config)
    
    # Sort by priority
    models.sort(key=lambda m: m.priority)
    
    return models


def load_provider_api_keys(provider: str) -> ProviderApiKeys:
    """Load all API keys for a provider from .env.
    
    Expected env vars:
    - {PROVIDER_UPPER}_API_KEY_1=...
    - {PROVIDER_UPPER}_API_KEY_2=...
    - {PROVIDER_UPPER}_API_KEY_3=...
    - etc.
    
    Example for Gemini:
    - GEMINI_API_KEY_1=...
    - GEMINI_API_KEY_2=...
    
    Args:
        provider: Provider name ("openai", "gemini")
    
    Returns:
        ProviderApiKeys with list of keys
    """
    provider_upper = provider.upper()
    keys = []
    
    # Try loading keys 1-10
    for key_index in range(1, 11):
        env_key = f"{provider_upper}_API_KEY_{key_index}"
        api_key = os.getenv(env_key, "").strip()
        
        if api_key:
            keys.append(api_key)
    
    return ProviderApiKeys(provider=provider, keys=keys)


def load_all_provider_keys() -> dict[str, ProviderApiKeys]:
    """Load API keys for all providers.
    
    Returns:
        Dictionary mapping provider name to ProviderApiKeys
    """
    providers = ["openai", "gemini", "anthropic", "deepseek"]
    result = {}
    
    for provider in providers:
        keys = load_provider_api_keys(provider)
        if keys.keys:  # Only include if has at least one key
            result[provider] = keys
    
    return result


def validate_config() -> tuple[list[ModelConfig], dict[str, ProviderApiKeys], list[str]]:
    """Validate and load full LLM configuration.
    
    Returns:
        Tuple of (models, provider_keys, warnings)
    """
    models = load_all_models()
    provider_keys = load_all_provider_keys()
    warnings = []
    
    # Validate each model has corresponding API keys
    for model in models:
        if model.provider not in provider_keys:
            warnings.append(f"Model {model.name} requires provider {model.provider} but no API keys configured")
        elif not provider_keys[model.provider].keys:
            warnings.append(f"Model {model.name} requires provider {model.provider} but no API keys found")
    
    return models, provider_keys, warnings
