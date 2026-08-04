"""Central model registry — reads LLM_<PROVIDER> env vars from settings.

Each env var follows the format:
    LLM_<PROVIDER>=model_name
    LLM_<PROVIDER>=model_name|Label
    LLM_<PROVIDER>=model_name|Label|context_window

API key is auto-derived as <PROVIDER>_API_KEY.

Example:
    LLM_OPENAI=gpt-4o|OpenAI
    → provider="openai", model_name="gpt-4o", label="OpenAI",
      api_key_env="OPENAI_API_KEY", id="openai/gpt-4o"
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from app.infra.llm.preflight_constants import API_KEY_ENV_NAMES

logger = logging.getLogger(__name__)

# Prefix used to discover model env vars in settings
_LLM_PREFIX = "llm_"


@dataclass(frozen=True)
class RegisteredModel:
    """One model entry parsed from an LLM_<PROVIDER> env var."""

    provider: str
    model_name: str
    label: str
    api_key_env: str
    id: str  # "provider/model_name"


def parse_llm_env_var(provider: str, value: str) -> RegisteredModel | None:
    """Parse a single LLM_<PROVIDER> value.

    Accepted formats:
        'model_name'
        'model_name|Label'
        'model_name|Label|context_window'

    Returns None if the value is empty/invalid.
    """
    if not value or not value.strip():
        return None

    parts = value.strip().split("|")
    model_name = parts[0].strip()

    if not model_name:
        logger.warning("LLM_%s has empty model_name, skipping", provider.upper())
        return None

    label = parts[1].strip() if len(parts) > 1 and parts[1].strip() else f"{provider.capitalize()} ({model_name})"

    provider_lower = provider.lower()
    return RegisteredModel(
        provider=provider_lower,
        model_name=model_name,
        label=label,
        api_key_env=API_KEY_ENV_NAMES.get(provider_lower, f"{provider.upper()}_API_KEY"),
        id=f"{provider_lower}/{model_name}",
    )


def build_registry_from_settings(settings: object) -> list[RegisteredModel]:
    """Scan settings for any field starting with 'llm_' and parse models.

    The settings object is expected to have attributes like
    llm_openai, llm_anthropic, etc. (pydantic-settings reads LLM_OPENAI env var).
    """
    models: list[RegisteredModel] = []

    for attr_name in sorted(dir(settings)):
        if not attr_name.startswith(_LLM_PREFIX):
            continue
        # Skip internal/private attrs
        if attr_name.startswith("__"):
            continue

        provider = attr_name[len(_LLM_PREFIX):]
        if not provider:
            continue

        value = getattr(settings, attr_name, None)
        if not value or not isinstance(value, str):
            continue

        model = parse_llm_env_var(provider, value)
        if model:
            models.append(model)
            logger.debug("Registered model: %s", model.id)

    if not models:
        logger.warning("No LLM_* models found in settings")

    return models


# ---------------------------------------------------------------------------
# Convenience helpers
# ---------------------------------------------------------------------------

def get_scheduler_models(
    models: list[RegisteredModel],
) -> list[dict[str, str]]:
    """Return models in the format used by scheduled_eval.py."""
    return [
        {
            "provider": m.provider,
            "model_name": m.model_name,
            "api_key_env": m.api_key_env,
        }
        for m in models
    ]


def get_model_by_key(
    models: list[RegisteredModel],
    key: str,
) -> RegisteredModel | None:
    """Lookup a model by its id (provider/model_name)."""
    for m in models:
        if m.id == key:
            return m
    return None
