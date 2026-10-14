"""Resume upload, retrieval and deletion endpoints.

The endpoint accepts resume text in two ways:

* ``multipart/form-data`` with an optional ``file`` part (PDF/DOCX/TXT) and/or
  a ``text`` field for pasted content.
* ``application/json`` with a ``{"text": "..."}`` body for paste-only flows.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from fastapi import APIRouter, Request, Response, status
from pydantic import ValidationError
from starlette.datastructures import UploadFile

from ..core.errors import ApiError
from ..models.analysis import AnalysisResponse
from ..models.resume import (
    ParsingMetadata,
    ResumeResponse,
    ResumeTextInput,
    SourceType,
)
from ..models.tailoring import (
    ChangeDecisionResponse,
    ChangeEditRequest,
    ChangeListResponse,
    TailorRequest,
    TailorResponse,
)
from ..services.analyzer import analyze_resume
from ..services.artifacts import get_artifact_store
from ..services.extraction import extract_text
from ..services.review import (
    accept_change as apply_change,
)
from ..services.review import (
    build_change_list,
    tailor,
)
from ..services.review import (
    edit_change as revise_change,
)
from ..services.review import (
    reject_change as discard_change,
)
from ..services.store import StoredResume, get_store

router = APIRouter(prefix="/resumes", tags=["resumes"])


@dataclass
class _Candidate:
    """Normalized, validated input ready to be stored."""

    source_type: SourceType
    text: str
    filename: str | None = None
    content_type: str | None = None
    size_bytes: int = 0
    parser: str = "text-input"
    page_count: int | None = None
    warnings: list[str] = field(default_factory=list)


def _to_response(resume: StoredResume) -> ResumeResponse:
    return ResumeResponse(
        resume_id=resume.id,
        status=resume.status,
        extracted_text=resume.text,
        metadata=resume.metadata,
        created_at=resume.created_at,
        expires_at=resume.expires_at,
    )


def _validate_pasted_text(text: str) -> str:
    try:
        return ResumeTextInput(text=text).text
    except ValidationError as exc:
        message = exc.errors()[0].get("msg", "Invalid resume text.")
        raise ApiError(422, "empty_resume", message) from exc


async def _read_json(request: Request) -> _Candidate | None:
    try:
        payload = await request.json()
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ApiError(400, "invalid_request", "The JSON body could not be parsed.") from exc
    if not isinstance(payload, dict) or "text" not in payload:
        raise ApiError(400, "invalid_request", 'Expected a JSON object with a "text" field.')
    raw = payload.get("text")
    if not isinstance(raw, str):
        raise ApiError(400, "invalid_request", 'The "text" field must be a string.')
    text = _validate_pasted_text(raw)
    return _Candidate(
        source_type=SourceType.PASTE,
        text=text.strip(),
        content_type="text/plain",
        size_bytes=len(text.encode("utf-8")),
        parser="pasted-text",
    )


async def _read_form(request: Request) -> _Candidate:
    try:
        form = await request.form()
    except Exception as exc:  # malformed multipart body
        raise ApiError(400, "invalid_request", "The form data could not be parsed.") from exc

    upload = form.get("file")
    raw_text = form.get("text")

    has_file = isinstance(upload, UploadFile) and bool(upload.filename)
    has_text = isinstance(raw_text, str) and bool(raw_text.strip())

    if has_file and has_text:
        raise ApiError(
            400,
            "invalid_request",
            "Provide either an uploaded file or pasted text, not both.",
        )

    if has_file:
        data = await upload.read()
        result = extract_text(upload.filename, data)
        return _Candidate(
            source_type=SourceType.UPLOAD,
            text=result.text.strip(),
            filename=upload.filename,
            content_type=upload.content_type,
            size_bytes=len(data),
            parser=result.parser,
            page_count=result.page_count,
            warnings=result.warnings,
        )

    if has_text:
        assert isinstance(raw_text, str)
        text = _validate_pasted_text(raw_text)
        return _Candidate(
            source_type=SourceType.PASTE,
            text=text.strip(),
            content_type="text/plain",
            size_bytes=len(text.encode("utf-8")),
            parser="pasted-text",
        )

    raise ApiError(400, "empty_resume", "Provide a resume file or pasted resume text.")


async def _read_candidate(request: Request) -> _Candidate:
    content_type = request.headers.get("content-type", "").lower()
    if content_type.startswith(("multipart/form-data", "application/x-www-form-urlencoded")):
        return await _read_form(request)
    if content_type.startswith("application/json"):
        candidate = await _read_json(request)
        if candidate is not None:
            return candidate
    raise ApiError(
        415,
        "unsupported_media_type",
        "Send multipart/form-data with a file or text field, or application/json with text.",
    )


@router.post(
    "",
    response_model=ResumeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a resume from an uploaded file or pasted text",
)
async def create_resume(request: Request) -> ResumeResponse:
    candidate = await _read_candidate(request)

    text = candidate.text
    metadata = ParsingMetadata(
        source_type=candidate.source_type,
        filename=candidate.filename,
        content_type=candidate.content_type,
        size_bytes=candidate.size_bytes,
        parser=candidate.parser,
        character_count=len(text),
        word_count=len(text.split()),
        line_count=len(text.splitlines()),
        page_count=candidate.page_count,
        warnings=candidate.warnings,
    )

    resume = get_store().create(
        text=text,
        source_type=candidate.source_type,
        metadata=metadata,
    )
    return _to_response(resume)


@router.get(
    "/{resume_id}",
    response_model=ResumeResponse,
    summary="Retrieve a previously processed resume",
)
async def get_resume(resume_id: str) -> ResumeResponse:
    return _to_response(get_store().get(resume_id))


@router.post(
    "/{resume_id}/analyze",
    response_model=AnalysisResponse,
    summary="Parse and score a previously uploaded resume",
)
async def analyze_resume_endpoint(resume_id: str) -> AnalysisResponse:
    """Parse the stored resume into structured JSON and score it deterministically."""
    resume = get_store().get(resume_id)
    return analyze_resume(resume.id, resume.text, metadata_warnings=resume.metadata.warnings)


@router.post(
    "/{resume_id}/tailor",
    response_model=TailorResponse,
    summary="Tailor the resume to a job description",
)
async def tailor_resume_endpoint(resume_id: str, payload: TailorRequest) -> TailorResponse:
    """Compare a job description with the resume; never adds missing skills."""
    resume = get_store().get(resume_id)
    return tailor(resume, payload.job_description)


@router.get(
    "/{resume_id}/changes",
    response_model=ChangeListResponse,
    summary="List proposed changes and their review status",
)
async def list_changes_endpoint(resume_id: str) -> ChangeListResponse:
    resume = get_store().get(resume_id)
    return build_change_list(resume)


@router.post(
    "/{resume_id}/changes/{change_id}/accept",
    response_model=ChangeDecisionResponse,
    summary="Accept a proposed change and update the effective resume",
)
async def accept_change_endpoint(resume_id: str, change_id: str) -> ChangeDecisionResponse:
    resume = get_store().get(resume_id)
    change, effective = apply_change(resume, change_id)
    return ChangeDecisionResponse(
        resume_id=resume.id, change=change, applied=True, effective_analysis=effective
    )


@router.post(
    "/{resume_id}/changes/{change_id}/reject",
    response_model=ChangeDecisionResponse,
    summary="Reject a proposed change and preserve the original text",
)
async def reject_change_endpoint(resume_id: str, change_id: str) -> ChangeDecisionResponse:
    resume = get_store().get(resume_id)
    change, effective = discard_change(resume, change_id)
    return ChangeDecisionResponse(
        resume_id=resume.id, change=change, applied=False, effective_analysis=effective
    )


@router.post(
    "/{resume_id}/changes/{change_id}/edit",
    response_model=ChangeDecisionResponse,
    summary="Edit the replacement text of a proposed change",
)
async def edit_change_endpoint(
    resume_id: str, change_id: str, payload: ChangeEditRequest
) -> ChangeDecisionResponse:
    """Store a user-edited replacement; it is only applied when accepted."""
    resume = get_store().get(resume_id)
    change, effective = revise_change(resume, change_id, payload.proposed_text)
    return ChangeDecisionResponse(
        resume_id=resume.id, change=change, applied=False, effective_analysis=effective
    )


@router.delete(
    "/{resume_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete temporary resume data",
)
async def delete_resume(resume_id: str) -> Response:
    get_artifact_store().delete_for_resume(resume_id)
    get_store().delete(resume_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
