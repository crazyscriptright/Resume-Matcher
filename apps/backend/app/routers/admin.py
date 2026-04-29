"""Admin API endpoints — restricted to users with role='admin'."""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.database import db
from app.services.auth import get_current_admin

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["Admin"])

VALID_ROLES = {"user", "premium", "admin"}


# ── Schemas ──────────────────────────────────────────────────────────────

class UserSummary(BaseModel):
    """Safe user summary returned by the list endpoint."""
    user_id: str
    email: str
    role: str
    created_at: str
    updated_at: str


class UserListResponse(BaseModel):
    """Response for the user list endpoint."""
    users: list[UserSummary]


class UpdateRoleRequest(BaseModel):
    """Request body for role update."""
    role: str


class UpdateRoleResponse(BaseModel):
    """Response for role update."""
    message: str
    user: UserSummary


# ── Endpoints ────────────────────────────────────────────────────────────

@router.get("/users", response_model=UserListResponse)
async def list_users(
    admin: dict[str, Any] = Depends(get_current_admin),
) -> UserListResponse:
    """List all registered users. Admin only."""
    users = db.list_users()
    return UserListResponse(
        users=[UserSummary(**u) for u in users],
    )


@router.patch("/users/{user_id}/role", response_model=UpdateRoleResponse)
async def update_user_role(
    user_id: str,
    request: UpdateRoleRequest,
    admin: dict[str, Any] = Depends(get_current_admin),
) -> UpdateRoleResponse:
    """Update a user's role. Admin only.

    Prevents admins from demoting themselves to avoid accidental lockout.
    """
    if request.role not in VALID_ROLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role '{request.role}'. Must be one of: {', '.join(sorted(VALID_ROLES))}",
        )

    # Prevent self-demotion
    if user_id == admin["user_id"] and request.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot change your own admin role.",
        )

    updated = db.update_user_role(user_id, request.role)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    logger.info(
        "Admin %s changed role of user %s to '%s'",
        admin["email"],
        updated["email"],
        request.role,
    )

    return UpdateRoleResponse(
        message=f"Role updated to '{request.role}'",
        user=UserSummary(
            user_id=updated["user_id"],
            email=updated["email"],
            role=updated["role"],
            created_at=updated.get("created_at", ""),
            updated_at=updated.get("updated_at", ""),
        ),
    )
