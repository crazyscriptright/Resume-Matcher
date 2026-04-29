"""Firebase Firestore database layer for JSON storage."""

import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore_v1.base_query import FieldFilter

from app.config import settings

logger = logging.getLogger(__name__)


def _init_firebase() -> firestore.firestore.Client:
    """Initialize Firebase Admin SDK from FIREBASE_SERVICE_ACCOUNT env var.

    The env var must contain a JSON string with the service account credentials.
    Returns a Firestore client.
    """
    raw = os.environ.get("FIREBASE_SERVICE_ACCOUNT", "")
    if not raw:
        raise RuntimeError(
            "FIREBASE_SERVICE_ACCOUNT environment variable is not set. "
            "Set it to a JSON string containing your Firebase service account credentials."
        )

    try:
        service_account_info = json.loads(raw)
    except json.JSONDecodeError as e:
        raise RuntimeError(
            f"FIREBASE_SERVICE_ACCOUNT is not valid JSON: {e}"
        ) from e

    cred = credentials.Certificate(service_account_info)

    # Only initialize if not already done (prevents duplicate-app errors on reload)
    try:
        firebase_admin.get_app()
    except ValueError:
        firebase_admin.initialize_app(cred)

    return firestore.client()


class Database:
    """Firestore wrapper for resume matcher data.

    Mirrors the original TinyDB API so all routers work without changes.
    Each 'table' is a Firestore top-level collection.
    """

    _master_resume_lock = asyncio.Lock()

    # Collection names
    RESUMES = "resumes"
    JOBS = "jobs"
    IMPROVEMENTS = "improvements"

    def __init__(self) -> None:
        self._client: firestore.firestore.Client | None = None

    @property
    def client(self) -> firestore.firestore.Client:
        """Lazy initialization of Firestore client."""
        if self._client is None:
            self._client = _init_firebase()
            logger.info("Firestore client initialized successfully")
        return self._client

    # ── helpers ──────────────────────────────────────────────────────────

    def _col(self, name: str):
        """Shorthand for collection reference."""
        return self.client.collection(name)

    @staticmethod
    def _doc_to_dict(doc_snapshot) -> dict[str, Any] | None:
        """Convert a Firestore DocumentSnapshot to a plain dict."""
        if doc_snapshot.exists:
            return doc_snapshot.to_dict()
        return None

    def close(self) -> None:
        """Close database connection (no-op for Firestore — kept for API compat)."""
        self._client = None

    # ── Resume operations ────────────────────────────────────────────────

    def create_resume(
        self,
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
        """Create a new resume entry.

        processing_status: "pending", "processing", "ready", "failed"
        """
        resume_id = str(uuid4())
        now = datetime.now(timezone.utc).isoformat()

        doc: dict[str, Any] = {
            "resume_id": resume_id,
            "content": content,
            "content_type": content_type,
            "filename": filename,
            "is_master": is_master,
            "parent_id": parent_id,
            "processed_data": processed_data,
            "processing_status": processing_status,
            "cover_letter": cover_letter,
            "outreach_message": outreach_message,
            "title": title,
            "created_at": now,
            "updated_at": now,
        }
        if original_markdown is not None:
            doc["original_markdown"] = original_markdown

        self._col(self.RESUMES).document(resume_id).set(doc)
        return doc

    async def create_resume_atomic_master(
        self,
        content: str,
        content_type: str = "md",
        filename: str | None = None,
        processed_data: dict[str, Any] | None = None,
        processing_status: str = "pending",
        cover_letter: str | None = None,
        outreach_message: str | None = None,
        original_markdown: str | None = None,
    ) -> dict[str, Any]:
        """Create a new resume with atomic master assignment.

        Uses an asyncio.Lock to prevent race conditions when multiple uploads
        happen concurrently and both try to become master. This avoids blocking
        the FastAPI event loop unlike threading.Lock.
        """
        async with self._master_resume_lock:
            current_master = self.get_master_resume()
            is_master = current_master is None

            # Recovery behavior: if the current master is stuck in failed or
            # processing state, promote the next upload to become the new master.
            if current_master and current_master.get("processing_status") in ("failed", "processing"):
                self._col(self.RESUMES).document(
                    current_master["resume_id"]
                ).update({"is_master": False})
                is_master = True

            return self.create_resume(
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

    def get_resume(self, resume_id: str) -> dict[str, Any] | None:
        """Get resume by ID."""
        doc = self._col(self.RESUMES).document(resume_id).get()
        return self._doc_to_dict(doc)

    def get_master_resume(self) -> dict[str, Any] | None:
        """Get the master resume if exists."""
        docs = (
            self._col(self.RESUMES)
            .where(filter=FieldFilter("is_master", "==", True))
            .limit(1)
            .stream()
        )
        for doc in docs:
            return doc.to_dict()
        return None

    def update_resume(self, resume_id: str, updates: dict[str, Any]) -> dict[str, Any]:
        """Update resume by ID.

        Raises:
            ValueError: If resume not found.
        """
        updates["updated_at"] = datetime.now(timezone.utc).isoformat()
        doc_ref = self._col(self.RESUMES).document(resume_id)

        # Verify existence before updating
        if not doc_ref.get().exists:
            raise ValueError(f"Resume not found: {resume_id}")

        doc_ref.update(updates)

        result = self.get_resume(resume_id)
        if not result:
            raise ValueError(f"Resume disappeared after update: {resume_id}")

        return result

    def delete_resume(self, resume_id: str) -> bool:
        """Delete resume by ID."""
        doc_ref = self._col(self.RESUMES).document(resume_id)
        if not doc_ref.get().exists:
            return False
        doc_ref.delete()
        return True

    def list_resumes(self) -> list[dict[str, Any]]:
        """List all resumes."""
        docs = self._col(self.RESUMES).stream()
        return [doc.to_dict() for doc in docs]

    def set_master_resume(self, resume_id: str) -> bool:
        """Set a resume as the master, unsetting any existing master.

        Returns False if the resume doesn't exist.
        """
        # First verify the target resume exists
        target_ref = self._col(self.RESUMES).document(resume_id)
        if not target_ref.get().exists:
            logger.warning("Cannot set master: resume %s not found", resume_id)
            return False

        # Unset current master(s)
        masters = (
            self._col(self.RESUMES)
            .where(filter=FieldFilter("is_master", "==", True))
            .stream()
        )
        for doc in masters:
            doc.reference.update({"is_master": False})

        # Set new master
        target_ref.update({"is_master": True})
        return True

    # ── Job operations ───────────────────────────────────────────────────

    def create_job(self, content: str, resume_id: str | None = None) -> dict[str, Any]:
        """Create a new job description entry."""
        job_id = str(uuid4())
        now = datetime.now(timezone.utc).isoformat()

        doc = {
            "job_id": job_id,
            "content": content,
            "resume_id": resume_id,
            "created_at": now,
        }
        self._col(self.JOBS).document(job_id).set(doc)
        return doc

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        """Get job by ID."""
        doc = self._col(self.JOBS).document(job_id).get()
        return self._doc_to_dict(doc)

    def update_job(self, job_id: str, updates: dict[str, Any]) -> dict[str, Any] | None:
        """Update a job by ID."""
        doc_ref = self._col(self.JOBS).document(job_id)
        if not doc_ref.get().exists:
            return None
        doc_ref.update(updates)
        return self.get_job(job_id)

    # ── Improvement operations ───────────────────────────────────────────

    def create_improvement(
        self,
        original_resume_id: str,
        tailored_resume_id: str,
        job_id: str,
        improvements: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Create an improvement result entry."""
        request_id = str(uuid4())
        now = datetime.now(timezone.utc).isoformat()

        doc = {
            "request_id": request_id,
            "original_resume_id": original_resume_id,
            "tailored_resume_id": tailored_resume_id,
            "job_id": job_id,
            "improvements": improvements,
            "created_at": now,
        }
        self._col(self.IMPROVEMENTS).document(request_id).set(doc)
        return doc

    def get_improvement_by_tailored_resume(
        self, tailored_resume_id: str
    ) -> dict[str, Any] | None:
        """Get improvement record by tailored resume ID.

        This is used to retrieve the job context for on-demand
        cover letter and outreach message generation.
        """
        docs = (
            self._col(self.IMPROVEMENTS)
            .where(filter=FieldFilter("tailored_resume_id", "==", tailored_resume_id))
            .limit(1)
            .stream()
        )
        for doc in docs:
            return doc.to_dict()
        return None

    # ── Stats ────────────────────────────────────────────────────────────

    def get_stats(self) -> dict[str, Any]:
        """Get database statistics."""
        return {
            "total_resumes": len(list(self._col(self.RESUMES).stream())),
            "total_jobs": len(list(self._col(self.JOBS).stream())),
            "total_improvements": len(list(self._col(self.IMPROVEMENTS).stream())),
            "has_master_resume": self.get_master_resume() is not None,
        }

    def reset_database(self) -> None:
        """Reset the database by deleting all documents and clearing uploads."""
        # Delete all documents in each collection
        for collection_name in (self.RESUMES, self.JOBS, self.IMPROVEMENTS):
            docs = self._col(collection_name).stream()
            for doc in docs:
                doc.reference.delete()

        # Clear uploads directory
        uploads_dir = settings.data_dir / "uploads"
        if uploads_dir.exists():
            import shutil

            shutil.rmtree(uploads_dir)
            uploads_dir.mkdir(parents=True, exist_ok=True)


# Global database instance
db = Database()
