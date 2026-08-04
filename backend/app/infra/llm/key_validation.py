"""Error classification for LLM API key validation."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

# Regex pattern for detecting billing/quota-related error messages
BILLING_KEYWORDS = re.compile(
    r"(billing|quota|credits?|plan|spend\s*limit|balance|payment|subscription|account\s*limit|budget)",
    re.IGNORECASE,
)


class KeyValidationStatus(str, Enum):
    """Status of API key validation."""

    VALID = "VALID"
    INVALID_KEY = "INVALID_KEY"
    NO_FUNDS_OR_BUDGET = "NO_FUNDS_OR_BUDGET"
    RATE_LIMIT = "RATE_LIMIT"
    PERMISSION_OR_REGION = "PERMISSION_OR_REGION"
    PROVIDER_OUTAGE = "PROVIDER_OUTAGE"
    TIMEOUT = "TIMEOUT"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"


@dataclass
class KeyValidationResult:
    """Result of API key validation."""

    status: KeyValidationStatus
    provider: str
    api_key_env: str
    error_message: Optional[str] = None
    request_id: Optional[str] = None
    http_status: Optional[int] = None
    validated_at: datetime = None

    def __post_init__(self) -> None:
        """Set validated_at if not provided."""
        if self.validated_at is None:
            self.validated_at = datetime.now(timezone.utc)


def classify_error(
    status_code: Optional[int],
    error_message: Optional[str],
    error_type: Optional[str] = None,
) -> KeyValidationStatus:
    """Classify error based on HTTP status, message, and provider-specific type.

    Args:
        status_code: HTTP status code from the API response
        error_message: Error message from the exception
        error_type: Provider-specific error type field (e.g., Anthropic's "type")

    Returns:
        KeyValidationStatus enum value
    """
    # Handle missing status code (extract from message if possible)
    if status_code is None:
        # Try to extract from error message (some SDKs include it)
        status_match = re.search(r"\b(40[0-9]|50[0-9])\b", str(error_message) or "")
        if status_match:
            status_code = int(status_match.group(1))
        else:
            # If we can't determine, check message content
            msg_lower = (error_message or "").lower()
            if (
                "authentication" in msg_lower
                or "invalid" in msg_lower
                or "unauthorized" in msg_lower
            ):
                return KeyValidationStatus.INVALID_KEY
            return KeyValidationStatus.UNKNOWN_ERROR

    # Classification by status code
    if status_code == 401:
        return KeyValidationStatus.INVALID_KEY
    elif status_code == 403:
        return KeyValidationStatus.PERMISSION_OR_REGION
    elif status_code == 429:
        # Critical: Distinguish rate limit from billing/quota
        msg = (error_message or "").lower()
        error_type_lower = (error_type or "").lower()

        # Check for billing/quota indicators
        if (
            BILLING_KEYWORDS.search(msg)
            or BILLING_KEYWORDS.search(error_type_lower)
            or "insufficient" in msg
            or ("exceeded" in msg and ("quota" in msg or "limit" in msg))
        ):
            return KeyValidationStatus.NO_FUNDS_OR_BUDGET
        else:
            return KeyValidationStatus.RATE_LIMIT
    elif status_code in (500, 502, 503, 504, 529):
        return KeyValidationStatus.PROVIDER_OUTAGE
    elif status_code == 408:
        return KeyValidationStatus.TIMEOUT
    else:
        return KeyValidationStatus.UNKNOWN_ERROR


def is_quota_exhaustion(exc: Exception) -> bool:
    """Check if an exception indicates quota/billing exhaustion (not transient rate-limit)."""
    status = getattr(exc, "status_code", None) or getattr(exc, "status", None)
    msg = str(exc).lower()

    if status == 429 and (
        BILLING_KEYWORDS.search(msg)
        or "insufficient" in msg
        or ("exceeded" in msg and ("quota" in msg or "limit" in msg))
    ):
        return True

    if "resource_exhausted" in msg and BILLING_KEYWORDS.search(msg):
        return True

    return False

