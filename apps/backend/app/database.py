"""Firebase Firestore database layer for JSON storage."""

import asyncio
import logging
import os
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore_v1.base_query import FieldFilter

from app.config import settings
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load environment variables from .env file so os.environ is populated
load_dotenv()

# Initialize Firebase App
try:
    if "FIREBASE_SERVICE_ACCOUNT" in os.environ:
        service_account_info = json.loads(os.environ["FIREBASE_SERVICE_ACCOUNT"])
        cred = credentials.Certificate(service_account_info)
        
        # Check if already initialized to prevent errors on reload
        if not firebase_admin._apps:
            firebase_admin.initialize_app(cred)
            logger.info("Firebase Admin SDK initialized successfully.")
    else:
        logger.warning("FIREBASE_SERVICE_ACCOUNT environment variable not found.")
except Exception as e:
    logger.error(f"Failed to initialize Firebase Admin SDK: {e}")

class Database:
    """Firebase Firestore wrapper for resume matcher data."""

    _master_resume_lock = asyncio.Lock()

    def __init__(self):
        try:
            self._db = firestore.client()
        except Exception as e:
            logger.error(f"Failed to get Firestore client: {e}")
            self._db = None

    @property
    def resumes(self):
        if not self._db:
            raise RuntimeError("Firestore client not initialized.")
        return self._db.collection("resumes")

    @property
    def jobs(self):
        if not self._db:
            raise RuntimeError("Firestore client not initialized.")
        return self._db.collection("jobs")

    @property
    def improvements(self):
        if not self._db:
            raise RuntimeError("Firestore client not initialized.")
        return self._db.collection("improvements")

    def close(self) -> None:
        """Close database connection. (No-op for Firestore)."""
        pass

    # Resume operations
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
            
        self.resumes.document(resume_id).set(doc)
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
        happen concurrently and both try to become master.
        """
        async with self._master_resume_lock:
            current_master = self.get_master_resume()
            is_master = current_master is None

            # Recovery behavior: if the current master is stuck in failed or
            # processing state, promote the next upload to become the new master.
            if current_master and current_master.get("processing_status") in ("failed", "processing"):
                self.update_resume(current_master["resume_id"], {"is_master": False})
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
        doc_ref = self.resumes.document(resume_id).get()
        if doc_ref.exists:
            return doc_ref.to_dict()
        return None

    def get_master_resume(self) -> dict[str, Any] | None:
        """Get the master resume if exists."""
        docs = self.resumes.where(filter=FieldFilter("is_master", "==", True)).limit(1).stream()
        for doc in docs:
            return doc.to_dict()
        return None

    def update_resume(self, resume_id: str, updates: dict[str, Any]) -> dict[str, Any]:
        """Update resume by ID.

        Raises:
            ValueError: If resume not found.
        """
        updates["updated_at"] = datetime.now(timezone.utc).isoformat()
        doc_ref = self.resumes.document(resume_id)
        
        # Verify it exists
        if not doc_ref.get().exists:
            raise ValueError(f"Resume not found: {resume_id}")
            
        doc_ref.update(updates)
        
        result = self.get_resume(resume_id)
        if not result:
            raise ValueError(f"Resume disappeared after update: {resume_id}")

        return result

    def delete_resume(self, resume_id: str) -> bool:
        """Delete resume by ID."""
        doc_ref = self.resumes.document(resume_id)
        if doc_ref.get().exists:
            doc_ref.delete()
            return True
        return False

    def list_resumes(self) -> list[dict[str, Any]]:
        """List all resumes."""
        docs = self.resumes.stream()
        # Ensure we return a list of dicts, sorted by updated_at descending
        resumes = [doc.to_dict() for doc in docs]
        return sorted(resumes, key=lambda x: x.get("updated_at", ""), reverse=True)

    def set_master_resume(self, resume_id: str) -> bool:
        """Set a resume as the master, unsetting any existing master.

        Returns False if the resume doesn't exist.
        """
        # First verify the target resume exists
        target = self.get_resume(resume_id)
        if not target:
            logger.warning("Cannot set master: resume %s not found", resume_id)
            return False

        # Unset current master(s)
        current_masters = self.resumes.where(filter=FieldFilter("is_master", "==", True)).stream()
        for master in current_masters:
            master.reference.update({"is_master": False})
            
        # Set new master
        self.resumes.document(resume_id).update({"is_master": True})
        return True

    # Job operations
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
        self.jobs.document(job_id).set(doc)
        return doc

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        """Get job by ID."""
        doc_ref = self.jobs.document(job_id).get()
        if doc_ref.exists:
            return doc_ref.to_dict()
        return None

    def update_job(self, job_id: str, updates: dict[str, Any]) -> dict[str, Any] | None:
        """Update a job by ID."""
        doc_ref = self.jobs.document(job_id)
        if not doc_ref.get().exists:
            return None
        doc_ref.update(updates)
        return self.get_job(job_id)

    # Improvement operations
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
        self.improvements.document(request_id).set(doc)
        return doc

    def get_improvement_by_tailored_resume(
        self, tailored_resume_id: str
    ) -> dict[str, Any] | None:
        """Get improvement record by tailored resume ID.

        This is used to retrieve the job context for on-demand
        cover letter and outreach message generation.
        """
        docs = self.improvements.where(filter=FieldFilter("tailored_resume_id", "==", tailored_resume_id)).limit(1).stream()
        for doc in docs:
            return doc.to_dict()
        return None

    # Stats
    def get_stats(self) -> dict[str, Any]:
        """Get database statistics."""
        # Note: getting count of collection in Firestore requires iterating or aggregation query
        # Since we expect low volume for a personal app, we can use simple count queries
        from google.cloud.firestore_v1.aggregation import AggregationQuery
        
        # Helper to get count
        def get_count(collection_ref):
            count_query = collection_ref.count()
            results = count_query.get()
            return results[0][0].value

        try:
            return {
                "total_resumes": get_count(self.resumes),
                "total_jobs": get_count(self.jobs),
                "total_improvements": get_count(self.improvements),
                "has_master_resume": self.get_master_resume() is not None,
            }
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {
                "total_resumes": 0,
                "total_jobs": 0,
                "total_improvements": 0,
                "has_master_resume": False,
            }

    def reset_database(self) -> None:
        """Reset the database by deleting all documents in collections and clearing uploads."""
        def delete_collection(collection_ref, batch_size=50):
            docs = collection_ref.limit(batch_size).stream()
            deleted = 0
            for doc in docs:
                doc.reference.delete()
                deleted += 1
            if deleted >= batch_size:
                return delete_collection(collection_ref, batch_size)
                
        delete_collection(self.resumes)
        delete_collection(self.jobs)
        delete_collection(self.improvements)

        # Clear uploads directory
        uploads_dir = settings.data_dir / "uploads"
        if uploads_dir.exists():
            import shutil
            shutil.rmtree(uploads_dir)
            uploads_dir.mkdir(parents=True, exist_ok=True)


# Global database instance
db = Database()
