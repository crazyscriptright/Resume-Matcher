"""Service to initialize LLM database and load configuration on startup."""

import logging
from typing import TYPE_CHECKING

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.models.llm_quota import LLMBase, LLMModel, LLMProviderApiKey
from app.services.config_loader import load_all_models, load_all_provider_keys

if TYPE_CHECKING:
    from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


class LLMDatabaseInitializer:
    """Initialize LLM database tables and load configuration."""

    def __init__(self, engine: "Engine"):
        """Initialize with SQLAlchemy engine.
        
        Args:
            engine: SQLAlchemy engine instance
        """
        self.engine = engine

    def create_tables(self) -> None:
        """Create all LLM database tables if they don't exist."""
        try:
            LLMBase.metadata.create_all(self.engine)
            logger.info("✅ LLM database tables created/verified")
        except Exception as e:
            logger.error(f"❌ Failed to create LLM tables: {e}")
            raise

    def load_models_from_env(self, db: Session) -> int:
        """Load model configuration from .env into database.
        
        Args:
            db: SQLAlchemy session
        
        Returns:
            Number of models loaded
        """
        models = load_all_models()
        loaded_count = 0
        
        for model_config in models:
            # Check if model already exists
            stmt = select(LLMModel).where(LLMModel.name == model_config.name)
            existing = db.execute(stmt).scalar_one_or_none()
            
            if existing:
                # Update existing model
                existing.provider = model_config.provider
                existing.priority = model_config.priority
                existing.tpm_limit = model_config.tpm_limit
                existing.rpm_limit = model_config.rpm_limit
                existing.rpd_limit = model_config.rpd_limit
                existing.tpd_limit = model_config.tpd_limit
                existing.active = True
                logger.info(f"📝 Updated model: {model_config.name}")
            else:
                # Create new model
                new_model = LLMModel(
                    name=model_config.name,
                    provider=model_config.provider,
                    priority=model_config.priority,
                    tpm_limit=model_config.tpm_limit,
                    rpm_limit=model_config.rpm_limit,
                    rpd_limit=model_config.rpd_limit,
                    tpd_limit=model_config.tpd_limit,
                    active=True,
                )
                db.add(new_model)
                logger.info(f"🆕 Added model: {model_config.name} (priority {model_config.priority})")
            
            loaded_count += 1
        
        db.commit()
        logger.info(f"✅ Loaded {loaded_count} LLM models from .env")
        return loaded_count

    def load_provider_keys_from_env(self, db: Session) -> int:
        """Load provider API keys from .env with smart sync.
        
        Smart detection:
        - New position: Creates fresh key with 0 quota
        - Key replacement (different value at same position): Archives old, creates fresh new
        - Unchanged key: No action, history preserved
        - Removed keys: Deleted from active pool but usage history archived
        
        Args:
            db: SQLAlchemy session
        
        Returns:
            Number of keys synced
        """
        provider_keys = load_all_provider_keys()
        synced_count = 0
        
        for provider, keys_config in provider_keys.items():
            # Get new keys from .env
            env_keys = keys_config.keys
            
            # Track which positions were updated
            for key_index, new_key in enumerate(env_keys, start=1):
                # Get existing key at this position
                stmt = select(LLMProviderApiKey).where(
                    and_(
                        LLMProviderApiKey.provider == provider,
                        LLMProviderApiKey.key_index == key_index,
                        LLMProviderApiKey.is_active == True,  # Only check active keys
                    )
                )
                existing = db.execute(stmt).scalar_one_or_none()
                
                if not existing:
                    # ✅ New position: create fresh key with 0 quota
                    new_entry = LLMProviderApiKey(
                        provider=provider,
                        api_key=new_key,
                        key_index=key_index,
                        is_active=True,
                    )
                    db.add(new_entry)
                    logger.info(f"✅ Added {provider} KEY_{key_index} (fresh)")
                    synced_count += 1
                
                elif existing.api_key != new_key:
                    # ⭐ KEY REPLACEMENT: Different key at same position
                    # Archive old key (disable it but keep history)
                    existing.is_active = False
                    logger.info(
                        f"📦 Archived {provider} KEY_{key_index} (old key, usage history preserved)"
                    )
                    
                    # Create new entry with same index but fresh quota
                    new_entry = LLMProviderApiKey(
                        provider=provider,
                        api_key=new_key,
                        key_index=key_index,
                        is_active=True,
                    )
                    db.add(new_entry)
                    logger.info(f"✨ Added {provider} KEY_{key_index} NEW (quota reset)")
                    synced_count += 1
                
                else:
                    # Same key, no action needed
                    logger.info(f"ℹ️ {provider} KEY_{key_index} unchanged (history preserved)")
            
            # Handle removed keys: find active keys beyond new list length
            if len(env_keys) > 0:
                # Get all active keys for this provider
                stmt = select(LLMProviderApiKey).where(
                    and_(
                        LLMProviderApiKey.provider == provider,
                        LLMProviderApiKey.is_active == True,
                    )
                )
                all_active_keys = db.execute(stmt).scalars().all()
                
                # If we have keys beyond the new list length, disable them
                for existing_key in all_active_keys:
                    if existing_key.key_index > len(env_keys):
                        existing_key.is_active = False
                        logger.info(
                            f"🗑️ Disabled {provider} KEY_{existing_key.key_index} (removed from .env, history kept)"
                        )
        
        db.commit()
        logger.info(f"✅ Synced {synced_count} API keys (replacements handled, history preserved)")
        return synced_count

    def initialize_all(self, db: Session) -> bool:
        """Full initialization: create tables and load config.
        
        Args:
            db: SQLAlchemy session
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Create tables
            self.create_tables()
            
            # Load models
            models_count = self.load_models_from_env(db)
            
            # Load API keys
            keys_count = self.load_provider_keys_from_env(db)
            
            logger.info(
                f"✅ LLM initialization complete: {models_count} models, {keys_count} API keys"
            )
            return True
        
        except Exception as e:
            logger.error(f"❌ LLM initialization failed: {e}")
            return False
