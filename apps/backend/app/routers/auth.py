"""Authentication API endpoints."""

import logging

from fastapi import APIRouter, HTTPException, status

from app.database import db
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserInfo
from app.services.auth import (
    create_access_token,
    get_default_role_for_email,
    get_token_expiry_seconds,
    hash_password,
    verify_password,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=TokenResponse)
async def register(request: RegisterRequest) -> TokenResponse:
    """Register using email/password; role is managed server-side only."""
    if db.get_user_by_email(request.email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    role = get_default_role_for_email(request.email)
    user = db.create_user(
        email=request.email,
        password_hash=hash_password(request.password),
        role=role,
    )

    token = create_access_token(
        {
            "sub": user["user_id"],
            "email": user["email"],
            "role": user["role"],
        }
    )

    return TokenResponse(
        access_token=token,
        expires_in=get_token_expiry_seconds(),
        user=UserInfo(user_id=user["user_id"], email=user["email"], role=user["role"]),
    )


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest) -> TokenResponse:
    """Authenticate with email/password and issue access token."""
    user = db.get_user_by_email(request.email)
    if not user or not verify_password(request.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    token = create_access_token(
        {
            "sub": user["user_id"],
            "email": user["email"],
            "role": user["role"],
        }
    )

    return TokenResponse(
        access_token=token,
        expires_in=get_token_expiry_seconds(),
        user=UserInfo(user_id=user["user_id"], email=user["email"], role=user["role"]),
    )
