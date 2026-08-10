"""NVIDIA NIM (build.nvidia.com) — OpenAI-compatible inference.

z-ai/glm-5.2 (and other NVIDIA NIM models) are served via the
build.nvidia.com OpenAI-compatible endpoint.
"""

from __future__ import annotations

from typing import Any, Optional

from .costs import DEFAULT_PRICING
from .openai_compatible import OpenAICompatibleClient
from .preflight_constants import PROVIDER_BASE_URLS

_NVIDIA_NAMESPACE = "z-ai/"


class NvidiaClient(OpenAICompatibleClient):
    """NVIDIA NIM client (build.nvidia.com).

    GLM-5.2 and other NIM models can be large, so we use a slightly
    higher default timeout (90s) and more retries than lighter providers.
    """

    BASE_URL = PROVIDER_BASE_URLS["nvidia"]
    PRICING = DEFAULT_PRICING

    async def complete(
        self,
        prompt: str,
        *,
        json_schema: Optional[dict[str, Any]] = None,
        temperature: float = 0.0,
        timeout: int = 90,
        retries: int = 3,
    ) -> "LLMResponse":  # noqa: F821
        return await super().complete(
            prompt,
            json_schema=json_schema,
            temperature=temperature,
            timeout=timeout,
            retries=retries,
        )
