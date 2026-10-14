"""Health check endpoint."""

from __future__ import annotations

import time
from datetime import UTC, datetime

from fastapi import APIRouter
from pydantic import BaseModel

from ..config import get_settings
from ..services.store import get_store

router = APIRouter(tags=["health"])

_STARTED_AT = time.monotonic()


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    uptime_seconds: float
    stored_resumes: int
    timestamp: datetime


@router.get("/health", response_model=HealthResponse, summary="Service health status")
async def health() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(
        status="ok",
        service=settings.app_name,
        version=settings.app_version,
        uptime_seconds=round(time.monotonic() - _STARTED_AT, 3),
        stored_resumes=get_store().count(),
        timestamp=datetime.now(UTC),
    )
