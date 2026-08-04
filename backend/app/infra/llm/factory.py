"""Resolve provider string -> concrete LLM client."""

from __future__ import annotations

from app.config import settings
from app.core.domain.schemas import LLMProvider

from .base import BaseLLMClient


def _get_provider_class(provider: str) -> type:
    if provider == LLMProvider.OPENAI:
        from .openai_client import OpenAIClient
        return OpenAIClient
    if provider == LLMProvider.ANTHROPIC:
        from .anthropic_client import AnthropicClient
        return AnthropicClient
    if provider == LLMProvider.MISTRAL:
        from .mistral_client import MistralClient
        return MistralClient
    if provider == LLMProvider.DEEPSEEK:
        from .deepseek_client import DeepSeekClient
        return DeepSeekClient
    if provider == LLMProvider.GEMINI:
        from .gemini_client import GeminiClient
        return GeminiClient
    if provider == LLMProvider.GROK:
        from .grok_client import GrokClient
        return GrokClient
    if provider == LLMProvider.MOONSHOTAI:
        from .moonshotai_client import MoonshotAIClient
        return MoonshotAIClient

    raise ValueError(
        f"Unknown provider '{provider}'. Supported: "
        f"{', '.join(v.value for v in LLMProvider)}"
    )


def get_llm_client(
    *,
    provider: str,
    model_name: str,
    api_key_override: str | None = None,
) -> BaseLLMClient:
    provider_lower = provider.lower()
    cls = _get_provider_class(provider_lower)

    api_key = api_key_override or settings.get_api_key(provider_lower) or ""

    if not api_key:
        raise ValueError(
            f"No API key for '{provider}'. "
            f"Set {provider_lower.upper()}_API_KEY in .env"
        )

    return cls(api_key=api_key, model_name=model_name)  # type: ignore[call-arg]


