"""Provider-specific preflight validation functions for API keys."""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

try:
    import anthropic  # pyright: ignore[reportMissingImports]
except ImportError:  # pragma: no cover - optional dependency
    anthropic = None

AnthropicAPIError = getattr(anthropic, "APIError", Exception)

try:
    from google import genai  # pyright: ignore[reportMissingImports]
except ImportError:  # pragma: no cover - optional dependency
    genai = None

try:
    from mistralai import Mistral  # pyright: ignore[reportMissingImports]
except ImportError:  # pragma: no cover - optional dependency
    Mistral = None

try:
    from openai import APIError, AsyncOpenAI, RateLimitError  # pyright: ignore[reportMissingImports]
except ImportError:  # pragma: no cover - optional dependency
    APIError = RateLimitError = Exception
    AsyncOpenAI = None

from .key_validation import (
    KeyValidationResult,
    KeyValidationStatus,
    classify_error,
)
from .preflight_constants import (
    API_KEY_ENV_NAMES,
    ERR_PREFLIGHT_TIMEOUT,
    PREFLIGHT_MAX_TOKENS,
    PREFLIGHT_MODELS,
    PREFLIGHT_TEST_CONTENT,
    PROVIDER_BASE_URLS,
)

logger = logging.getLogger(__name__)

# Timeout for individual preflight calls (8 seconds)
PREFLIGHT_TIMEOUT = 8


def _missing_sdk_result(provider: str, api_key_env: str, package_name: str) -> KeyValidationResult:
    return KeyValidationResult(
        status=KeyValidationStatus.UNKNOWN_ERROR,
        provider=provider,
        api_key_env=api_key_env,
        error_message=f"{package_name} is not installed in this environment",
    )


async def preflight_openai(api_key: str) -> KeyValidationResult:
    """Preflight validation for OpenAI API key.

    Uses models.list() which is lightweight and free.
    Falls back to minimal chat completion if models.list() is unavailable.
    """
    provider = "openai"
    api_key_env = API_KEY_ENV_NAMES[provider]

    if AsyncOpenAI is None:
        return _missing_sdk_result(provider, api_key_env, "openai")

    try:
        client = AsyncOpenAI(api_key=api_key, base_url=PROVIDER_BASE_URLS[provider])

        try:
            await asyncio.wait_for(
                client.models.list(),
                timeout=PREFLIGHT_TIMEOUT,
            )
            return KeyValidationResult(
                status=KeyValidationStatus.VALID,
                provider=provider,
                api_key_env=api_key_env,
                http_status=200,
            )
        except AttributeError:
            logger.debug("OpenAI models.list() not available, using chat completion fallback")
            await asyncio.wait_for(
                client.chat.completions.create(
                    model=PREFLIGHT_MODELS[provider],
                    messages=[{"role": "user", "content": PREFLIGHT_TEST_CONTENT}],
                    max_tokens=PREFLIGHT_MAX_TOKENS,
                ),
                timeout=PREFLIGHT_TIMEOUT,
            )
            return KeyValidationResult(
                status=KeyValidationStatus.VALID,
                provider=provider,
                api_key_env=api_key_env,
                http_status=200,
            )
    except asyncio.TimeoutError:
        return KeyValidationResult(
            status=KeyValidationStatus.TIMEOUT,
            provider=provider,
            api_key_env=api_key_env,
            error_message=ERR_PREFLIGHT_TIMEOUT,
        )
    except APIError as exc:
        status = getattr(exc, "status_code", None)
        message = getattr(exc, "message", str(exc))
        request_id = getattr(exc, "request_id", None)
        return KeyValidationResult(
            status=classify_error(status, message),
            provider=provider,
            api_key_env=api_key_env,
            error_message=message,
            request_id=request_id,
            http_status=status,
        )
    except RateLimitError as exc:
        status = getattr(exc, "status_code", 429)
        message = getattr(exc, "message", str(exc))
        request_id = getattr(exc, "request_id", None)
        return KeyValidationResult(
            status=classify_error(status, message),
            provider=provider,
            api_key_env=api_key_env,
            error_message=message,
            request_id=request_id,
            http_status=status,
        )
    except Exception as exc:
        logger.warning("Unexpected error in OpenAI preflight: %s", exc, exc_info=True)
        return KeyValidationResult(
            status=classify_error(None, str(exc)),
            provider=provider,
            api_key_env=api_key_env,
            error_message=str(exc),
        )


async def preflight_anthropic(api_key: str) -> KeyValidationResult:
    """Preflight validation for Anthropic API key.

    Uses minimal messages.create() call (costs ~$0.00001).
    Anthropic doesn't have a free models.list endpoint.
    """
    provider = "anthropic"
    api_key_env = API_KEY_ENV_NAMES[provider]

    if anthropic is None:
        return _missing_sdk_result(provider, api_key_env, "anthropic")

    try:
        client = anthropic.AsyncAnthropic(api_key=api_key)

        await asyncio.wait_for(
            client.messages.create(
                model=PREFLIGHT_MODELS[provider],
                max_tokens=PREFLIGHT_MAX_TOKENS,
                messages=[{"role": "user", "content": PREFLIGHT_TEST_CONTENT}],
            ),
            timeout=PREFLIGHT_TIMEOUT,
        )
        return KeyValidationResult(
            status=KeyValidationStatus.VALID,
            provider=provider,
            api_key_env=api_key_env,
            http_status=200,
        )
    except asyncio.TimeoutError:
        return KeyValidationResult(
            status=KeyValidationStatus.TIMEOUT,
            provider=provider,
            api_key_env=api_key_env,
            error_message=ERR_PREFLIGHT_TIMEOUT,
        )
    except AnthropicAPIError as exc:
        status = getattr(exc, "status_code", None)
        message = getattr(exc, "message", str(exc))
        error_type = getattr(exc, "type", None)
        request_id = None
        if hasattr(exc, "response") and exc.response:
            request_id = exc.response.headers.get("anthropic-request-id")
        return KeyValidationResult(
            status=classify_error(status, message, error_type),
            provider=provider,
            api_key_env=api_key_env,
            error_message=message,
            request_id=request_id,
            http_status=status,
        )
    except Exception as exc:
        logger.warning("Unexpected error in Anthropic preflight: %s", exc, exc_info=True)
        return KeyValidationResult(
            status=classify_error(None, str(exc)),
            provider=provider,
            api_key_env=api_key_env,
            error_message=str(exc),
        )


async def preflight_gemini(api_key: str) -> KeyValidationResult:
    """Preflight validation for Gemini API key.

    Tries models.list() if available, falls back to minimal generate_content.
    """
    provider = "gemini"
    api_key_env = API_KEY_ENV_NAMES[provider]

    if genai is None:
        return _missing_sdk_result(provider, api_key_env, "google-genai")

    try:
        client = genai.Client(api_key=api_key)

        try:
            models = await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: client.models.list(),
                ),
                timeout=PREFLIGHT_TIMEOUT,
            )
            return KeyValidationResult(
                status=KeyValidationStatus.VALID,
                provider=provider,
                api_key_env=api_key_env,
                http_status=200,
            )
        except AttributeError:
            logger.debug("Gemini models.list() not available, using generate_content fallback")
            await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: client.models.generate_content(
                        model=PREFLIGHT_MODELS[provider],
                        contents=PREFLIGHT_TEST_CONTENT,
                        config={"max_output_tokens": PREFLIGHT_MAX_TOKENS},
                    ),
                ),
                timeout=PREFLIGHT_TIMEOUT,
            )
            return KeyValidationResult(
                status=KeyValidationStatus.VALID,
                provider=provider,
                api_key_env=api_key_env,
                http_status=200,
            )
    except asyncio.TimeoutError:
        return KeyValidationResult(
            status=KeyValidationStatus.TIMEOUT,
            provider=provider,
            api_key_env=api_key_env,
            error_message=ERR_PREFLIGHT_TIMEOUT,
        )
    except Exception as exc:
        status = getattr(exc, "status_code", None) or getattr(exc, "code", None)
        message = str(exc)
        logger.warning("Error in Gemini preflight: %s", exc, exc_info=True)
        return KeyValidationResult(
            status=classify_error(status, message),
            provider=provider,
            api_key_env=api_key_env,
            error_message=message,
            http_status=status,
        )


async def preflight_mistral(api_key: str) -> KeyValidationResult:
    """Preflight validation for Mistral API key.

    Tries models.list() if available, falls back to minimal chat completion.
    """
    provider = "mistral"
    api_key_env = API_KEY_ENV_NAMES[provider]

    if Mistral is None:
        return _missing_sdk_result(provider, api_key_env, "mistralai")

    try:
        client = Mistral(api_key=api_key)

        if hasattr(client, "models") and hasattr(client.models, "list"):
            await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: client.models.list(),
                ),
                timeout=PREFLIGHT_TIMEOUT,
            )
            return KeyValidationResult(
                status=KeyValidationStatus.VALID,
                provider=provider,
                api_key_env=api_key_env,
                http_status=200,
            )
        else:
            await asyncio.wait_for(
                client.chat.complete_async(
                    model=PREFLIGHT_MODELS[provider],
                    messages=[{"role": "user", "content": PREFLIGHT_TEST_CONTENT}],
                    max_tokens=PREFLIGHT_MAX_TOKENS,
                ),
                timeout=PREFLIGHT_TIMEOUT,
            )
            return KeyValidationResult(
                status=KeyValidationStatus.VALID,
                provider=provider,
                api_key_env=api_key_env,
                http_status=200,
            )
    except asyncio.TimeoutError:
        return KeyValidationResult(
            status=KeyValidationStatus.TIMEOUT,
            provider=provider,
            api_key_env=api_key_env,
            error_message=ERR_PREFLIGHT_TIMEOUT,
        )
    except Exception as exc:
        status = getattr(exc, "status_code", None)
        message = getattr(exc, "message", str(exc))
        logger.warning("Error in Mistral preflight: %s", exc, exc_info=True)
        return KeyValidationResult(
            status=classify_error(status, message),
            provider=provider,
            api_key_env=api_key_env,
            error_message=message,
            http_status=status,
        )


async def preflight_deepseek(api_key: str) -> KeyValidationResult:
    """Preflight validation for DeepSeek API key.

    Uses OpenAI-compatible API, same as OpenAI preflight.
    """
    provider = "deepseek"
    api_key_env = API_KEY_ENV_NAMES[provider]

    if AsyncOpenAI is None:
        return _missing_sdk_result(provider, api_key_env, "openai")

    try:
        client = AsyncOpenAI(api_key=api_key, base_url=PROVIDER_BASE_URLS[provider])

        try:
            await asyncio.wait_for(
                client.models.list(),
                timeout=PREFLIGHT_TIMEOUT,
            )
            return KeyValidationResult(
                status=KeyValidationStatus.VALID,
                provider=provider,
                api_key_env=api_key_env,
                http_status=200,
            )
        except AttributeError:
            logger.debug("DeepSeek models.list() not available, using chat completion fallback")
            await asyncio.wait_for(
                client.chat.completions.create(
                    model=PREFLIGHT_MODELS[provider],
                    messages=[{"role": "user", "content": PREFLIGHT_TEST_CONTENT}],
                    max_tokens=PREFLIGHT_MAX_TOKENS,
                ),
                timeout=PREFLIGHT_TIMEOUT,
            )
            return KeyValidationResult(
                status=KeyValidationStatus.VALID,
                provider=provider,
                api_key_env=api_key_env,
                http_status=200,
            )
    except asyncio.TimeoutError:
        return KeyValidationResult(
            status=KeyValidationStatus.TIMEOUT,
            provider=provider,
            api_key_env=api_key_env,
            error_message=ERR_PREFLIGHT_TIMEOUT,
        )
    except APIError as exc:
        status = getattr(exc, "status_code", None)
        message = getattr(exc, "message", str(exc))
        request_id = getattr(exc, "request_id", None)
        return KeyValidationResult(
            status=classify_error(status, message),
            provider=provider,
            api_key_env=api_key_env,
            error_message=message,
            request_id=request_id,
            http_status=status,
        )
    except RateLimitError as exc:
        status = getattr(exc, "status_code", 429)
        message = getattr(exc, "message", str(exc))
        request_id = getattr(exc, "request_id", None)
        return KeyValidationResult(
            status=classify_error(status, message),
            provider=provider,
            api_key_env=api_key_env,
            error_message=message,
            request_id=request_id,
            http_status=status,
        )
    except Exception as exc:
        logger.warning("Unexpected error in DeepSeek preflight: %s", exc, exc_info=True)
        return KeyValidationResult(
            status=classify_error(None, str(exc)),
            provider=provider,
            api_key_env=api_key_env,
            error_message=str(exc),
        )


async def preflight_grok(api_key: str) -> KeyValidationResult:
    """Preflight validation for Grok API key.

    Uses OpenAI-compatible API, same as OpenAI preflight.
    """
    provider = "grok"
    api_key_env = API_KEY_ENV_NAMES[provider]

    if AsyncOpenAI is None:
        return _missing_sdk_result(provider, api_key_env, "openai")

    try:
        client = AsyncOpenAI(api_key=api_key, base_url=PROVIDER_BASE_URLS[provider])

        try:
            await asyncio.wait_for(
                client.models.list(),
                timeout=PREFLIGHT_TIMEOUT,
            )
            return KeyValidationResult(
                status=KeyValidationStatus.VALID,
                provider=provider,
                api_key_env=api_key_env,
                http_status=200,
            )
        except AttributeError:
            logger.debug("Grok models.list() not available, using chat completion fallback")
            await asyncio.wait_for(
                client.chat.completions.create(
                    model=PREFLIGHT_MODELS[provider],
                    messages=[{"role": "user", "content": PREFLIGHT_TEST_CONTENT}],
                    max_tokens=PREFLIGHT_MAX_TOKENS,
                ),
                timeout=PREFLIGHT_TIMEOUT,
            )
            return KeyValidationResult(
                status=KeyValidationStatus.VALID,
                provider=provider,
                api_key_env=api_key_env,
                http_status=200,
            )
    except asyncio.TimeoutError:
        return KeyValidationResult(
            status=KeyValidationStatus.TIMEOUT,
            provider=provider,
            api_key_env=api_key_env,
            error_message=ERR_PREFLIGHT_TIMEOUT,
        )
    except APIError as exc:
        status = getattr(exc, "status_code", None)
        message = getattr(exc, "message", str(exc))
        request_id = getattr(exc, "request_id", None)
        return KeyValidationResult(
            status=classify_error(status, message),
            provider=provider,
            api_key_env=api_key_env,
            error_message=message,
            request_id=request_id,
            http_status=status,
        )
    except RateLimitError as exc:
        status = getattr(exc, "status_code", 429)
        message = getattr(exc, "message", str(exc))
        request_id = getattr(exc, "request_id", None)
        return KeyValidationResult(
            status=classify_error(status, message),
            provider=provider,
            api_key_env=api_key_env,
            error_message=message,
            request_id=request_id,
            http_status=status,
        )
    except Exception as exc:
        logger.warning("Unexpected error in Grok preflight: %s", exc, exc_info=True)
        return KeyValidationResult(
            status=classify_error(None, str(exc)),
            provider=provider,
            api_key_env=api_key_env,
            error_message=str(exc),
        )


async def preflight_moonshotai(api_key: str) -> KeyValidationResult:
    """Preflight validation for MoonshotAI (Together AI) API key.

    Uses OpenAI-compatible API via Together AI's endpoint.
    """
    provider = "moonshotai"
    api_key_env = API_KEY_ENV_NAMES[provider]

    try:
        client = AsyncOpenAI(api_key=api_key, base_url=PROVIDER_BASE_URLS[provider])

        # Together AI's /v1/models is incompatible with the OpenAI SDK
        # (returns a plain list, not a paged response), so validate
        # directly with a minimal chat completion call.
        await asyncio.wait_for(
            client.chat.completions.create(
                model=PREFLIGHT_MODELS[provider],
                messages=[{"role": "user", "content": PREFLIGHT_TEST_CONTENT}],
                max_tokens=PREFLIGHT_MAX_TOKENS,
            ),
            timeout=PREFLIGHT_TIMEOUT,
        )
        return KeyValidationResult(
            status=KeyValidationStatus.VALID,
            provider=provider,
            api_key_env=api_key_env,
            http_status=200,
        )
    except asyncio.TimeoutError:
        return KeyValidationResult(
            status=KeyValidationStatus.TIMEOUT,
            provider=provider,
            api_key_env=api_key_env,
            error_message=ERR_PREFLIGHT_TIMEOUT,
        )
    except APIError as exc:
        status = getattr(exc, "status_code", None)
        message = getattr(exc, "message", str(exc))
        request_id = getattr(exc, "request_id", None)
        return KeyValidationResult(
            status=classify_error(status, message),
            provider=provider,
            api_key_env=api_key_env,
            error_message=message,
            request_id=request_id,
            http_status=status,
        )
    except RateLimitError as exc:
        status = getattr(exc, "status_code", 429)
        message = getattr(exc, "message", str(exc))
        request_id = getattr(exc, "request_id", None)
        return KeyValidationResult(
            status=classify_error(status, message),
            provider=provider,
            api_key_env=api_key_env,
            error_message=message,
            request_id=request_id,
            http_status=status,
        )
    except Exception as exc:
        logger.warning("Unexpected error in MoonshotAI preflight: %s", exc, exc_info=True)
        return KeyValidationResult(
            status=classify_error(None, str(exc)),
            provider=provider,
            api_key_env=api_key_env,
            error_message=str(exc),
        )


async def preflight_nvidia(api_key: str) -> KeyValidationResult:
    """Preflight validation for NVIDIA NIM API key (build.nvidia.com).

    Uses OpenAI-compatible chat completions with a minimal 1-token request
    against z-ai/glm-5.2 to verify the key without significant cost.
    """
    provider = "nvidia"
    api_key_env = API_KEY_ENV_NAMES[provider]

    if AsyncOpenAI is None:
        return _missing_sdk_result(provider, api_key_env, "openai")

    try:
        client = AsyncOpenAI(api_key=api_key, base_url=PROVIDER_BASE_URLS[provider])

        await asyncio.wait_for(
            client.chat.completions.create(
                model=PREFLIGHT_MODELS[provider],
                messages=[{"role": "user", "content": PREFLIGHT_TEST_CONTENT}],
                max_tokens=PREFLIGHT_MAX_TOKENS,
            ),
            timeout=PREFLIGHT_TIMEOUT,
        )
        return KeyValidationResult(
            status=KeyValidationStatus.VALID,
            provider=provider,
            api_key_env=api_key_env,
            http_status=200,
        )
    except asyncio.TimeoutError:
        return KeyValidationResult(
            status=KeyValidationStatus.TIMEOUT,
            provider=provider,
            api_key_env=api_key_env,
            error_message=ERR_PREFLIGHT_TIMEOUT,
        )
    except APIError as exc:
        status = getattr(exc, "status_code", None)
        message = getattr(exc, "message", str(exc))
        request_id = getattr(exc, "request_id", None)
        return KeyValidationResult(
            status=classify_error(status, message),
            provider=provider,
            api_key_env=api_key_env,
            error_message=message,
            request_id=request_id,
            http_status=status,
        )
    except RateLimitError as exc:
        status = getattr(exc, "status_code", 429)
        message = getattr(exc, "message", str(exc))
        request_id = getattr(exc, "request_id", None)
        return KeyValidationResult(
            status=classify_error(status, message),
            provider=provider,
            api_key_env=api_key_env,
            error_message=message,
            request_id=request_id,
            http_status=status,
        )
    except Exception as exc:
        logger.warning("Unexpected error in NVIDIA preflight: %s", exc, exc_info=True)
        return KeyValidationResult(
            status=classify_error(None, str(exc)),
            provider=provider,
            api_key_env=api_key_env,
            error_message=str(exc),
        )

