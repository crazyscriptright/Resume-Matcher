"""Unit tests for role-based LLM API key resolution."""

from app import llm


def test_user_role_does_not_fallback_to_shared_or_global_key(monkeypatch):
    """User role must use personal key only."""
    token = llm.current_user_id.set("user-1")
    try:
        monkeypatch.setattr(
            llm,
            "load_config_file",
            lambda: {"provider": "openai", "model": "gpt-4", "api_key": "sk-global"},
        )
        monkeypatch.setattr(llm.db, "get_user", lambda _user_id: {"user_id": "user-1", "role": "user"})
        monkeypatch.setattr(llm, "resolve_role_llm_config", lambda _user: {})

        config = llm.get_llm_config()

        assert config.api_key == ""
    finally:
        llm.current_user_id.reset(token)


def test_premium_role_uses_shared_key(monkeypatch):
    """Premium role should use shared key configuration."""
    token = llm.current_user_id.set("premium-1")
    try:
        monkeypatch.setattr(
            llm,
            "load_config_file",
            lambda: {"provider": "openai", "model": "gpt-4", "api_key": "sk-global"},
        )
        monkeypatch.setattr(
            llm.db,
            "get_user",
            lambda _user_id: {"user_id": "premium-1", "role": "premium"},
        )
        monkeypatch.setattr(llm, "resolve_role_llm_config", lambda _user: {"api_key": "sk-shared"})

        config = llm.get_llm_config()

        assert config.api_key == "sk-shared"
    finally:
        llm.current_user_id.reset(token)
