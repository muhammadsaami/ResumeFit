"""Rendering, template listing, artifact download and Overleaf export endpoints.

Compilation always happens server-side against an accepted resume state. The
``.tex``/``.pdf`` are returned as short-lived in-memory artifacts, never as
filesystem paths constructed from user input.
"""

from __future__ import annotations

from fastapi import APIRouter, Response

from ..models.render import (
    OverleafRequest,
    OverleafResponse,
    RenderRequest,
    RenderResponse,
    TemplateListResponse,
)
from ..services import rendering
from ..services.artifacts import get_artifact_store
from ..services.latex import DEFAULT_TEMPLATE, list_templates
from ..services.store import get_store

resumes_router = APIRouter(prefix="/resumes", tags=["render"])
artifacts_router = APIRouter(prefix="/artifacts", tags=["artifacts"])


@resumes_router.get(
    "/{resume_id}/render/templates",
    response_model=TemplateListResponse,
    summary="List the available resume templates",
)
async def list_templates_endpoint(resume_id: str) -> TemplateListResponse:
    get_store().get(resume_id)
    return TemplateListResponse(
        templates=list_templates(),
        default_template=DEFAULT_TEMPLATE,
    )


@resumes_router.post(
    "/{resume_id}/render",
    response_model=RenderResponse,
    summary="Render a resume to LaTeX source and, if possible, a PDF",
)
async def render_resume_endpoint(resume_id: str, payload: RenderRequest) -> RenderResponse:
    resume = get_store().get(resume_id)
    return rendering.render_resume(resume, payload.template_id)


@resumes_router.post(
    "/{resume_id}/overleaf",
    response_model=OverleafResponse,
    summary="Prepare a self-contained Overleaf .tex download",
)
async def prepare_overleaf_endpoint(resume_id: str, payload: OverleafRequest) -> OverleafResponse:
    resume = get_store().get(resume_id)
    return rendering.prepare_overleaf(resume, payload.template_id)


@artifacts_router.get(
    "/{artifact_id}",
    summary="Download a generated artifact by opaque id",
)
async def download_artifact(artifact_id: str) -> Response:
    artifact = get_artifact_store().get(artifact_id)
    return Response(
        content=artifact.data,
        media_type=artifact.media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{artifact.filename}"',
            "Cache-Control": "no-store",
        },
    )