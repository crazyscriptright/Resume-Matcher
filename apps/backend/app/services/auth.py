"""Authentication services for password hashing and JWT handling."""

from datetime import datetime, timedelta, timezone
from contextvars import ContextVar
from typing import Any

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from app.config import settings
from app.database import db

security = HTTPBearer(auto_error=False)
JWT_ALGORITHM = "HS256"
current_user_id: ContextVar[str | None] = ContextVar("current_user_id", default=None)


def hash_password(password: str) -> str:
    """Hash a plaintext password."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a plaintext password against its hash."""
    try:
        return bcrypt.checkpw(
            password.encode("utf-8"),
            password_hash.encode("utf-8"),
        )
    except ValueError:
        return False


def get_token_expiry_seconds() -> int:
    """Get configured token expiry duration in seconds."""
    return settings.auth_token_expire_minutes * 60


def create_access_token(subject: dict[str, Any]) -> str:
    """Create a JWT access token for the provided subject payload."""
    now = datetime.now(timezone.utc)
    expire_at = now + timedelta(minutes=settings.auth_token_expire_minutes)
    payload = {
        **subject,
        "iat": int(now.timestamp()),
        "exp": int(expire_at.timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT access token."""
    try:
        return jwt.decode(token, settings.jwt_secret_key, algorithms=[JWT_ALGORITHM])
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        ) from exc


def get_default_role_for_email(email: str) -> str:
    """Determine initial role for a newly registered user."""
    normalized = email.strip().lower()
    if normalized in settings.admin_emails:
        return "admin"
    if normalized in settings.premium_emails:
        return "premium"
    return "user"


def is_shared_llm_role(role: str) -> bool:
    """Return True for roles that should use the shared LLM API key."""
    return role in {"premium", "admin"}


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> dict[str, Any]:
    """Resolve authenticated user from bearer token."""
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    payload = decode_access_token(credentials.credentials)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    user = db.get_user(str(user_id))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    current_user_id.set(str(user_id))
    return user


async def get_current_admin(user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    """Ensure current authenticated user has admin role."""
    if user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return user
