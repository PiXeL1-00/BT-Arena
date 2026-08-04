from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any, Optional

from mistralai import Mistral

from .base import LLMResponse
from .costs import MISTRAL_LARGE_PRICING
from .key_validation import is_quota_exhaustion
from app.core.domain.exceptions import LLMClientError, QuotaExhaustedError

logger = logging.getLogger(__name__)


class MistralClient:
    PRICING = MISTRAL_LARGE_PRICING

    def __init__(self, *, api_key: str, model_name: str) -> None:
        self.model_name = model_name
        self._client = Mistral(api_key=api_key)

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
                t0 = time.perf_counter()
                resp = await asyncio.wait_for(
                    self._client.chat.complete_async(
                        model=self.model_name,
                        messages=[{"role": "user", "content": prompt}],
                        temperature=temperature,
                        response_format={"type": "json_object"} if json_schema else None,
                    ),
                    timeout=timeout,
                )
                latency = int((time.perf_counter() - t0) * 1000)
                content = resp.choices[0].message.content

                cost = 0.0
                if resp.usage:
                    cost = self._estimate_cost(resp.usage.prompt_tokens, resp.usage.completion_tokens)

                if json_schema:
                    json.loads(content)

                return LLMResponse(text=content, latency_ms=latency, cost_estimate=cost)
            except asyncio.CancelledError:
                # Never swallow cancellation — let it propagate immediately.
                raise
            except Exception as exc:
                if is_quota_exhaustion(exc):
                    raise QuotaExhaustedError("mistral", str(exc)) from exc
                last_err = exc
                wait = min(2 ** attempt, 8)
                logger.warning("Mistral attempt %d/%d failed: %s", attempt, retries, exc)
                if attempt < retries:
                    await asyncio.sleep(wait)

        raise LLMClientError("mistral", f"call failed after {retries} retries: {last_err}") from last_err

    def _estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        inp = (input_tokens / 1_000_000) * self.PRICING[0]
        out = (output_tokens / 1_000_000) * self.PRICING[1]
        return round(inp + out, 6)
