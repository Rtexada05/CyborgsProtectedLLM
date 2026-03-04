"""Auth dependencies for API routes."""

from typing import Optional

from fastapi import Header, HTTPException, status

from ...core.config import settings


async def require_client_api_key(x_api_key: Optional[str] = Header(default=None, alias="X-API-Key")) -> None:
    """Strict API key validation for inbound client requests."""
    expected_key = settings.CLIENT_API_KEY
    if not expected_key or not x_api_key or x_api_key != expected_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )
