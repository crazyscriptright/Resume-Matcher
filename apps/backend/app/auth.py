"""Authentication middleware and dependencies for FastAPI."""

import logging
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.services.auth import decode_access_token, get_user_by_id
from app.db import get_db_session

logger = logging.getLogger(__name__)

security = HTTPBearer()


async def get_current_user_id(credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)]) -> int:
    """Extract and validate user ID from JWT token.

    Args:
        credentials: HTTP Bearer credentials

    Returns:
        User ID

    Raises:
        HTTPException: If token is invalid or missing
    """
    token = credentials.credentials
    user_id = decode_access_token(token)

    if user_id is None:
        logger.warning("Invalid or expired token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user_id


# Optional authentication - returns user_id if token provided, None otherwise
async def get_current_user_id_optional(credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)] | None = None) -> int | None:
    """Optionally extract user ID from JWT token.

    Args:
        credentials: HTTP Bearer credentials (optional)

    Returns:
        User ID if token provided and valid, None otherwise
    """
    if credentials is None:
        return None

    token = credentials.credentials
    return decode_access_token(token)


# Type aliases for use in route handlers
CurrentUserID = Annotated[int, Depends(get_current_user_id)]
OptionalUserID = Annotated[int | None, Depends(get_current_user_id_optional)]
