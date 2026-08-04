"""Adapter: BaseLLMClient → AutoGen ChatCompletionClient.

Wraps the existing provider-agnostic BaseLLMClient so it can be used as
the ``model_client`` argument for AutoGen's AssistantAgent and group chats.

All 9 abstract methods of ChatCompletionClient are implemented.
Cost tracking is accumulated across calls via ``accumulated_cost``.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, AsyncGenerator, Literal, Mapping, Optional, Sequence, Union

from autogen_core import CancellationToken
from autogen_core.models import (
    AssistantMessage,
    ChatCompletionClient,
    CreateResult,
    LLMMessage,
    ModelFamily,
    ModelInfo,
    RequestUsage,
    SystemMessage,
    UserMessage,
)
from autogen_core.tools import Tool, ToolSchema
from pydantic import BaseModel

from app.infra.llm.base import BaseLLMClient

logger = logging.getLogger(__name__)

# Safety-net timeout (seconds) per LLM call; prevents indefinite hangs
# even when the underlying provider client has its own timeout/retry logic.
_DEFAULT_CREATE_TIMEOUT: int = 90


class GalileoModelClient(ChatCompletionClient):
    """Wrap an existing BaseLLMClient for AutoGen compatibility.

    Design decisions:
    - Flattens AutoGen's message list into a single prompt string
    - Delegates to the existing provider's ``complete()`` method
    - Tracks cumulative token usage / cost for reporting
    - ``function_calling`` is configurable (must be True when tools are used)
    """

    def __init__(
        self,
        base_client: BaseLLMClient,
        *,
        model_name: str = "unknown",
        provider: str = "unknown",
        enable_function_calling: bool = False,
    ) -> None:
        self._client = base_client
        self._model_name = model_name
        self._provider = provider
        self._function_calling = enable_function_calling
        self._total_prompt_tokens = 0
        self._total_completion_tokens = 0
        self._total_cost = 0.0

    # ------------------------------------------------------------------
    # Required abstract method: create
    # ------------------------------------------------------------------

    async def create(
        self,
        messages: Sequence[LLMMessage],
        *,
        tools: Sequence[Tool | ToolSchema] = [],
        tool_choice: Union[Tool, Literal["auto", "required", "none"]] = "auto",
        json_output: Optional[bool | type[BaseModel]] = None,
        extra_create_args: Mapping[str, Any] = {},
        cancellation_token: Optional[CancellationToken] = None,
    ) -> CreateResult:
        """Flatten messages → single prompt → delegate to BaseLLMClient.

        When a ``cancellation_token`` is provided (group-chat phases), the
        call is wrapped in ``asyncio.ensure_future`` so the token can abort
        it, plus ``asyncio.wait_for`` as a safety-net timeout.

        Without a token (standalone agent calls), the coroutine is awaited
        directly so that deterministic scheduling is preserved.
        """
        prompt = self._messages_to_prompt(messages)

        if cancellation_token is not None:
            # Group-chat path: link future to the token so the AutoGen
            # runtime can abort a stalled call, with a timeout safety-net.
            llm_future = asyncio.ensure_future(
                self._client.complete(prompt, temperature=0.0),
            )
            cancellation_token.link_future(llm_future)
            try:
                resp = await asyncio.wait_for(
                    llm_future, timeout=_DEFAULT_CREATE_TIMEOUT,
                )
            except asyncio.TimeoutError:
                llm_future.cancel()
                raise
        else:
            # Standalone path: direct await keeps deterministic scheduling
            # (the underlying client already has its own timeout / retry).
            resp = await self._client.complete(prompt, temperature=0.0)

        # Rough token estimate (4 chars ≈ 1 token)
        est_prompt_tokens = max(1, len(prompt) // 4)
        est_completion_tokens = max(1, len(resp.text) // 4)
        self._total_prompt_tokens += est_prompt_tokens
        self._total_completion_tokens += est_completion_tokens
        self._total_cost += resp.cost_estimate

        usage = RequestUsage(
            prompt_tokens=est_prompt_tokens,
            completion_tokens=est_completion_tokens,
        )

        return CreateResult(
            finish_reason="stop",
            content=resp.text,
            usage=usage,
            cached=False,
        )

    # ------------------------------------------------------------------
    # Required abstract method: create_stream
    # ------------------------------------------------------------------

    async def create_stream(
        self,
        messages: Sequence[LLMMessage],
        *,
        tools: Sequence[Tool | ToolSchema] = [],
        tool_choice: Union[Tool, Literal["auto", "required", "none"]] = "auto",
        json_output: Optional[bool | type[BaseModel]] = None,
        extra_create_args: Mapping[str, Any] = {},
        cancellation_token: Optional[CancellationToken] = None,
    ) -> AsyncGenerator[Union[str, CreateResult], None]:
        """Streaming not supported; raises immediately."""
        raise NotImplementedError("Streaming not supported by GalileoModelClient")
        yield  # pragma: no cover – makes this an async generator

    # ------------------------------------------------------------------
    # Required abstract methods: token counting
    # ------------------------------------------------------------------

    def count_tokens(
        self,
        messages: Sequence[LLMMessage],
        *,
        tools: Sequence[Tool | ToolSchema] = [],
    ) -> int:
        return sum(len(self._msg_to_str(m)) // 4 for m in messages)

    def remaining_tokens(
        self,
        messages: Sequence[LLMMessage],
        *,
        tools: Sequence[Tool | ToolSchema] = [],
    ) -> int:
        return 128_000 - self.count_tokens(messages, tools=tools)

    # ------------------------------------------------------------------
    # Required abstract properties: usage tracking
    # ------------------------------------------------------------------

    @property
    def total_usage(self) -> RequestUsage:
        return RequestUsage(
            prompt_tokens=self._total_prompt_tokens,
            completion_tokens=self._total_completion_tokens,
        )

    @property
    def actual_usage(self) -> RequestUsage:
        return self.total_usage

    # ------------------------------------------------------------------
    # Required abstract properties: model capabilities
    # ------------------------------------------------------------------

    @property
    def capabilities(self) -> ModelInfo:
        return self.model_info

    @property
    def model_info(self) -> ModelInfo:
        return ModelInfo(
            vision=False,
            function_calling=self._function_calling,
            json_output=True,
            family=ModelFamily.UNKNOWN,
            structured_output=False,
        )

    # ------------------------------------------------------------------
    # Required abstract method: close
    # ------------------------------------------------------------------

    async def close(self) -> None:
        """No-op; the underlying BaseLLMClient has no close semantics."""

    # ------------------------------------------------------------------
    # Cost accessor (not part of AutoGen interface)
    # ------------------------------------------------------------------

    @property
    def accumulated_cost(self) -> float:
        """Total cost accumulated across all ``create()`` calls."""
        return self._total_cost

    def reset_usage(self) -> None:
        self._total_prompt_tokens = 0
        self._total_completion_tokens = 0
        self._total_cost = 0.0

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _messages_to_prompt(messages: Sequence[LLMMessage]) -> str:
        parts: list[str] = []
        for msg in messages:
            parts.append(GalileoModelClient._msg_to_str(msg))
        return "\n\n".join(parts)

    @staticmethod
    def _msg_to_str(msg: LLMMessage) -> str:
        if isinstance(msg, SystemMessage):
            return f"[System]\n{msg.content}"
        if isinstance(msg, UserMessage):
            content = msg.content if isinstance(msg.content, str) else str(msg.content)
            return f"[User]\n{content}"
        if isinstance(msg, AssistantMessage):
            return f"[Assistant]\n{msg.content}"
        return str(msg)
