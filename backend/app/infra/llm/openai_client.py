from __future__ import annotations

import json
import logging
import time
from typing import Any, Optional

from .base import LLMResponse
from .costs import OPENAI_GPT4O_PRICING
from .openai_compatible import OpenAICompatibleClient
from .preflight_constants import PROVIDER_BASE_URLS

logger = logging.getLogger(__name__)


class OpenAIClient(OpenAICompatibleClient):
    """OpenAI with native Structured Outputs for the Judge role."""

    BASE_URL = PROVIDER_BASE_URLS["openai"]
    PRICING = OPENAI_GPT4O_PRICING

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
            kwargs["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": "judge_decision",
                    "strict": True,
                    "schema": json_schema,
                },
            }

        t0 = time.perf_counter()
        resp = await self._client.chat.completions.create(**kwargs)
        latency = int((time.perf_counter() - t0) * 1000)

        content = resp.choices[0].message.content or ""
        cost = self._estimate_cost(resp.usage)

        if json_schema:
            json.loads(content)

        return LLMResponse(text=content, latency_ms=latency, cost_estimate=cost)
