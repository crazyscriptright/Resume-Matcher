"""Unit tests for auth service helpers."""

import pytest
from fastapi import HTTPException

from app.services.auth import (
    create_access_token,
    decode_access_token,
    get_default_role_for_email,
    hash_password,
    verify_password,
)


class TestPasswordHelpers:
    """Password hash/verify behavior."""

    def test_hash_and_verify_password(self):
        password = "password123"
        password_hash = hash_password(password)

        assert password_hash != password
        assert verify_password(password, password_hash) is True
        assert verify_password("wrong-password", password_hash) is False


class TestTokenHelpers:
    """JWT creation and validation behavior."""

    def test_create_and_decode_access_token(self):
        token = create_access_token({"sub": "u-1", "email": "user@example.com", "role": "user"})

        payload = decode_access_token(token)

        assert payload["sub"] == "u-1"
        assert payload["email"] == "user@example.com"
        assert payload["role"] == "user"
        assert payload["exp"] > payload["iat"]

    def test_decode_invalid_token_raises_http_401(self):
        with pytest.raises(HTTPException) as exc:
            decode_access_token("invalid-token")

        assert exc.value.status_code == 401


class TestRoleAssignment:
    """Backend role assignment rules."""

    def test_default_role_user(self, monkeypatch):
        from app.services import auth as auth_service

        monkeypatch.setattr(auth_service.settings, "admin_emails", ["admin@example.com"])
        monkeypatch.setattr(auth_service.settings, "premium_emails", ["premium@example.com"])
        assert get_default_role_for_email("normal@example.com") == "user"

    def test_allowlisted_email_gets_admin_role(self, monkeypatch):
        from app.services import auth as auth_service

        monkeypatch.setattr(auth_service.settings, "admin_emails", ["admin@example.com"])
        monkeypatch.setattr(auth_service.settings, "premium_emails", ["admin@example.com"])
        assert get_default_role_for_email("ADMIN@example.com") == "admin"

    def test_allowlisted_email_gets_premium_role(self, monkeypatch):
        from app.services import auth as auth_service

        monkeypatch.setattr(auth_service.settings, "admin_emails", ["admin@example.com"])
        monkeypatch.setattr(auth_service.settings, "premium_emails", ["premium@example.com"])
        assert get_default_role_for_email("premium@example.com") == "premium"
