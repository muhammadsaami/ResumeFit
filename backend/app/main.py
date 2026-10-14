"""ResumeFit FastAPI application entrypoint.

Run locally with::

    uvicorn app.main:app --reload --port 8000
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import __version__
from .api import routes_health, routes_render, routes_resumes
from .config import get_settings
from .core.errors import register_exception_handlers
from .services.artifacts import get_artifact_store
from .services.store import get_store

logger = logging.getLogger("resumefit")

_CLEANUP_INTERVAL_SECONDS = 60


async def _cleanup_loop() -> None:
    """Periodically remove expired resume data (one-hour TTL)."""
    while True:
        await asyncio.sleep(_CLEANUP_INTERVAL_SECONDS)
        purged = get_store().purge_expired()
        if purged:
            logger.info("Purged %d expired resume(s) from temporary storage.", purged)
        purged_artifacts = get_artifact_store().purge_expired()
        if purged_artifacts:
            logger.info("Purged %d expired artifact(s) from temporary storage.", purged_artifacts)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    task = asyncio.create_task(_cleanup_loop())
    try:
        yield
    finally:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task


def create_app() -> FastAPI:
    settings = get_settings()
    logging.basicConfig(level=settings.log_level.upper())

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version or __version__,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)
    app.include_router(routes_health.router, prefix=settings.api_prefix)
    app.include_router(routes_resumes.router, prefix=settings.api_prefix)
    app.include_router(routes_render.resumes_router, prefix=settings.api_prefix)
    app.include_router(routes_render.artifacts_router, prefix=settings.api_prefix)

    @app.get("/", include_in_schema=False)
    async def root() -> dict[str, str]:
        return {
            "service": settings.app_name,
            "version": settings.app_version,
            "docs": "/docs",
            "health": f"{settings.api_prefix}/health",
        }

    return app


app = create_app()
