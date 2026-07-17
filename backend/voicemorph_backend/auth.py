"""API-key authentication.

Simple shared-secret auth suitable for a personal/self-hosted server, so the
native apps can talk to their backend securely. Checks the ``X-API-Key`` header
(or ``Authorization: Bearer <key>``) against the configured key.
"""

from __future__ import annotations

import hmac

from fastapi import Depends, Header, HTTPException, status

from voicemorph_backend.settings import Settings, get_settings


def _constant_time_eq(a: str, b: str) -> bool:
    return hmac.compare_digest(a.encode("utf-8"), b.encode("utf-8"))


async def require_api_key(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    authorization: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> None:
    provided = x_api_key
    if provided is None and authorization and authorization.lower().startswith("bearer "):
        provided = authorization[7:]
    if provided is None or not _constant_time_eq(provided, settings.api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid API key.",
            headers={"WWW-Authenticate": "Bearer"},
        )
