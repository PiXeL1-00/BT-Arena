from __future__ import annotations

import logging
import time

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.api.security import verify_admin_key
from app.config import settings
from app.infra.llm.key_validator import validate_all_keys
from app.infra.llm.key_validation import KeyValidationResult, KeyValidationStatus
from app.infra.db.repository import Repository
from app.infra.timezone_utils import get_today_in_tz

router = APIRouter(prefix="/models", tags=["models"])

# Simple rate limiting: track last request time per IP
# Format: {ip: last_request_timestamp}
_rate_limit_cache: dict[str, float] = {}
RATE_LIMIT_SECONDS = 5  # Reduced from 10 to 5 seconds for better UX


def _check_rate_limit(request: Request) -> None:
    """Check if request is within rate limit.

    Raises:
        HTTPException: If rate limit exceeded
    """
    client_ip = request.client.host if request.client else "unknown"
    now = time.time()

    if client_ip in _rate_limit_cache:
        last_request = _rate_limit_cache[client_ip]
        elapsed = now - last_request
        if elapsed < RATE_LIMIT_SECONDS:
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded. Please wait {RATE_LIMIT_SECONDS - int(elapsed)} seconds.",
            )

    _rate_limit_cache[client_ip] = now


def _serialize_validation_result(result: KeyValidationResult) -> dict:
    """Serialize KeyValidationResult to dict for JSON response."""
    return {
        "status": result.status.value,
        "provider": result.provider,
        "api_key_env": result.api_key_env,
        "error_message": result.error_message,
        "request_id": result.request_id,
        "http_status": result.http_status,
        "validated_at": result.validated_at.isoformat() if result.validated_at else None,
    }


@router.get("/debate-config")
async def get_debate_config(
    session: AsyncSession = Depends(get_session),
):
    """Return env-mode config + daily usage so frontend can enable/disable models."""
    is_debug = settings.debug

    if is_debug:
        return {
            "debug_mode": True,
            "allowed_models": [],
            "daily_cap": 0,
            "usage_today": {},
        }

    repo = Repository(session)
    today = get_today_in_tz()
    usage = await repo.get_all_debate_usage_today(today=today)

    return {
        "debug_mode": False,
        "allowed_models": settings.debate_enabled_production_model_keys,
        "daily_cap": settings.debate_daily_production_cap,
        "usage_today": usage,
    }


@router.get("/registry")
async def get_model_registry():
    """Return the full list of registered models from LLM_* env vars."""
    models = settings.registered_models
    return {
        "models": [
            {
                "id": m.id,
                "provider": m.provider,
                "model_name": m.model_name,
                "label": m.label,
                "api_key_env": m.api_key_env,
            }
            for m in models
        ],
    }


@router.get("/available-keys")
async def get_available_keys(
    request: Request,
    validate: bool = False,
    force: bool = False,
    _: None = Depends(verify_admin_key),
):
    """Return a set of API key environment variable names that are configured.

    Args:
        validate: If True, also validate keys and return validation results
        force: If True, bypass cache and force re-validation (only used if validate=True)
        request: FastAPI request object (injected automatically, used for rate limiting)

    Returns:
        Dict with available_keys list, and optionally validation dict
    """
    available = set()

    _PROVIDER_NAMES = ("openai", "anthropic", "mistral", "deepseek", "gemini", "grok")
    _MIN_KEY_LENGTH = 10
    _INVALID_VALUES = frozenset(("no", "false", "none", "", "n/a", "na", "not set", "unset"))

    for provider in _PROVIDER_NAMES:
        env_name = f"{provider.upper()}_API_KEY"
        key_value = settings.get_api_key(provider)
        if not key_value or not isinstance(key_value, str):
            continue
        stripped = key_value.strip().lower()
        if stripped not in _INVALID_VALUES and len(stripped) > _MIN_KEY_LENGTH:
            available.add(env_name)

    response = {"available_keys": list(available)}

    # If validation requested, add validation results
    if validate:
        # Check rate limit for validation requests
        _check_rate_limit(request)

        try:
            validation_results = await validate_all_keys(force=force)
            # Serialize validation results
            response["validation"] = {
                api_key_env: _serialize_validation_result(result)
                for api_key_env, result in validation_results.items()
            }
        except HTTPException:
            # Re-raise rate limit exceptions
            raise
        except Exception as exc:
            logger = logging.getLogger(__name__)
            logger.error("Error during key validation: %s", exc, exc_info=True)
            response["validation"] = {}
            response["validation_error"] = "Failed to validate keys. Please try again."

    return response
