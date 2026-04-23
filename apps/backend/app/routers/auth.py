"""Authentication router for login and registration endpoints."""

import logging

from fastapi import APIRouter, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import get_current_user_id, CurrentUserID
from app.db import get_db_session
from app.schemas.auth import TokenResponse, UserLogin, UserRegister, UserResponse
from app.services.auth import authenticate_user, create_access_token, register_user

logger = logging.getLogger(__name__)

router = APIRouter(tags=["auth"], prefix="/auth")


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: UserRegister,
) -> TokenResponse:
    """Register a new user.

    Args:
        request: Registration request with email and password

    Returns:
        Token response with access token and user info

    Raises:
        HTTPException: If email already exists or validation fails
    """
    session = get_db_session()
    try:
        # Register user
        user = register_user(session, request.email, request.password)

        # Create access token
        access_token = create_access_token(user.id)

        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            user=UserResponse(id=user.id, email=user.email),
        )
    except ValueError as e:
        logger.warning(f"Registration failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Unexpected error during registration: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed. Please try again.",
        )
    finally:
        session.close()


@router.post("/login", response_model=TokenResponse)
async def login(request: UserLogin) -> TokenResponse:
    """Authenticate user and return JWT token.

    Args:
        request: Login request with email and password

    Returns:
        Token response with access token and user info

    Raises:
        HTTPException: If credentials invalid
    """
    session = get_db_session()
    try:
        # Authenticate user
        user = authenticate_user(session, request.email, request.password)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )

        # Create access token
        access_token = create_access_token(user.id)

        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            user=UserResponse(id=user.id, email=user.email),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during login: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed. Please try again.",
        )
    finally:
        session.close()


@router.get("/me", response_model=UserResponse)
async def get_current_user(user_id: CurrentUserID) -> UserResponse:
    """Get current authenticated user information.

    Args:
        user_id: Current user ID (extracted from JWT token)

    Returns:
        Current user information

    Raises:
        HTTPException: If user not found
    """
    from app.services.auth import get_user_by_id

    session = get_db_session()
    try:
        user = get_user_by_id(session, user_id)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        return UserResponse(id=user.id, email=user.email)
    finally:
        session.close()
