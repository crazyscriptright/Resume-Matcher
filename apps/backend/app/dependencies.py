"""FastAPI dependencies."""

from typing import Annotated

from fastapi import Depends

from app.db_adapter import DatabaseAdapter


async def get_db_adapter() -> DatabaseAdapter:
    """Get the current database adapter."""
    from app.main import db_adapter

    if db_adapter is None:
        raise RuntimeError("Database adapter not initialized")
    return db_adapter


# Annotated type for use in route handlers
DBAdapter = Annotated[DatabaseAdapter, Depends(get_db_adapter)]
