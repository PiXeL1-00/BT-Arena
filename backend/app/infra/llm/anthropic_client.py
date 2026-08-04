from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any, Optional

import anthropic

from .base import LLMResponse
from .costs import ANTHROPIC_CLAUDE_35_SONNET_PRICING
from .key_validation import is_quota_exhaustion
from app.core.domain.exceptions import LLMClientError, QuotaExhaustedError

logger = logging.getLogger(__name__)


class AnthropicClient:
    PRICING = ANTHROPIC_CLAUDE_35_SONNET_PRICING

    def __init__(self, *, api_key: str, model_name: str) -> None:
        self.model_name = model_name
        self._client = anthropic.AsyncAnthropic(api_key=api_key)

    async def complete(
        self,
        prompt: str,
        *,
        json_schema: Optional[dict[str, Any]] = None,
        temperature: float = 0.0,
        timeout: int = 60,
        retries: int = 3,
    ) -> LLMResponse:
        system_msg = "You are a helpful assistant."
        if json_schema:
            system_msg += "\nRespond ONLY with valid JSON matching the schema. No extra text."

        last_err: Exception | None = None
        for attempt in range(1, retries + 1):
            try:
                t0 = time.perf_counter()
                resp = await asyncio.wait_for(
                    self._client.messages.create(
                        model=self.model_name,
                        max_tokens=2048,
                        temperature=temperature,
                        system=system_msg,
                        messages=[{"role": "user", "content": prompt}],
                    ),
                    timeout=timeout,
                )
                latency = int((time.perf_counter() - t0) * 1000)
                content = resp.content[0].text

                cost = self._estimate_cost(resp.usage.input_tokens, resp.usage.output_tokens)

                if json_schema:
                    json.loads(content)

                return LLMResponse(text=content, latency_ms=latency, cost_estimate=cost)
            except asyncio.CancelledError:
                # Never swallow cancellation — let it propagate immediately.
                raise
            except Exception as exc:
                if is_quota_exhaustion(exc):
                    raise QuotaExhaustedError("anthropic", str(exc)) from exc
                last_err = exc
                wait = min(2 ** attempt, 8)
                logger.warning("Anthropic attempt %d/%d failed: %s", attempt, retries, exc)
                if attempt < retries:
                    await asyncio.sleep(wait)

        raise LLMClientError("anthropic", f"call failed after {retries} retries: {last_err}") from last_err

    def _estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        inp = (input_tokens / 1_000_000) * self.PRICING[0]
        out = (output_tokens / 1_000_000) * self.PRICING[1]
        return round(inp + out, 6)
