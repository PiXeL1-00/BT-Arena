"""Base for OpenAI-compatible APIs (OpenAI, DeepSeek, Grok)."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any, Optional

from openai import AsyncOpenAI, APIError, RateLimitError

from .base import LLMResponse
from .costs import DEFAULT_PRICING
from .key_validation import is_quota_exhaustion
from .preflight_constants import PROVIDER_BASE_URLS
from app.core.domain.exceptions import LLMClientError, QuotaExhaustedError

logger = logging.getLogger(__name__)


class OpenAICompatibleClient:

    BASE_URL: str = PROVIDER_BASE_URLS["openai"]
    PRICING: tuple[float, float] = DEFAULT_PRICING

    def __init__(self, *, api_key: str, model_name: str) -> None:
        self.model_name = model_name
        self._client = AsyncOpenAI(api_key=api_key, base_url=self.BASE_URL)

    async def complete(
        self,
        prompt: str,
        *,
        json_schema: Optional[dict[str, Any]] = None,
        temperature: float = 0.0,
        timeout: int = 60,
        retries: int = 3,
    ) -> LLMResponse:
        last_err: Exception | None = None
        for attempt in range(1, retries + 1):
            try:
                return await self._call(
                    prompt, json_schema=json_schema,
                    temperature=temperature, timeout=timeout,
                )
            except (APIError, RateLimitError, asyncio.TimeoutError) as exc:
                if isinstance(exc, RateLimitError) and is_quota_exhaustion(exc):
                    provider = self.BASE_URL.split("//")[1].split(".")[0] if "//" in self.BASE_URL else "openai"
                    raise QuotaExhaustedError(provider, str(exc)) from exc
                last_err = exc
                wait = min(2 ** attempt, 8)
                logger.warning(
                    "LLM attempt %d/%d failed (%s), retrying in %ds",
                    attempt, retries, exc, wait,
                )
                await asyncio.sleep(wait)
        raise LLMClientError("openai", f"call failed after {retries} retries: {last_err}") from last_err

    async def _call(
        self, prompt: str, *,
        json_schema: Optional[dict[str, Any]],
        temperature: float, timeout: int,
    ) -> LLMResponse:
        kwargs: dict[str, Any] = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "timeout": timeout,
        }
        if json_schema:
            kwargs["response_format"] = {"type": "json_object"}

        t0 = time.perf_counter()
        resp = await self._client.chat.completions.create(**kwargs)
        latency = int((time.perf_counter() - t0) * 1000)

        content = resp.choices[0].message.content or ""
        cost = self._estimate_cost(resp.usage)

        if json_schema:
            json.loads(content)

        return LLMResponse(text=content, latency_ms=latency, cost_estimate=cost)

    def _estimate_cost(self, usage) -> float:
        if usage is None:
            return 0.0
        inp = (usage.prompt_tokens / 1_000_000) * self.PRICING[0]
        out = (usage.completion_tokens / 1_000_000) * self.PRICING[1]
        return round(inp + out, 6)
