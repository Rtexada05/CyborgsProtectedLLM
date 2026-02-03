"""
Health check endpoint
"""

from fastapi import APIRouter
from datetime import datetime

from ...models.schemas import HealthResponse

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="ok",
        timestamp=datetime.now(),
        version="1.0.0"
    )
