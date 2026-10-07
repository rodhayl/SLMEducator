from fastapi import APIRouter, Body, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session
import logging
from typing import Optional, Dict, Any, List, Literal

from src.api.dependencies import get_db, get_ai_service_dependency, default_ai_configuration
from src.api.security import get_current_user, get_optional_current_user
from src.core.models import User, ApplicationConfiguration, AIModelConfiguration
from src.core.services.ai_service import AIProvider, AIService, RuntimeAIConfig

router = APIRouter(prefix="/api/settings", tags=["settings"])
logger = logging.getLogger(__name__)


class AIConfigModel(BaseModel):
    provider: Literal["ollama", "lm_studio", "openai", "openrouter"] = "ollama"
    model: str = "llama3"
    endpoint: Optional[str] = None
    api_key: Optional[str] = None
    has_api_key: bool = False
    clear_api_key: bool = False
    # Advanced settings
    temperature: float = Field(default=0.7, ge=0, le=2)
    max_tokens: int = Field(default=1000, ge=1, le=16384)
    reasoning_effort: Optional[Literal["none"]] = None
    # Accepted only to migrate old clients; never persisted or advertised active.
    preprocessing_model: Optional[str] = Field(default=None, exclude=True)
    enable_preprocessing: Optional[bool] = Field(default=None, exclude=True)
    compatibility_warnings: List[str] = Field(default_factory=list)

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
        config = default_ai_configuration(current_user.id)

    return _public_ai_config(config)


def _public_ai_config(config: AIModelConfiguration) -> AIConfigModel:
    """Return settings and key presence without revealing the saved credential."""
    parameters = config.model_parameters or {}
    if config.provider not in {"ollama", "lm_studio", "openai", "openrouter"}:
        raise HTTPException(
            status_code=409,
            detail="Saved AI provider is unsupported. Choose Ollama, LM Studio, OpenAI or OpenRouter and save a supported configuration.",
        )
    return AIConfigModel(
        provider=config.provider,
        model=config.model,
        endpoint=config.endpoint,
        has_api_key=bool(config.api_key),
        compatibility_warnings=(
            [
                "Legacy preprocessing settings are inactive and will be removed on the next save."
            ]
            if parameters.get("enable_preprocessing")
            or parameters.get("preprocessing_model")
            else []
        ),
        **{
            key: parameters[key]
            for key in (
                "temperature",
                "max_tokens",
                "reasoning_effort",
            )
            if key in parameters
        },
    )


@router.post("/ai", response_model=AIConfigModel)
async def update_ai_config(
    data: AIConfigModel,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update User AI Config"""
    if data.reasoning_effort is not None and data.provider != "lm_studio":
        raise HTTPException(status_code=422, detail="Reasoning override is supported only for compatible LM Studio models")
    config = (
        db.query(AIModelConfiguration)
        .filter(AIModelConfiguration.user_id == current_user.id)
        .first()
    )
    if not config:
        config = AIModelConfiguration(user_id=current_user.id)
        db.add(config)

    destination_changed = config.provider != data.provider or (
        config.endpoint or ""
    ) != (data.endpoint or "")
    config.provider = data.provider
    config.model = data.model
    config.endpoint = data.endpoint
    if data.clear_api_key or (destination_changed and not data.api_key):
        config.api_key = None
    elif data.api_key:
        config.set_encrypted_api_key(data.api_key)
    config.model_parameters = {
        key: getattr(data, key)
        for key in (
            "temperature",
            "max_tokens",
        )
    }
    if data.reasoning_effort is not None:
        config.model_parameters = {**config.model_parameters, "reasoning_effort": data.reasoning_effort}
    db.commit()
    db.refresh(config)
    public = _public_ai_config(config)
    if data.enable_preprocessing or data.preprocessing_model:
        public.compatibility_warnings = [
            "Preprocessing is retired. These legacy settings were ignored; the selected model receives the bounded source directly."
        ]
    return public


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
    Supports: ollama, lm_studio, openai, openrouter
    """
    try:
        # Get user's AI configuration for defaults
        config = (
            db.query(AIModelConfiguration)
            .filter(AIModelConfiguration.user_id == current_user.id)
            .first()
        )

        if not config:
            config = default_ai_configuration(current_user.id)
        target_provider = provider or config.provider

        # Fetch models from the provider
        try:
            target_enum = AIProvider(target_provider)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Invalid provider: {target_provider}. "
                    "Valid options: ollama, lm_studio, openai, openrouter"
                ),
            )

        if target_provider not in {"ollama", "lm_studio", "openai", "openrouter"}:
            raise HTTPException(
                status_code=422,
                detail="Unsupported provider; choose a supported provider in settings",
            )
        if target_provider != config.provider:
            raise HTTPException(
                status_code=409,
                detail="Save the requested provider and its endpoint in AI settings before fetching models",
            )
        ai_service = get_ai_service_dependency(current_user, db)
        try:
            models = ai_service.fetch_available_models(provider=target_enum)
        finally:
            ai_service.close()

        return ModelsResponse(models=models, provider=target_provider)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch models: {str(e)}")


def _build_ai_service(
    config_override: Optional[AIConfigModel], current_user: User, db: Session
) -> AIService:
    if config_override:
        saved = (
            db.query(AIModelConfiguration).filter_by(user_id=current_user.id).first()
        )
        key = config_override.api_key
        same_destination = (
            saved is not None
            and saved.provider == config_override.provider
            and (saved.endpoint or "") == (config_override.endpoint or "")
        )
        if not key and same_destination and not config_override.clear_api_key:
            key = saved.decrypted_api_key
        return AIService(
            RuntimeAIConfig(
                provider=config_override.provider,
                model=config_override.model,
                endpoint=config_override.endpoint,
                api_key=key,
                temperature=config_override.temperature,
                max_tokens=config_override.max_tokens,
                reasoning_effort=config_override.reasoning_effort,
            ),
            logger,
        )
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
            max_tokens=256,
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
