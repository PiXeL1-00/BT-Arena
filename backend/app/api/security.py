"""Admin API-key authentication dependency."""

from __future__ import annotations

import secrets
from typing import Annotated

from fastapi import Header, HTTPException, status

from app.config import settings

_MISSING_KEY_MSG = "Admin API key not configured on server"
_INVALID_KEY_MSG = "Invalid admin API key"


async def verify_admin_key(
    x_admin_key: Annotated[str | None, Header()] = None,
) -> None:
    if settings.admin_api_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=_MISSING_KEY_MSG,
        )
    if x_admin_key is None or not secrets.compare_digest(
        x_admin_key, settings.admin_api_key,
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=_INVALID_KEY_MSG,
        )
