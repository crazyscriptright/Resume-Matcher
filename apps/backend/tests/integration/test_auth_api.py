"""Integration tests for auth endpoints."""

from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
def client() -> AsyncClient:
    """Async HTTP client for testing FastAPI endpoints."""
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


class TestAuthRegister:
    """POST /api/v1/auth/register"""

    @patch("app.routers.auth.db")
    async def test_register_creates_default_user_role(self, mock_db, client, monkeypatch):
        from app.services import auth as auth_service

        monkeypatch.setattr(auth_service.settings, "admin_emails", [])

        mock_db.get_user_by_email.return_value = None
        mock_db.create_user.return_value = {
            "user_id": "u-1",
            "email": "user@example.com",
            "password_hash": "hashed",
            "role": "user",
        }

        async with client:
            resp = await client.post(
                "/api/v1/auth/register",
                json={"email": "user@example.com", "password": "password123"},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["token_type"] == "bearer"
        assert data["user"]["role"] == "user"
        assert data["user"]["email"] == "user@example.com"
        assert data["access_token"]

        create_kwargs = mock_db.create_user.call_args.kwargs
        assert create_kwargs["email"] == "user@example.com"
        assert create_kwargs["role"] == "user"
        assert create_kwargs["password_hash"] != "password123"

    @patch("app.routers.auth.db")
    async def test_register_assigns_admin_from_env_allowlist(self, mock_db, client, monkeypatch):
        from app.services import auth as auth_service

        monkeypatch.setattr(auth_service.settings, "admin_emails", ["admin@example.com"])

        mock_db.get_user_by_email.return_value = None
        mock_db.create_user.return_value = {
            "user_id": "u-2",
            "email": "admin@example.com",
            "password_hash": "hashed",
            "role": "admin",
        }

        async with client:
            resp = await client.post(
                "/api/v1/auth/register",
                json={"email": "admin@example.com", "password": "password123"},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["user"]["role"] == "admin"

        create_kwargs = mock_db.create_user.call_args.kwargs
        assert create_kwargs["role"] == "admin"

    @patch("app.routers.auth.db")
    async def test_register_duplicate_email_returns_conflict(self, mock_db, client):
        mock_db.get_user_by_email.return_value = {
            "user_id": "existing",
            "email": "user@example.com",
        }

        async with client:
            resp = await client.post(
                "/api/v1/auth/register",
                json={"email": "user@example.com", "password": "password123"},
            )

        assert resp.status_code == 409
        assert resp.json()["detail"] == "Email already registered"


class TestAuthLogin:
    """POST /api/v1/auth/login"""

    @patch("app.routers.auth.db")
    async def test_login_success(self, mock_db, client):
        from app.services.auth import hash_password

        mock_db.get_user_by_email.return_value = {
            "user_id": "u-3",
            "email": "user@example.com",
            "password_hash": hash_password("password123"),
            "role": "user",
        }

        async with client:
            resp = await client.post(
                "/api/v1/auth/login",
                json={"email": "user@example.com", "password": "password123"},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["access_token"]
        assert data["user"]["user_id"] == "u-3"

    @patch("app.routers.auth.db")
    async def test_login_invalid_credentials(self, mock_db, client):
        from app.services.auth import hash_password

        mock_db.get_user_by_email.return_value = {
            "user_id": "u-4",
            "email": "user@example.com",
            "password_hash": hash_password("another-password"),
            "role": "user",
        }

        async with client:
            resp = await client.post(
                "/api/v1/auth/login",
                json={"email": "user@example.com", "password": "password123"},
            )

        assert resp.status_code == 401
        assert resp.json()["detail"] == "Invalid email or password"
