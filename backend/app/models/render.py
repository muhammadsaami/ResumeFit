"""Models for LaTeX rendering, artifacts and Overleaf export."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class RenderStatus(str, Enum):
    """The outcome of a render job.

    A PDF is only ever reported once compilation really produced one.
    """

    SUCCESS = "success"
    COMPILER_UNAVAILABLE = "compiler_unavailable"
    COMPILATION_FAILED = "compilation_failed"
    TIMEOUT = "timeout"
    TOO_LARGE = "too_large"


class TemplateInfo(BaseModel):
    """Metadata for an available resume template."""

    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    description: str


class TemplateListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    templates: list[TemplateInfo]
    default_template: str


class RenderRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    template_id: str = Field(default="classic", description="One of the registered template ids.")


class ArtifactKind(str, Enum):
    PDF = "pdf"
    TEX = "tex"


class ArtifactInfo(BaseModel):
    """A stored artifact a client can download via ``download_url``."""

    model_config = ConfigDict(extra="forbid")

    artifact_id: str
    kind: ArtifactKind
    filename: str
    media_type: str
    size_bytes: int
    download_url: str


class RenderResponse(BaseModel):
    """Response for ``POST /api/v1/resumes/{resume_id}/render``."""

    model_config = ConfigDict(extra="forbid")

    resume_id: str
    template_id: str
    status: RenderStatus
    compiler: str | None = None
    page_count: int | None = None
    pdf: ArtifactInfo | None = None
    tex: ArtifactInfo
    log: str | None = None
    message: str | None = None
    rendered_at: datetime


class OverleafRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    template_id: str = Field(default="classic", description="One of the registered template ids.")


class OverleafResponse(BaseModel):
    """Response for ``POST /api/v1/resumes/{resume_id}/overleaf``.

    Resume content is never published to a public URL. Overleaf has no verified
    server-side project-creation API for private content, so the truthful workflow
    is a self-contained ``.tex`` download plus manual import instructions.
    """

    model_config = ConfigDict(extra="forbid")

    resume_id: str
    template_id: str
    method: str = "download"
    tex: ArtifactInfo
    note: str
    instructions: list[str]