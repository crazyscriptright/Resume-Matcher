"""Shared config cache used by multiple routers.

This module owns the cached read of ``app_config/main`` (Firestore) so
that routers (resumes, enrichment, config) can share it without importing
each other.
"""

import copy
import logging
import time
from typing import Any

from app.config import load_config_file

logger = logging.getLogger(__name__)

# Cache state — accessed without a lock because:
# 1. The app runs single-worker uvicorn (one thread, cooperative async).
# 2. The GIL protects dict/float assignment; worst-case TOCTOU is a
#    redundant Firestore read (benign, same document, same result).
# 3. A threading.Lock would block the event loop; an asyncio.Lock would
#    require making load_config async and changing every caller.
_config_cache: dict[str, Any] = {}
_config_cache_time: float = 0.0
_CONFIG_CACHE_TTL: float = 300.0  # 5 minutes


def invalidate_config_cache() -> None:
    """Invalidate the config cache so the next read fetches from Firestore.

    Call this after any write to the config document.
    """
    global _config_cache, _config_cache_time
    _config_cache = {}
    _config_cache_time = 0.0


def load_config() -> dict[str, Any]:
    """Load configuration from Firestore with 5-minute TTL cache.

    Returns a deep copy so callers cannot corrupt the cached data.
    """
    global _config_cache, _config_cache_time
    now = time.monotonic()
    if _config_cache and (now - _config_cache_time) < _CONFIG_CACHE_TTL:
        return copy.deepcopy(_config_cache)

    try:
        _config_cache = load_config_file()
        _config_cache_time = now
        return copy.deepcopy(_config_cache)
    except Exception as e:
        logger.error("Failed to load config: %s", e)
        _config_cache = {}
        _config_cache_time = now
        return {}


def get_content_language() -> str:
    """Get configured content language from cached config."""
    config = load_config()
    return config.get("content_language", config.get("language", "en"))
