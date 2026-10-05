from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session
from src.core.models import User, AIModelConfiguration
from src.core.services.ai_service import AIService, RuntimeAIConfig
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


def default_ai_configuration(user_id: int) -> AIModelConfiguration:
    """One transient default for the settings receipt and actual transport."""
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

    return AIModelConfiguration(
        user_id=user_id,
        provider=provider,
        model=model,
        endpoint=endpoint,
        model_parameters={"temperature": 0.7, "max_tokens": 1000},
    )



def get_ai_service_dependency(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),  # Now available
):
    """
    Get AI Service instance configured for the specific user.
    If no config exists, creating a default one (or using system default).
    """
    user_id = current_user.id
    if user_id is None:
        raise HTTPException(status_code=401, detail="Authenticated account is unavailable")
    config = (
        db.query(AIModelConfiguration)
        .filter(AIModelConfiguration.user_id == user_id)
        .first()
    )

    if not config:
        config = default_ai_configuration(user_id)

    parameters = config.model_parameters or {}
    model = config.model
    if not isinstance(model, str) or not model.strip():
        raise HTTPException(status_code=409, detail="Choose an AI model in settings before generation")
    if config.provider not in {"ollama", "lm_studio", "openai", "openrouter"}:
        raise HTTPException(
            status_code=409,
            detail="Saved AI provider is unsupported; choose a supported provider in settings",
        )
    runtime = RuntimeAIConfig(
        provider=config.provider,
        model=model,
        endpoint=config.endpoint,
        api_key=config.decrypted_api_key,
        temperature=parameters.get("temperature"),
        max_tokens=parameters.get("max_tokens"),
        reasoning_effort=parameters.get("reasoning_effort"),
    )
    return AIService(runtime, logger)
