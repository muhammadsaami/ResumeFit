"""Application configuration loaded from environment variables."""

from __future__ import annotations

from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings.

    All values can be overridden with ``RESUMEFIT_``-prefixed environment
    variables (or a ``.env`` file placed next to the backend package).
    """

    model_config = SettingsConfigDict(
        env_prefix="RESUMEFIT_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "ResumeFit API"
    app_version: str = "0.1.0"
    api_prefix: str = "/api/v1"

    # 5 MB maximum upload, matching the product requirement.
    max_upload_bytes: int = 5 * 1024 * 1024

    # Temporary resume data expires after one hour.
    resume_ttl_seconds: int = 60 * 60

    # Origins allowed to call the API during local development.
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    log_level: str = "info"

    # --- LaTeX rendering ------------------------------------------------------
    # Which LaTeX engine to use for PDF generation. Options:
    #   "auto"  - search for tectonic, then xelatex, then pdflatex
    #   "none"  - never compile (PDF generation returns compiler_unavailable)
    #   a name or path - use that specific executable (e.g. "pdflatex")
    latex_compiler: str = "auto"
    latex_timeout_seconds: int = 60
    # Refuse to download any TeX package at render time. Requires a warm cache.
    latex_only_cached: bool = False
    # Hard size ceilings used before/after compilation.
    latex_max_tex_bytes: int = 300_000
    latex_max_pdf_bytes: int = 15_000_000
    # Maximum number of characters of compiler log returned to the client.
    latex_max_log_chars: int = 4000

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        """Allow a comma-separated string as well as a JSON/list value."""
        if isinstance(value, str):
            stripped = value.strip()
            if stripped.startswith("["):
                return value  # let pydantic parse JSON
            return [item.strip() for item in stripped.split(",") if item.strip()]
        return value

    @field_validator("max_upload_bytes", "resume_ttl_seconds", "latex_timeout_seconds")
    @classmethod
    def _must_be_positive(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("must be a positive integer")
        return value


@lru_cache
def get_settings() -> Settings:
    """Return a cached ``Settings`` instance."""
    return Settings()
