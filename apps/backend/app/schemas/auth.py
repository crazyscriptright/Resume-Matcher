"""Pydantic schemas for authentication."""

from pydantic import BaseModel, EmailStr, Field, field_validator


class RegisterRequest(BaseModel):
    """Request body for user registration."""

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        """Normalize email for uniqueness checks and admin matching."""
        return str(value).strip().lower()


class LoginRequest(BaseModel):
    """Request body for user login."""

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        """Normalize email before authentication checks."""
        return str(value).strip().lower()


class UserInfo(BaseModel):
    """Safe user details returned to clients."""

    user_id: str
    email: str
    role: str


class TokenResponse(BaseModel):
    """JWT token response payload."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserInfo
