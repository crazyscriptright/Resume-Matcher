"""Application configuration using pydantic-settings.

Config persistence uses Firebase Firestore (collection: ``app_config``,
document: ``main``) so nothing is stored on the local filesystem.
This is critical for ephemeral hosting (Heroku dynos, Railway, etc.).
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, Literal

import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore_v1.base_query import FieldFilter
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ALLOWED_LOG_LEVELS = ("CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG")

logger = logging.getLogger(__name__)


# ── Firestore-backed config storage ─────────────────────────────────────────

_firestore_client = None

def _get_firestore_client():
    """Get or initialize the Firestore client.

    Re-uses the same Firebase app as the database module (both call
    ``firebase_admin.get_app()`` first).
    """
    global _firestore_client
    if _firestore_client is not None:
        return _firestore_client

    raw = os.environ.get("FIREBASE_SERVICE_ACCOUNT", "")
    if not raw:
        logger.warning(
            "FIREBASE_SERVICE_ACCOUNT not set — config will use in-memory fallback"
        )
        return None

    try:
        service_account_info = json.loads(raw)
    except json.JSONDecodeError as e:
        logger.error("FIREBASE_SERVICE_ACCOUNT is not valid JSON: %s", e)
        return None

    cred = credentials.Certificate(service_account_info)
    try:
        firebase_admin.get_app()
    except ValueError:
        firebase_admin.initialize_app(cred)

    _firestore_client = firestore.client()
    return _firestore_client


# In-memory fallback when Firestore is unavailable (dev / testing)
_memory_config: dict[str, Any] = {}

CONFIG_COLLECTION = "app_config"
CONFIG_DOC_ID = "main"


def load_config_file() -> dict[str, Any]:
    """Load configuration from Firestore.

    Returns:
        Dictionary with configuration values, empty dict if not found.
    """
    client = _get_firestore_client()
    if client is None:
        return dict(_memory_config)

    try:
        doc = client.collection(CONFIG_COLLECTION).document(CONFIG_DOC_ID).get()
        if doc.exists:
            return doc.to_dict() or {}
        return {}
    except Exception as e:
        logger.error("Failed to load config from Firestore: %s", e)
        return {}


def save_config_file(config: dict[str, Any]) -> None:
    """Save configuration to Firestore.

    Args:
        config: Dictionary with configuration values to save.
    """
    global _memory_config

    client = _get_firestore_client()
    if client is None:
        _memory_config = dict(config)
        return

    try:
        client.collection(CONFIG_COLLECTION).document(CONFIG_DOC_ID).set(config)
    except Exception as e:
        logger.error("Failed to save config to Firestore: %s", e)


def get_api_keys_from_config() -> dict[str, str]:
    """Get API keys from config.

    Returns:
        Dictionary with provider names as keys and API keys as values.
    """
    config = load_config_file()
    return config.get("api_keys", {})


def save_api_keys_to_config(api_keys: dict[str, str]) -> None:
    """Save API keys to config.

    Args:
        api_keys: Dictionary with provider names as keys and API keys as values.
    """
    config = load_config_file()
    config["api_keys"] = api_keys
    save_config_file(config)


def delete_api_key_from_config(provider: str) -> None:
    """Delete a specific API key from config.

    Args:
        provider: The provider name to delete.
    """
    config = load_config_file()
    if "api_keys" in config and provider in config["api_keys"]:
        del config["api_keys"][provider]
        save_config_file(config)


def clear_all_api_keys() -> None:
    """Clear all API keys from config."""
    config = load_config_file()
    # Clear plural dict
    config["api_keys"] = {}
    # Clear singular top-level key (legacy support)
    config["api_key"] = ""
    save_config_file(config)


def _get_llm_api_key_with_fallback() -> str:
    """Get LLM API key with fallback to config.

    Priority: Environment variable > Firestore config > empty string
    """
    # First check environment variable
    env_key = os.environ.get("LLM_API_KEY", "")
    if env_key:
        return env_key

    # Fallback to config based on provider
    config_keys = get_api_keys_from_config()
    provider = os.environ.get("LLM_PROVIDER", "openai")

    # Map provider to config key
    provider_map = {
        "openai": "openai",
        "anthropic": "anthropic",
        "gemini": "google",
        "openrouter": "openrouter",
        "deepseek": "deepseek",
        "ollama": "ollama",
    }

    config_provider = provider_map.get(provider, provider)
    return config_keys.get(config_provider, "")


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # LLM Configuration
    llm_provider: Literal[
        "openai",
        "openai_compatible",
        "anthropic",
        "openrouter",
        "gemini",
        "deepseek",
        "ollama",
    ] = "openai"
    llm_model: str = "gpt-5-nano-2025-08-07"
    llm_api_key: str = ""
    llm_api_base: str | None = None  # For Ollama or custom endpoints
    log_llm: Literal["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"] = "WARNING"

    @field_validator("llm_provider", mode="before")
    @classmethod
    def set_default_provider(cls, v: Any) -> str:
        """Handle empty string provider by defaulting to openai."""
        if not v or (isinstance(v, str) and not v.strip()):
            return "openai"
        return v

    @field_validator("log_llm", mode="before")
    @classmethod
    def normalize_log_llm_level(cls, v: Any) -> str:
        """Normalize LiteLLM log level from environment values."""
        value = "WARNING" if not v else str(v).strip().upper()
        if value not in ALLOWED_LOG_LEVELS:
            raise ValueError(f"Invalid LOG_LLM: {value}. Allowed: {ALLOWED_LOG_LEVELS}")
        return value

    # Server Configuration
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = False
    log_level: Literal["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"] = "INFO"
    frontend_base_url: str = "http://localhost:3000"

    # Reasoning effort for models that support it (OpenAI gpt-5 family,
    # Anthropic Claude 3.7+, DeepSeek R1, etc.). None means "do not send the
    # param" — the default for maximum compatibility. LiteLLM drops this
    # parameter for providers that don't support it (via drop_params=True).
    reasoning_effort: Literal["minimal", "low", "medium", "high"] | None = None

    @field_validator("reasoning_effort", mode="before")
    @classmethod
    def normalize_reasoning_effort(cls, v: Any) -> Any:
        """Treat empty string (common when env var is blank) as None."""
        if isinstance(v, str) and not v.strip():
            return None
        return v

    @field_validator("log_level", mode="before")
    @classmethod
    def normalize_log_level(cls, v: Any) -> str:
        """Normalize application log level from environment values."""
        value = "INFO" if not v else str(v).strip().upper()
        if value not in ALLOWED_LOG_LEVELS:
            raise ValueError(f"Invalid LOG_LEVEL: {value}. Allowed: {ALLOWED_LOG_LEVELS}")
        return value

    # CORS Configuration
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    @property
    def effective_cors_origins(self) -> list[str]:
        """CORS origins including frontend_base_url for production deployments."""
        origins = list(self.cors_origins)
        url = self.frontend_base_url.strip().rstrip("/")
        if url and url not in origins:
            origins.append(url)
        return origins

    # Paths
    data_dir: Path = Path(__file__).parent.parent / "data"

    @property
    def db_path(self) -> Path:
        """Path to database file (legacy — kept for compatibility)."""
        return self.data_dir / "database.json"

    @property
    def config_path(self) -> Path:
        """Path to config storage file (legacy — kept for compatibility)."""
        return self.data_dir / "config.json"

    def get_effective_api_key(self) -> str:
        """Get the effective API key with config fallback.

        Priority: Environment/settings value > Firestore config > empty string
        """
        if self.llm_api_key:
            return self.llm_api_key
        return _get_llm_api_key_with_fallback()


settings = Settings()
