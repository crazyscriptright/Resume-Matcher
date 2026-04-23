"""SQLAlchemy models for LLM multi-model routing and quota tracking."""

from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint, Index
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class LLMBase(DeclarativeBase):
    """Base class for LLM-specific SQLAlchemy models."""

    pass


class LLMModel(LLMBase):
    """LLM model configuration with flexible quota limits."""

    __tablename__ = "llm_models"
    __table_args__ = (UniqueConstraint("name", name="uq_llm_model_name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # "openai", "gemini"
    priority: Mapped[int] = mapped_column(Integer, nullable=False)  # 1=highest, 8=lowest
    tpm_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)  # tokens/min, NULL=unlimited
    rpm_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)  # requests/min, NULL=unlimited
    rpd_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)  # requests/day, NULL=unlimited
    tpd_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)  # tokens/day, NULL=unlimited
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class LLMProviderApiKey(LLMBase):
    """API keys grouped by provider (shared across all models of same provider)."""

    __tablename__ = "llm_provider_api_keys"
    __table_args__ = (
        UniqueConstraint("provider", "key_index", name="uq_provider_key_index"),
        Index("ix_provider_active", "provider", "is_active"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    provider: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # "openai", "gemini"
    api_key: Mapped[str] = mapped_column(String(1024), nullable=False)  # encrypted in production
    key_index: Mapped[int] = mapped_column(Integer, nullable=False)  # 1, 2, 3, 4...
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )


class LLMUsageTracking(LLMBase):
    """Track usage per provider-key PER HOUR (for TPM/RPM limits) and PER DAY (for TPD/RPD limits).
    
    Uses actual API key value (not position) so when keys are rotated, usage history is preserved.
    """

    __tablename__ = "llm_usage_tracking"
    __table_args__ = (
        UniqueConstraint("provider", "model_name", "api_key", "date", "hour", name="uq_usage_hour"),
        Index("ix_usage_date", "date"),
        Index("ix_usage_provider", "provider"),
        Index("ix_usage_api_key", "api_key"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    provider: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # "openai", "gemini"
    model_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)  # for per-model tracking
    api_key: Mapped[str] = mapped_column(String(1024), nullable=False, index=True)  # ⭐ Actual key value for tracking
    date: Mapped[str] = mapped_column(String(10), nullable=False)  # YYYY-MM-DD for daily reset
    hour: Mapped[int] = mapped_column(Integer, nullable=False)  # 0-23 for hourly reset
    tokens_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # cumulative for this hour
    requests_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # cumulative for this hour
    last_request_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    quota_exhausted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class LLMUserSession(LLMBase):
    """Audit log for LLM requests (which model was used, fallback chain, etc)."""

    __tablename__ = "llm_user_sessions"
    __table_args__ = (
        Index("ix_user_session_created", "user_id", "created_at"),
        Index("ix_user_session_status", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)  # NULL for system requests
    model_attempted: Mapped[str] = mapped_column(String(255), nullable=False)  # which model user tried
    model_used: Mapped[str] = mapped_column(String(255), nullable=False)  # which model actually served request
    provider: Mapped[str] = mapped_column(String(50), nullable=False)  # "openai", "gemini"
    api_key_index: Mapped[int] = mapped_column(Integer, nullable=False)  # which key was used (1,2,3...)
    status: Mapped[str] = mapped_column(String(50), nullable=False)  # "success", "fallback_used", "queued"
    fallback_chain: Mapped[list[str]] = mapped_column(JSON, nullable=True)  # ["gpt-5-pro", "gemini-3", ...]
    tokens_predicted: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tokens_actual: Mapped[int | None] = mapped_column(Integer, nullable=True)
    prompt_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    completion_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)  # request duration
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True
    )


class LLMRequestQueue(LLMBase):
    """Queue for requests when all models are exhausted."""

    __tablename__ = "llm_request_queue"
    __table_args__ = (Index("ix_queue_status", "status"), Index("ix_queue_created", "created_at"))

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    request_data: Mapped[dict] = mapped_column(JSON, nullable=False)  # Serialized request payload
    model_requested: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="queued", nullable=False)  # queued, processing, completed, failed
    fallback_models_tried: Mapped[list[str]] = mapped_column(JSON, nullable=True)
    result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_retries: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
