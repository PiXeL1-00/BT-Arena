from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any, Optional

from google import genai

from .base import LLMResponse
from .costs import GEMINI_20_FLASH_PRICING
from .key_validation import is_quota_exhaustion
from app.core.domain.exceptions import LLMClientError, QuotaExhaustedError

logger = logging.getLogger(__name__)


class GeminiClient:
    PRICING = GEMINI_20_FLASH_PRICING

    def __init__(self, *, api_key: str, model_name: str) -> None:
        self.model_name = model_name
        self._client = genai.Client(api_key=api_key)

    async def complete(
        self,
        prompt: str,
        *,
        json_schema: Optional[dict[str, Any]] = None,
        temperature: float = 0.0,
        timeout: int = 60,
        retries: int = 3,
    ) -> LLMResponse:
        if json_schema:
            prompt += "\n\nRespond ONLY with valid JSON matching the schema. No extra text."

        last_err: Exception | None = None
        for attempt in range(1, retries + 1):
            try:
                t0 = time.perf_counter()

                # google-genai is sync; run in executor
                resp = await asyncio.wait_for(
                    asyncio.get_event_loop().run_in_executor(
                        None,
                        lambda: self._client.models.generate_content(
                            model=self.model_name,
                            contents=prompt,
                            config={
                                "temperature": temperature,
                                "response_mime_type": "application/json" if json_schema else "text/plain",
                            },
                        ),
                    ),
                    timeout=timeout,
                )
                latency = int((time.perf_counter() - t0) * 1000)
                content = resp.text or ""

                # rough estimate -- Gemini doesn't always return token counts
                cost = 0.0001

                if json_schema:
                    json.loads(content)

                return LLMResponse(text=content, latency_ms=latency, cost_estimate=cost)
            except asyncio.CancelledError:
                # Never swallow cancellation — let it propagate immediately.
                raise
            except Exception as exc:
                if is_quota_exhaustion(exc):
                    raise QuotaExhaustedError("gemini", str(exc)) from exc
                last_err = exc
                wait = min(2 ** attempt, 8)
                logger.warning("Gemini attempt %d/%d failed: %s", attempt, retries, exc)
                if attempt < retries:
                    await asyncio.sleep(wait)

        raise LLMClientError("gemini", f"call failed after {retries} retries: {last_err}") from last_err
