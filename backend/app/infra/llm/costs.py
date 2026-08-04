"""LLM pricing -- USD per 1M tokens (input, output)."""

from typing import Final

OPENAI_GPT4O_PRICING: Final[tuple[float, float]] = (2.50, 10.00)
ANTHROPIC_CLAUDE_35_SONNET_PRICING: Final[tuple[float, float]] = (3.00, 15.00)
MISTRAL_LARGE_PRICING: Final[tuple[float, float]] = (2.00, 6.00)
DEEPSEEK_CHAT_PRICING: Final[tuple[float, float]] = (0.27, 1.10)
GEMINI_20_FLASH_PRICING: Final[tuple[float, float]] = (0.10, 0.40)
GROK_2_PRICING: Final[tuple[float, float]] = (2.00, 10.00)
DEFAULT_PRICING: Final[tuple[float, float]] = (1.00, 2.00)
