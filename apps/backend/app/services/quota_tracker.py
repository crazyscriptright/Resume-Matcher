"""Service to track LLM quota usage."""

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.models.llm_quota import LLMModel, LLMUsageTracking

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


class QuotaTracker:
    """Track and check LLM quota usage (TPM, RPM, RPD, TPD)."""

    def __init__(self, db: Session):
        """Initialize quota tracker.
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db

    def get_current_datetime(self) -> datetime:
        """Get current datetime in UTC."""
        return datetime.now(timezone.utc)

    def get_current_date_str(self) -> str:
        """Get current date as YYYY-MM-DD string."""
        return self.get_current_datetime().strftime("%Y-%m-%d")

    def get_current_hour(self) -> int:
        """Get current hour (0-23)."""
        return self.get_current_datetime().hour

    def get_or_create_usage_tracking(
        self, provider: str, model_name: str, api_key: str
    ) -> LLMUsageTracking:
        """Get or create usage tracking record for this hour.
        
        Args:
            provider: Provider name ("openai", "gemini")
            model_name: Model name
            api_key: Actual API key value (for tracking)
        
        Returns:
            LLMUsageTracking record
        """
        date_str = self.get_current_date_str()
        hour = self.get_current_hour()
        
        # Try to find existing record by provider, model, and actual API key
        stmt = select(LLMUsageTracking).where(
            and_(
                LLMUsageTracking.provider == provider,
                LLMUsageTracking.model_name == model_name,
                LLMUsageTracking.api_key == api_key,  # ⭐ Track by actual key value
                LLMUsageTracking.date == date_str,
                LLMUsageTracking.hour == hour,
            )
        )
        
        existing = self.db.execute(stmt).scalar_one_or_none()
        if existing:
            return existing
        
        # Create new record
        tracking = LLMUsageTracking(
            provider=provider,
            model_name=model_name,
            api_key=api_key,
            date=date_str,
            hour=hour,
            tokens_used=0,
            requests_count=0,
        )
        self.db.add(tracking)
        self.db.commit()
        return tracking

    def check_quota_available(
        self, model_name: str, api_key: str, estimated_tokens: int = 0
    ) -> tuple[bool, str]:
        """Check if model quota is available for this API key.
        
        Args:
            model_name: Model name to check
            api_key: Actual API key value to use
            estimated_tokens: Estimated tokens for request
        
        Returns:
            Tuple of (is_available, reason)
            - (True, "") if quota available
            - (False, reason) if quota exceeded
        """
        # Get model configuration
        stmt = select(LLMModel).where(LLMModel.name == model_name)
        model = self.db.execute(stmt).scalar_one_or_none()
        
        if not model:
            return False, f"Model {model_name} not found"
        
        if not model.active:
            return False, f"Model {model_name} is disabled"
        
        provider = model.provider
        
        # Get current usage tracking for this specific API key
        tracking = self.get_or_create_usage_tracking(provider, model_name, api_key)
        
        # Check hourly limits (RPM, TPM)
        if model.rpm_limit is not None and tracking.requests_count >= model.rpm_limit:
            return False, f"Model {model_name} hourly RPM limit ({model.rpm_limit}) exceeded"
        
        if model.tpm_limit is not None and tracking.tokens_used + estimated_tokens > model.tpm_limit:
            return False, f"Model {model_name} hourly TPM limit ({model.tpm_limit}) would be exceeded"
        
        # Check daily limits (RPD, TPD)
        if model.rpd_limit is not None:
            daily_requests = self._get_daily_request_count(provider, model_name, api_key)
            if daily_requests >= model.rpd_limit:
                return False, f"Model {model_name} daily RPD limit ({model.rpd_limit}) exceeded"
        
        if model.tpd_limit is not None:
            daily_tokens = self._get_daily_token_count(provider, model_name, api_key)
            if daily_tokens + estimated_tokens > model.tpd_limit:
                return False, f"Model {model_name} daily TPD limit ({model.tpd_limit}) would be exceeded"
        
        return True, ""

    def increment_usage(
        self,
        model_name: str,
        api_key: str,
        tokens_used: int,
        requests_count: int = 1,
    ) -> None:
        """Increment usage counters for this API key.
        
        Args:
            model_name: Model name
            api_key: Actual API key value
            tokens_used: Number of tokens used
            requests_count: Number of requests (default 1)
        """
        stmt = select(LLMModel).where(LLMModel.name == model_name)
        model = self.db.execute(stmt).scalar_one_or_none()
        
        if not model:
            return
        
        provider = model.provider
        tracking = self.get_or_create_usage_tracking(provider, model_name, api_key)
        
        # Update counters
        tracking.tokens_used += tokens_used
        tracking.requests_count += requests_count
        tracking.last_request_at = self.get_current_datetime()
        
        self.db.commit()

    def reset_hourly_limits(self) -> None:
        """Reset hourly usage counters.
        
        This should be called hourly via APScheduler.
        Only resets records older than 1 hour.
        """
        current_date = self.get_current_date_str()
        current_hour = self.get_current_hour()
        
        # Reset records from previous hour
        previous_hour = (current_hour - 1) % 24
        
        stmt = select(LLMUsageTracking).where(
            and_(
                LLMUsageTracking.date == current_date,
                LLMUsageTracking.hour == previous_hour,
            )
        )
        
        records = self.db.execute(stmt).scalars().all()
        for record in records:
            record.tokens_used = 0
            record.requests_count = 0
        
        self.db.commit()

    def reset_daily_limits(self) -> None:
        """Reset daily usage counters.
        
        This should be called once per day via APScheduler.
        """
        # Get yesterday's date
        current_date = self.get_current_date_str()
        
        stmt = select(LLMUsageTracking).where(LLMUsageTracking.date < current_date)
        
        records = self.db.execute(stmt).scalars().all()
        for record in records:
            record.tokens_used = 0
            record.requests_count = 0
        
        self.db.commit()

    def _get_daily_request_count(self, provider: str, model_name: str, api_key: str) -> int:
        """Get total requests for today for this specific API key.
        
        Args:
            provider: Provider name
            model_name: Model name
            api_key: Actual API key value
        
        Returns:
            Total request count for today
        """
        current_date = self.get_current_date_str()
        
        stmt = select(LLMUsageTracking).where(
            and_(
                LLMUsageTracking.provider == provider,
                LLMUsageTracking.model_name == model_name,
                LLMUsageTracking.api_key == api_key,
                LLMUsageTracking.date == current_date,
            )
        )
        
        records = self.db.execute(stmt).scalars().all()
        return sum(r.requests_count for r in records)

    def _get_daily_token_count(self, provider: str, model_name: str, api_key: str) -> int:
        """Get total tokens for today for this specific API key.
        
        Args:
            provider: Provider name
            model_name: Model name
            api_key: Actual API key value
        
        Returns:
            Total token count for today
        """
        current_date = self.get_current_date_str()
        
        stmt = select(LLMUsageTracking).where(
            and_(
                LLMUsageTracking.provider == provider,
                LLMUsageTracking.model_name == model_name,
                LLMUsageTracking.api_key == api_key,
                LLMUsageTracking.date == current_date,
            )
        )
        
        records = self.db.execute(stmt).scalars().all()
        return sum(r.tokens_used for r in records)
