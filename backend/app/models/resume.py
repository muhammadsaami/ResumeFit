"""Request/response and internal models for resume handling."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator

# A resume must contain at least this many non-whitespace characters.
MIN_RESUME_CHARS = 20


class SourceType(str, Enum):
    """Where the resume text came from."""

    UPLOAD = "upload"
    PASTE = "paste"


class ExtractionStatus(str, Enum):
    """Whether text was successfully obtained from the input."""

    PROCESSED = "processed"


class ResumeTextInput(BaseModel):
    """Validation model for pasted resume text."""

    text: str = Field(..., description="Raw resume text.")

    @field_validator("text")
    @classmethod
    def _not_empty(cls, value: str) -> str:
        if len(value.strip()) < MIN_RESUME_CHARS:
            raise ValueError(
                f"Resume text must contain at least {MIN_RESUME_CHARS} non-whitespace characters."
            )
        return value


class ParsingMetadata(BaseModel):
    """Non-sensitive metadata describing how the resume was processed."""

    model_config = ConfigDict(extra="forbid")

    source_type: SourceType
    filename: str | None = None
    content_type: str | None = None
    size_bytes: int
    parser: str
    character_count: int
    word_count: int
    line_count: int
    page_count: int | None = None
    warnings: list[str] = Field(default_factory=list)


class ResumeResponse(BaseModel):
    """Public representation of a processed resume.

    Internal storage models are kept separate so that storage details
    (raw text layout, expiry bookkeeping) never leak into the API surface.
    """

    model_config = ConfigDict(extra="forbid")

    resume_id: str
    status: ExtractionStatus
    extracted_text: str
    metadata: ParsingMetadata
    created_at: datetime
    expires_at: datetime
