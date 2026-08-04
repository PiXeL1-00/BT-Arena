"""MoonshotAI via Together AI (OpenAI-compatible).

Together AI requires the full namespace 'moonshotai/<model>' in API calls.
"""

from __future__ import annotations

from typing import Any, Optional

from .costs import DEFAULT_PRICING
from .base import LLMResponse
from .openai_compatible import OpenAICompatibleClient
from .preflight_constants import PROVIDER_BASE_URLS

_NAMESPACE = "moonshotai/"


class MoonshotAIClient(OpenAICompatibleClient):
    """MoonshotAI via Together AI.

    Kimi-K2.5 is a large model (~45s per call), so we use a higher
    default timeout (120s) and more retries than other providers.
    """

    BASE_URL = PROVIDER_BASE_URLS["moonshotai"]
    PRICING = DEFAULT_PRICING

    def __init__(self, *, api_key: str, model_name: str) -> None:
        # Together AI expects the full namespace: moonshotai/<model>
        if not model_name.startswith(_NAMESPACE):
            model_name = f"{_NAMESPACE}{model_name}"
        super().__init__(api_key=api_key, model_name=model_name)

    async def complete(
        self,
        prompt: str,
        *,
        json_schema: Optional[dict[str, Any]] = None,
        temperature: float = 0.0,
        timeout: int = 120,
        retries: int = 4,
    ) -> LLMResponse:
        return await super().complete(
            prompt,
            json_schema=json_schema,
            temperature=temperature,
            timeout=timeout,
            retries=retries,
        )

    async def _call(
        self, prompt: str, *,
        json_schema: Optional[dict[str, Any]],
        temperature: float, timeout: int,
    ) -> LLMResponse:
        # Belt-and-suspenders: ensure namespace prefix at call time too
        if not self.model_name.startswith(_NAMESPACE):
            self.model_name = f"{_NAMESPACE}{self.model_name}"
        return await super()._call(
            prompt, json_schema=json_schema,
            temperature=temperature, timeout=timeout,
        )
