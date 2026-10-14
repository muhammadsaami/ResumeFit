"""Structured API errors and their FastAPI exception handlers.

Public error responses use a single, predictable envelope::

    {"error": {"code": "...", "message": "...", "details": [...]}}
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class ApiError(Exception):
    """An error that maps directly to a structured HTTP response."""

    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        details: list[dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details or []


def _payload(code: str, message: str, details: list[dict[str, Any]] | None = None) -> dict:
    body: dict[str, Any] = {"error": {"code": code, "message": message}}
    if details:
        body["error"]["details"] = details
    return body


async def api_error_handler(_: Request, exc: ApiError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=_payload(exc.code, exc.message, exc.details),
    )


async def validation_error_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    details = [
        {"location": list(err.get("loc", [])), "message": err.get("msg", "invalid value")}
        for err in exc.errors()
    ]
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=_payload("validation_error", "The request was not valid.", details),
    )


async def http_error_handler(_: Request, exc: StarletteHTTPException) -> JSONResponse:
    code = "not_found" if exc.status_code == status.HTTP_404_NOT_FOUND else "http_error"
    message = exc.detail if isinstance(exc.detail, str) else "Request failed."
    return JSONResponse(status_code=exc.status_code, content=_payload(code, message))


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(ApiError, api_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_error_handler)
