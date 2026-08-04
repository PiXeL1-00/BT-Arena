"""Version-aware prompt template loader.

Templates are stored as plain-text files in ``backend/prompts/<version>/``.
Each file uses Python ``str.format_map()`` placeholders (e.g. ``{role}``).
"""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path

logger = logging.getLogger(__name__)

_PROMPTS_ROOT = Path(__file__).resolve().parent.parent.parent.parent / "prompts"

# Available prompt versions (newest first)
AVAILABLE_VERSIONS: list[str] = sorted(
    [d.name for d in _PROMPTS_ROOT.iterdir() if d.is_dir()],
    reverse=True,
) if _PROMPTS_ROOT.exists() else []

DEFAULT_VERSION = AVAILABLE_VERSIONS[0] if AVAILABLE_VERSIONS else "v1"


@lru_cache(maxsize=64)
def load_template(name: str, *, version: str = DEFAULT_VERSION) -> str:
    """Load a prompt template by name and version.

    Args:
        name: Template filename without extension (e.g. ``"proposal"``).
        version: Prompt version directory (e.g. ``"v1"``).

    Returns:
        The raw template string with ``{placeholders}``.

    Raises:
        FileNotFoundError: If the template file does not exist.
    """
    path = _PROMPTS_ROOT / version / f"{name}.txt"
    if not path.exists():
        raise FileNotFoundError(f"Prompt template not found: {path}")
    return path.read_text(encoding="utf-8")


def get_prompt_version() -> str:
    """Return the currently active prompt version string."""
    return DEFAULT_VERSION
