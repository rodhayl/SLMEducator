from fastapi import Depends
from sqlalchemy.orm import Session
from src.core.models import User, AIModelConfiguration
from src.core.services.ai_service import AIService
from src.core.services.database import get_db_service as _get_db_service
from src.core.services.settings_config_service import get_settings_service

from src.api.security import get_current_user
import logging

logger = logging.getLogger(__name__)


def get_db_service():
    # Delegate to the core database singleton so tests and the API share the
    # same DatabaseService instance regardless of import path.
    return _get_db_service()


def get_db():
    service = get_db_service()
    session = service.get_session()
    try:
        yield session
    finally:
        session.close()


def get_ai_service_dependency(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),  # Now available
):
    """
    Get AI Service instance configured for the specific user.
    If no config exists, creating a default one (or using system default).
    """
    # Try to find user-specific config
    # In a real app we query DB. For MVP/Migration, we might rely on settings service defaults
    # But AIService expects an AIModelConfig object.

    # Check if user has a config
    config = (
        db.query(AIModelConfiguration)
        .filter(AIModelConfiguration.user_id == current_user.id)
        .first()
    )

    if not config:
        # Create a transient/default config object based on settings.properties
        # or just return a default one.
        settings = get_settings_service()

        # Get provider and model (try both key variations for compatibility)
        provider = settings.get("ai", "default_provider", None) or settings.get(
            "ai", "provider", "ollama"
        )
        model = settings.get("ai", "default_model", None) or settings.get(
            "ai", "model", "llama3"
        )

        # Get endpoint based on provider
        if provider == "lm_studio":
            endpoint = settings.get("ai", "lm_studio.url", "http://localhost:1234")
        elif provider == "ollama":
            endpoint = settings.get("ai", "ollama.url", "http://localhost:11434")
        elif provider == "openrouter":
            endpoint = settings.get(
                "ai", "openrouter.url", "https://openrouter.ai/api/v1/chat/completions"
            )
        else:
            endpoint = settings.get("ai", f"{provider}.url", None)

        config = AIModelConfiguration(
            user_id=current_user.id,
            provider=provider,
            model=model,
            endpoint=endpoint,
            # API key handling omitted for brevity/safety in this transient object
        )

    return AIService(config, logger)
