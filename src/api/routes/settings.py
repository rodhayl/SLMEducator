from fastapi import APIRouter, Body, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session
import logging
from typing import Optional, Dict, Any, List

from src.api.dependencies import get_db, get_ai_service_dependency
from src.api.security import get_current_user, get_optional_current_user
from src.core.models import User, ApplicationConfiguration, AIModelConfiguration
from src.core.services.ai_service import AIProvider, AIService

router = APIRouter(prefix="/api/settings", tags=["settings"])
logger = logging.getLogger(__name__)


class AIConfigModel(BaseModel):
    provider: str = "ollama"
    model: str = "llama3"
    endpoint: Optional[str] = None
    api_key: Optional[str] = None
    # Advanced settings
    temperature: float = 0.7
    max_tokens: int = 1000
    preprocessing_model: Optional[str] = None
    enable_preprocessing: bool = False

    model_config = ConfigDict(from_attributes=True)


class ModelsResponse(BaseModel):
    """Response model for fetching available models"""

    models: List[str]
    provider: str


class AppConfigModel(BaseModel):
    theme: str = "auto"
    language: str = "es"
    font_size: str = "medium"
    enable_animations: bool = True

    model_config = ConfigDict(from_attributes=True)


@router.get("/ai", response_model=AIConfigModel)
async def get_ai_config(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Get User AI Config"""
    config = (
        db.query(AIModelConfiguration)
        .filter(AIModelConfiguration.user_id == current_user.id)
        .first()
    )
    if not config:
        # Return defaults
        return AIConfigModel()

    # Decrypt key for display? Or keep hidden?
    # Usually we don't send back the key unless requested or masked.
    # For now, let's send it back specific for the user to edit.
    key = config.decrypted_api_key
    return AIConfigModel(
        provider=config.provider,
        model=config.model,
        endpoint=config.endpoint,
        api_key=key,
    )


@router.post("/ai", response_model=AIConfigModel)
async def update_ai_config(
    data: AIConfigModel,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update User AI Config"""
    config = (
        db.query(AIModelConfiguration)
        .filter(AIModelConfiguration.user_id == current_user.id)
        .first()
    )
    if not config:
        config = AIModelConfiguration(user_id=current_user.id)
        db.add(config)

    config.provider = data.provider
    config.model = data.model
    config.endpoint = data.endpoint
    if "api_key" in data.model_fields_set:
        if data.api_key:
            config.set_encrypted_api_key(data.api_key)
        else:
            config.api_key = None

    db.commit()
    db.refresh(config)
    return AIConfigModel(
        provider=config.provider,
        model=config.model,
        endpoint=config.endpoint,
        api_key=config.decrypted_api_key,
    )


@router.get("/app", response_model=AppConfigModel)
async def get_app_config(
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
):
    """Get Application/Interface Config"""
    if not current_user:
        return AppConfigModel()

    config = (
        db.query(ApplicationConfiguration)
        .filter(ApplicationConfiguration.user_id == current_user.id)
        .first()
    )
    if not config:
        return AppConfigModel()
    return config


@router.post("/app", response_model=AppConfigModel)
async def update_app_config(
    data: AppConfigModel,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update Application/Interface Config"""
    config = (
        db.query(ApplicationConfiguration)
        .filter(ApplicationConfiguration.user_id == current_user.id)
        .first()
    )
    if not config:
        config = ApplicationConfiguration(user_id=current_user.id)
        db.add(config)

    config.theme = data.theme
    config.language = data.language
    config.font_size = data.font_size
    config.enable_animations = data.enable_animations

    db.commit()
    db.refresh(config)
    return config


@router.get("/translations/{lang}")
async def get_translations(lang: str):
    """Get translation strings for a language"""
    from src.core.services.translation_service import get_translation_service

    service = get_translation_service()

    # Force load checks existence
    if not service.load_language(lang):
        raise HTTPException(status_code=404, detail=f"Language '{lang}' not found")

    # Manually retrieve dict to return raw JSON
    # Access internal store directly or add a new method.
    # Since we have logic in get() for fallbacks, passing raw JSON to frontend
    # means frontend must handle fallbacks or we return a merged dict?
    # For simplicitly, let's return the raw loaded file.

    import json

    trans_file = service.translations_dir / f"{lang}.json"
    if not trans_file.exists():
        raise HTTPException(status_code=404, detail="Translation file missing")

    with open(trans_file, "r", encoding="utf-8") as f:
        return json.load(f)


@router.get("/ai/models", response_model=ModelsResponse)
async def fetch_models(
    provider: Optional[str] = Query(
        None, description="AI provider to fetch models from"
    ),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Fetch available models from the specified AI provider.

    If no provider is specified, uses the user's configured provider.
    Supports: ollama, lm_studio, openai, anthropic, openrouter
    """
    try:
        # Get user's AI configuration for defaults
        config = (
            db.query(AIModelConfiguration)
            .filter(AIModelConfiguration.user_id == current_user.id)
            .first()
        )

        # Determine which provider to use
        target_provider = provider or (config.provider if config else "ollama")

        # Get AI service instance
        ai_service = get_ai_service_dependency(current_user, db)

        # Fetch models from the provider
        try:
            target_enum = AIProvider(target_provider)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Invalid provider: {target_provider}. "
                    "Valid options: ollama, lm_studio, openai, anthropic, openrouter"
                ),
            )

        models = ai_service.fetch_available_models(provider=target_enum)

        return ModelsResponse(models=models, provider=target_provider)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch models: {str(e)}")


def _build_ai_service(
    config_override: Optional[AIConfigModel], current_user: User, db: Session
) -> AIService:
    if config_override:
        temp_config = AIModelConfiguration(
            user_id=current_user.id,
            provider=config_override.provider,
            model=config_override.model,
            endpoint=config_override.endpoint or None,
        )
        if config_override.api_key:
            temp_config.set_encrypted_api_key(config_override.api_key)
        return AIService(temp_config, logger)
    return get_ai_service_dependency(current_user, db)


def _run_ai_connection_test(
    config_override: Optional[AIConfigModel], current_user: User, db: Session
) -> Dict[str, Any]:
    import time

    ai_service = None
    try:
        ai_service = _build_ai_service(config_override, current_user, db)
        start_time = time.time()

        response = ai_service.generate_content(
            context="Say 'Hello, I am connected!' in exactly those words.",
            max_tokens=50,
            temperature=0.1,
        )

        elapsed = time.time() - start_time

        return {
            "status": "connected",
            "response_time_ms": round(elapsed * 1000),
            "model": ai_service.config.model,
            "provider": ai_service.config.provider,
            "test_response": response[:100] if response else None,
        }
    except Exception as e:
        return {"status": "error", "error": str(e), "model": None, "provider": None}
    finally:
        if ai_service:
            try:
                ai_service.close()
            except Exception:
                pass


@router.post("/ai/test")
async def test_ai_connection_with_config(
    config: Optional[AIConfigModel] = Body(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Test the AI connection with a simple prompt using current form values.
    """
    return _run_ai_connection_test(config, current_user, db)


@router.get("/ai/test")
async def test_ai_connection(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """
    Test the AI connection with a simple prompt.

    Returns connection status and response time.
    """
    return _run_ai_connection_test(None, current_user, db)
