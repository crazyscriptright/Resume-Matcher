"""PostgreSQL adapter implementation using SQLAlchemy."""

import asyncio
import logging
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from app.models import Improvement, Job, Resume, User
from app.db_adapter import DatabaseAdapter

logger = logging.getLogger(__name__)


class PostgreSQLAdapter(DatabaseAdapter):
    """PostgreSQL adapter using SQLAlchemy ORM."""

    _master_resume_lock = asyncio.Lock()

    def __init__(self, session_factory: Any) -> None:
        """Initialize with SQLAlchemy session factory."""
        self.session_factory = session_factory

    def _get_session(self) -> Session:
        """Get a new database session."""
        return self.session_factory()

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
        session = self._get_session()
        try:
            resume = Resume(
                user_id=user_id,
                resume_id=str(uuid4()),
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
            session.add(resume)
            session.commit()
            result = resume.to_dict()
            return result
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to create resume: {e}")
            raise
        finally:
            session.close()

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
        async with self._master_resume_lock:
            session = self._get_session()
            try:
                # Check if user has a master resume
                current_master = session.query(Resume).filter(
                    Resume.user_id == user_id,
                    Resume.is_master == True
                ).first()

                is_master = current_master is None

                # Recovery: if current master is stuck in failed/processing state
                if current_master and current_master.processing_status in ("failed", "processing"):
                    current_master.is_master = False
                    is_master = True

                # Create new resume
                resume = Resume(
                    user_id=user_id,
                    resume_id=str(uuid4()),
                    content=content,
                    content_type=content_type,
                    filename=filename,
                    is_master=is_master,
                    processed_data=processed_data,
                    processing_status=processing_status,
                    cover_letter=cover_letter,
                    outreach_message=outreach_message,
                    original_markdown=original_markdown,
                )
                session.add(resume)
                session.commit()
                result = resume.to_dict()
                return result
            except Exception as e:
                session.rollback()
                logger.error(f"Failed to create resume atomically: {e}")
                raise
            finally:
                session.close()

    def get_resume(self, user_id: int, resume_id: str) -> dict[str, Any] | None:
        """Get resume by ID (user-isolated)."""
        session = self._get_session()
        try:
            resume = session.query(Resume).filter(
                Resume.user_id == user_id,
                Resume.resume_id == resume_id
            ).first()
            return resume.to_dict() if resume else None
        finally:
            session.close()

    def get_master_resume(self, user_id: int) -> dict[str, Any] | None:
        """Get the master resume for a user."""
        session = self._get_session()
        try:
            resume = session.query(Resume).filter(
                Resume.user_id == user_id,
                Resume.is_master == True
            ).first()
            return resume.to_dict() if resume else None
        finally:
            session.close()

    def update_resume(self, user_id: int, resume_id: str, updates: dict[str, Any]) -> dict[str, Any]:
        """Update resume by ID."""
        session = self._get_session()
        try:
            resume = session.query(Resume).filter(
                Resume.user_id == user_id,
                Resume.resume_id == resume_id
            ).first()

            if not resume:
                raise ValueError(f"Resume not found: {resume_id}")

            for key, value in updates.items():
                if hasattr(resume, key):
                    setattr(resume, key, value)

            session.commit()
            result = resume.to_dict()
            return result
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to update resume: {e}")
            raise
        finally:
            session.close()

    def delete_resume(self, user_id: int, resume_id: str) -> bool:
        """Delete resume by ID."""
        session = self._get_session()
        try:
            resume = session.query(Resume).filter(
                Resume.user_id == user_id,
                Resume.resume_id == resume_id
            ).first()

            if not resume:
                return False

            session.delete(resume)
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to delete resume: {e}")
            raise
        finally:
            session.close()

    def list_resumes(self, user_id: int) -> list[dict[str, Any]]:
        """List all resumes for a user."""
        session = self._get_session()
        try:
            resumes = session.query(Resume).filter(
                Resume.user_id == user_id
            ).all()
            return [resume.to_dict() for resume in resumes]
        finally:
            session.close()

    def set_master_resume(self, user_id: int, resume_id: str) -> bool:
        """Set a resume as the master."""
        session = self._get_session()
        try:
            # Verify target resume exists and belongs to user
            target = session.query(Resume).filter(
                Resume.user_id == user_id,
                Resume.resume_id == resume_id
            ).first()

            if not target:
                logger.warning(f"Cannot set master: resume {resume_id} not found for user {user_id}")
                return False

            # Unset current master
            current_master = session.query(Resume).filter(
                Resume.user_id == user_id,
                Resume.is_master == True
            ).first()

            if current_master:
                current_master.is_master = False

            # Set new master
            target.is_master = True
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to set master resume: {e}")
            raise
        finally:
            session.close()

    def create_job(self, user_id: int, content: str, resume_id: str | None = None) -> dict[str, Any]:
        """Create a new job description entry."""
        session = self._get_session()
        try:
            # Resolve resume_id to database ID if provided
            resume_db_id = None
            if resume_id:
                resume = session.query(Resume).filter(
                    Resume.user_id == user_id,
                    Resume.resume_id == resume_id
                ).first()
                if resume:
                    resume_db_id = resume.id

            job = Job(
                user_id=user_id,
                resume_id=resume_db_id,
                job_id=str(uuid4()),
                content=content,
            )
            session.add(job)
            session.commit()
            result = job.to_dict()
            return result
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to create job: {e}")
            raise
        finally:
            session.close()

    def get_job(self, user_id: int, job_id: str) -> dict[str, Any] | None:
        """Get job by ID (user-isolated)."""
        session = self._get_session()
        try:
            job = session.query(Job).filter(
                Job.user_id == user_id,
                Job.job_id == job_id
            ).first()
            return job.to_dict() if job else None
        finally:
            session.close()

    def update_job(self, user_id: int, job_id: str, updates: dict[str, Any]) -> dict[str, Any] | None:
        """Update a job by ID."""
        session = self._get_session()
        try:
            job = session.query(Job).filter(
                Job.user_id == user_id,
                Job.job_id == job_id
            ).first()

            if not job:
                return None

            for key, value in updates.items():
                if hasattr(job, key):
                    setattr(job, key, value)

            session.commit()
            result = job.to_dict()
            return result
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to update job: {e}")
            raise
        finally:
            session.close()

    def get_jobs_for_resume(self, user_id: int, resume_id: str) -> list[dict[str, Any]]:
        """Get all jobs for a specific resume."""
        session = self._get_session()
        try:
            # Get the resume to find its database ID
            resume = session.query(Resume).filter(
                Resume.user_id == user_id,
                Resume.resume_id == resume_id
            ).first()

            if not resume:
                return []

            # Get jobs for this resume
            jobs = session.query(Job).filter(
                Job.user_id == user_id,
                Job.resume_id == resume.id
            ).all()

            return [job.to_dict() for job in jobs]
        finally:
            session.close()

    def create_improvement(
        self,
        user_id: int,
        original_resume_id: str,
        tailored_resume_id: str,
        job_id: str,
        improvements: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Create an improvement result entry."""
        session = self._get_session()
        try:
            improvement = Improvement(
                user_id=user_id,
                request_id=str(uuid4()),
                original_resume_id=original_resume_id,
                tailored_resume_id=tailored_resume_id,
                job_id=job_id,
                improvements=improvements,
            )
            session.add(improvement)
            session.commit()
            result = improvement.to_dict()
            return result
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to create improvement: {e}")
            raise
        finally:
            session.close()

    def get_improvement_by_tailored_resume(self, user_id: int, tailored_resume_id: str) -> dict[str, Any] | None:
        """Get improvement record by tailored resume ID."""
        session = self._get_session()
        try:
            improvement = session.query(Improvement).filter(
                Improvement.user_id == user_id,
                Improvement.tailored_resume_id == tailored_resume_id
            ).first()
            return improvement.to_dict() if improvement else None
        finally:
            session.close()

    def get_stats(self, user_id: int) -> dict[str, Any]:
        """Get database statistics for a user."""
        session = self._get_session()
        try:
            total_resumes = session.query(Resume).filter(Resume.user_id == user_id).count()
            total_jobs = session.query(Job).filter(Job.user_id == user_id).count()
            total_improvements = session.query(Improvement).filter(Improvement.user_id == user_id).count()
            has_master_resume = session.query(Resume).filter(
                Resume.user_id == user_id,
                Resume.is_master == True
            ).first() is not None

            return {
                "total_resumes": total_resumes,
                "total_jobs": total_jobs,
                "total_improvements": total_improvements,
                "has_master_resume": has_master_resume,
            }
        finally:
            session.close()

    def close(self) -> None:
        """Close database connection."""
        # With SQLAlchemy, sessions are closed automatically
        # Engine disposal is handled by the application shutdown
        pass
