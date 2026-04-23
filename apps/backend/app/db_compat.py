"""Database compatibility layer for routers during migration to multi-user.

This provides a drop-in replacement for routers that are not yet
converted to use db_adapter directly. It maintains backward compatibility
while allowing gradual migration.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)

# This will be set by routers during request handling
_current_db_adapter = None
_current_user_id = None


def set_context(db_adapter: Any, user_id: int) -> None:
    """Set the current database adapter and user ID for this request.
    
    Call this at the start of each route handler.
    """
    global _current_db_adapter, _current_user_id
    _current_db_adapter = db_adapter
    _current_user_id = user_id


def clear_context() -> None:
    """Clear the request context."""
    global _current_db_adapter, _current_user_id
    _current_db_adapter = None
    _current_user_id = None


class ContextualDB:
    """Wrapper that uses context-local db_adapter and user_id."""

    @staticmethod
    def create_resume(
        content: str,
        content_type: str = "md",
        filename: str | None = None,
        is_master: bool = False,
        parent_id: str | None = None,
        processed_data: dict[str, Any] | None = None,
        processing_status: str = "pending",
        cover_letter: str | None = None,
        outreach_message: str | None = None,
        title: str | None = None,
        original_markdown: str | None = None,
    ) -> dict[str, Any]:
        return _current_db_adapter.create_resume(
            user_id=_current_user_id,
            content=content,
            content_type=content_type,
            filename=filename,
            is_master=is_master,
            parent_id=parent_id,
            processed_data=processed_data,
            processing_status=processing_status,
            cover_letter=cover_letter,
            outreach_message=outreach_message,
            title=title,
            original_markdown=original_markdown,
        )

    @staticmethod
    async def create_resume_atomic_master(
        content: str,
        content_type: str = "md",
        filename: str | None = None,
        processed_data: dict[str, Any] | None = None,
        processing_status: str = "pending",
        cover_letter: str | None = None,
        outreach_message: str | None = None,
        original_markdown: str | None = None,
    ) -> dict[str, Any]:
        return await _current_db_adapter.create_resume_atomic_master(
            user_id=_current_user_id,
            content=content,
            content_type=content_type,
            filename=filename,
            processed_data=processed_data,
            processing_status=processing_status,
            cover_letter=cover_letter,
            outreach_message=outreach_message,
            original_markdown=original_markdown,
        )

    @staticmethod
    def get_resume(resume_id: str) -> dict[str, Any] | None:
        return _current_db_adapter.get_resume(user_id=_current_user_id, resume_id=resume_id)

    @staticmethod
    def get_master_resume() -> dict[str, Any] | None:
        return _current_db_adapter.get_master_resume(user_id=_current_user_id)

    @staticmethod
    def update_resume(resume_id: str, updates: dict[str, Any]) -> dict[str, Any]:
        return _current_db_adapter.update_resume(
            user_id=_current_user_id,
            resume_id=resume_id,
            updates=updates,
        )

    @staticmethod
    def delete_resume(resume_id: str) -> bool:
        return _current_db_adapter.delete_resume(user_id=_current_user_id, resume_id=resume_id)

    @staticmethod
    def list_resumes() -> list[dict[str, Any]]:
        return _current_db_adapter.list_resumes(user_id=_current_user_id)

    @staticmethod
    def set_master_resume(resume_id: str) -> bool:
        return _current_db_adapter.set_master_resume(user_id=_current_user_id, resume_id=resume_id)

    @staticmethod
    def create_job(content: str, resume_id: str | None = None) -> dict[str, Any]:
        return _current_db_adapter.create_job(
            user_id=_current_user_id,
            content=content,
            resume_id=resume_id,
        )

    @staticmethod
    def get_job(job_id: str) -> dict[str, Any] | None:
        return _current_db_adapter.get_job(user_id=_current_user_id, job_id=job_id)

    @staticmethod
    def update_job(job_id: str, updates: dict[str, Any]) -> dict[str, Any] | None:
        return _current_db_adapter.update_job(
            user_id=_current_user_id,
            job_id=job_id,
            updates=updates,
        )

    @staticmethod
    def get_jobs_for_resume(resume_id: str) -> list[dict[str, Any]]:
        return _current_db_adapter.get_jobs_for_resume(
            user_id=_current_user_id,
            resume_id=resume_id,
        )

    @staticmethod
    def create_improvement(
        original_resume_id: str,
        tailored_resume_id: str,
        job_id: str,
        improvements: list[dict[str, Any]],
    ) -> dict[str, Any]:
        return _current_db_adapter.create_improvement(
            user_id=_current_user_id,
            original_resume_id=original_resume_id,
            tailored_resume_id=tailored_resume_id,
            job_id=job_id,
            improvements=improvements,
        )

    @staticmethod
    def get_improvement_by_tailored_resume(
        tailored_resume_id: str,
    ) -> dict[str, Any] | None:
        return _current_db_adapter.get_improvement_by_tailored_resume(
            user_id=_current_user_id,
            tailored_resume_id=tailored_resume_id,
        )

    @staticmethod
    def get_stats() -> dict[str, Any]:
        return _current_db_adapter.get_stats(user_id=_current_user_id)

    @staticmethod
    def reset_database() -> None:
        """Reset not supported in multi-user context."""
        raise NotImplementedError("reset_database not supported with multi-user adapter")


# Create a singleton instance for use as `db` in routers
db = ContextualDB()
