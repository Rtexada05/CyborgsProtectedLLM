"""Auth dependencies and client identity helpers for API routes."""

from typing import Optional

from fastapi import Header, HTTPException, Request, status

from ...core.config import settings


async def require_client_api_key(x_api_key: Optional[str] = Header(default=None, alias="X-API-Key")) -> str:
    """Strict API key validation for inbound client requests."""
    expected_key = settings.CLIENT_API_KEY
    if not expected_key or not x_api_key or x_api_key != expected_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )
    return x_api_key


def get_client_ip(request: Request) -> str:
    """Resolve the client IP, optionally honoring trusted proxy headers."""

    direct_ip = request.client.host if request.client and request.client.host else "unknown"
    if not settings.TRUST_PROXY_HEADERS:
        return direct_ip

    forwarded_for = request.headers.get("X-Forwarded-For", "")
    first_ip = forwarded_for.split(",")[0].strip() if forwarded_for else ""
    return first_ip or direct_ip
