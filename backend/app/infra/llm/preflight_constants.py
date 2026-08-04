"""Constants for LLM preflight validation."""

from typing import Final

# Cheapest/lightest model per provider for preflight checks
PREFLIGHT_MODELS: Final[dict[str, str]] = {
    "openai": "gpt-3.5-turbo",
    "anthropic": "claude-3-haiku-20240307",
    "gemini": "gemini-2.0-flash",
    "mistral": "mistral-small-latest",
    "deepseek": "deepseek-chat",
    "grok": "grok-3",
    "moonshotai": "moonshotai/Kimi-K2.5",
}

PROVIDER_BASE_URLS: Final[dict[str, str]] = {
    "openai": "https://api.openai.com/v1",
    "deepseek": "https://api.deepseek.com",
    "grok": "https://api.x.ai/v1",
    "moonshotai": "https://api.together.xyz/v1",
}

API_KEY_ENV_NAMES: Final[dict[str, str]] = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "mistral": "MISTRAL_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
    "grok": "GROK_API_KEY",
    "moonshotai": "MOONSHOTAI_API_KEY",
}

PREFLIGHT_TEST_CONTENT: Final[str] = "test"
ERR_PREFLIGHT_TIMEOUT: Final[str] = "Preflight request timed out"
PREFLIGHT_MAX_TOKENS: Final[int] = 1
