"""Database adapter abstraction for TinyDB and PostgreSQL."""

import logging
from abc import ABC, abstractmethod
from typing import Any

from app.database import Database as TinyDatabase

logger = logging.getLogger(__name__)


class DatabaseAdapter(ABC):
    """Abstract database adapter interface."""

    @abstractmethod
    def create_resume(
        self,
        user_id: int,
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
        """Create a new resume entry."""
        pass

    @abstractmethod
    async def create_resume_atomic_master(
        self,
        user_id: int,
        content: str,
        content_type: str = "md",
        filename: str | None = None,
        processed_data: dict[str, Any] | None = None,
        processing_status: str = "pending",
        cover_letter: str | None = None,
        outreach_message: str | None = None,
        original_markdown: str | None = None,
    ) -> dict[str, Any]:
        """Create a new resume with atomic master assignment."""
        pass

    @abstractmethod
    def get_resume(self, user_id: int, resume_id: str) -> dict[str, Any] | None:
        """Get resume by ID (user-isolated)."""
        pass

    @abstractmethod
    def get_master_resume(self, user_id: int) -> dict[str, Any] | None:
        """Get the master resume for a user."""
        pass

    @abstractmethod
    def update_resume(self, user_id: int, resume_id: str, updates: dict[str, Any]) -> dict[str, Any]:
        """Update resume by ID."""
        pass

    @abstractmethod
    def delete_resume(self, user_id: int, resume_id: str) -> bool:
        """Delete resume by ID."""
        pass

    @abstractmethod
    def list_resumes(self, user_id: int) -> list[dict[str, Any]]:
        """List all resumes for a user."""
        pass

    @abstractmethod
    def set_master_resume(self, user_id: int, resume_id: str) -> bool:
        """Set a resume as the master."""
        pass

    @abstractmethod
    def create_job(self, user_id: int, content: str, resume_id: str | None = None) -> dict[str, Any]:
        """Create a new job description entry."""
        pass

    @abstractmethod
    def get_job(self, user_id: int, job_id: str) -> dict[str, Any] | None:
        """Get job by ID (user-isolated)."""
        pass

    @abstractmethod
    def update_job(self, user_id: int, job_id: str, updates: dict[str, Any]) -> dict[str, Any] | None:
        """Update a job by ID."""
        pass

    @abstractmethod
    def get_jobs_for_resume(self, user_id: int, resume_id: str) -> list[dict[str, Any]]:
        """Get all jobs for a specific resume."""
        pass

    @abstractmethod
    def create_improvement(
        self,
        user_id: int,
        original_resume_id: str,
        tailored_resume_id: str,
        job_id: str,
        improvements: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Create an improvement result entry."""
        pass

    @abstractmethod
    def get_improvement_by_tailored_resume(self, user_id: int, tailored_resume_id: str) -> dict[str, Any] | None:
        """Get improvement record by tailored resume ID."""
        pass

    @abstractmethod
    def get_stats(self, user_id: int) -> dict[str, Any]:
        """Get database statistics for a user."""
        pass

    @abstractmethod
    def close(self) -> None:
        """Close database connection."""
        pass


class TinyDBAdapter(DatabaseAdapter):
    """TinyDB adapter (local file storage)."""

    def __init__(self, tiny_db: TinyDatabase) -> None:
        """Initialize with TinyDB instance."""
        self.db = tiny_db

    def create_resume(
        self,
        user_id: int,
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
        """Create a new resume entry."""
        result = self.db.create_resume(
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
        # Add user_id to result for consistency
        result["user_id"] = user_id
        return result

    async def create_resume_atomic_master(
        self,
        user_id: int,
        content: str,
        content_type: str = "md",
        filename: str | None = None,
        processed_data: dict[str, Any] | None = None,
        processing_status: str = "pending",
        cover_letter: str | None = None,
        outreach_message: str | None = None,
        original_markdown: str | None = None,
    ) -> dict[str, Any]:
        """Create a new resume with atomic master assignment."""
        result = await self.db.create_resume_atomic_master(
            content=content,
            content_type=content_type,
            filename=filename,
            processed_data=processed_data,
            processing_status=processing_status,
            cover_letter=cover_letter,
            outreach_message=outreach_message,
            original_markdown=original_markdown,
        )
        result["user_id"] = user_id
        return result

    def get_resume(self, user_id: int, resume_id: str) -> dict[str, Any] | None:
        """Get resume by ID."""
        result = self.db.get_resume(resume_id)
        if result:
            result["user_id"] = user_id
        return result

    def get_master_resume(self, user_id: int) -> dict[str, Any] | None:
        """Get the master resume for a user."""
        result = self.db.get_master_resume()
        if result:
            result["user_id"] = user_id
        return result

    def update_resume(self, user_id: int, resume_id: str, updates: dict[str, Any]) -> dict[str, Any]:
        """Update resume by ID."""
        result = self.db.update_resume(resume_id, updates)
        result["user_id"] = user_id
        return result

    def delete_resume(self, user_id: int, resume_id: str) -> bool:
        """Delete resume by ID."""
        return self.db.delete_resume(resume_id)

    def list_resumes(self, user_id: int) -> list[dict[str, Any]]:
        """List all resumes for a user."""
        results = self.db.list_resumes()
        for result in results:
            result["user_id"] = user_id
        return results

    def set_master_resume(self, user_id: int, resume_id: str) -> bool:
        """Set a resume as the master."""
        return self.db.set_master_resume(resume_id)

    def create_job(self, user_id: int, content: str, resume_id: str | None = None) -> dict[str, Any]:
        """Create a new job description entry."""
        result = self.db.create_job(content, resume_id)
        result["user_id"] = user_id
        return result

    def get_job(self, user_id: int, job_id: str) -> dict[str, Any] | None:
        """Get job by ID."""
        result = self.db.get_job(job_id)
        if result:
            result["user_id"] = user_id
        return result

    def update_job(self, user_id: int, job_id: str, updates: dict[str, Any]) -> dict[str, Any] | None:
        """Update a job by ID."""
        result = self.db.update_job(job_id, updates)
        if result:
            result["user_id"] = user_id
        return result

    def get_jobs_for_resume(self, user_id: int, resume_id: str) -> list[dict[str, Any]]:
        """Get all jobs for a specific resume."""
        # TinyDB doesn't have this method; we need to filter manually
        # For now, return empty list as placeholder
        return []

    def create_improvement(
        self,
        user_id: int,
        original_resume_id: str,
        tailored_resume_id: str,
        job_id: str,
        improvements: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Create an improvement result entry."""
        result = self.db.create_improvement(original_resume_id, tailored_resume_id, job_id, improvements)
        result["user_id"] = user_id
        return result

    def get_improvement_by_tailored_resume(self, user_id: int, tailored_resume_id: str) -> dict[str, Any] | None:
        """Get improvement record by tailored resume ID."""
        result = self.db.get_improvement_by_tailored_resume(tailored_resume_id)
        if result:
            result["user_id"] = user_id
        return result

    def get_stats(self, user_id: int) -> dict[str, Any]:
        """Get database statistics for a user."""
        stats = self.db.get_stats()
        stats["user_id"] = user_id
        return stats

    def close(self) -> None:
        """Close database connection."""
        self.db.close()
