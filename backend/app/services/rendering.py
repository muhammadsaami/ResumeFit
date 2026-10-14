"""Render orchestration: turn an accepted resume state into .tex and PDF.

Only the *effective* text of a resume is rendered. Rejected changes never reach
this pipeline, and rejected content list length: none here.
"""

from __future__ import annotations

from datetime import UTC, datetime

from ..config import get_settings
from ..core.errors import ApiError
from ..models.render import (
    ArtifactInfo,
    ArtifactKind,
    OverleafResponse,
    RenderResponse,
    RenderStatus,
)
from ..services import latex
from ..services.artifacts import get_artifact_store
from ..services.compiler import compile_latex, detect_compiler
from ..services.parser import parse_resume
from ..services.store import StoredResume

_OVERLEAF_INSTRUCTIONS = [
    "Download the .tex file below.",
    "Sign in at overleaf.com and create a new blank project (or open an existing one).",
    "Replace the project's main.tex with the downloaded file.",
    "Select the default compiler (pdfLaTeX) and wait for the rebuild to finish.",
    "Your resume content never leaves these instructions as a public link; process it manually.",
]

_OVERLEAF_NOTE = (
    "Overleaf offers no verified server-side project-creation API for private content, "
    "so the truthful workflow is a self-contained .tex download plus manual import. "
    "Nothing from your resume is shared publicly or uploaded by ResumeFit."
)


def _store_artifact(
    resume: StoredResume,
    kind: ArtifactKind,
    filename: str,
    media_type: str,
    data: bytes,
) -> ArtifactInfo:
    artifact = get_artifact_store().create(
        resume_id=resume.id,
        kind=kind.value,
        filename=filename,
        media_type=media_type,
        data=data,
        expires_at=resume.expires_at,
    )
    download_url = f"{get_settings().api_prefix}/artifacts/{artifact.id}"
    return ArtifactInfo(
        artifact_id=artifact.id,
        kind=kind,
        filename=filename,
        media_type=media_type,
        size_bytes=len(data),
        download_url=download_url,
    )


def render_resume(resume: StoredResume, template_id: str) -> RenderResponse:
    """Generate .tex (+ PDF when a compiler exists) for a stored resume."""
    try:
        latex.validate_template(template_id)
    except KeyError as exc:
        raise ApiError(422, "invalid_template", "Unknown template id.") from exc

    structured = parse_resume(resume.effective_text)
    tex_source = latex.render_template(template_id, structured)
    filename_stem = f"{template_id}-resume"

    tex_info = _store_artifact(
        resume,
        ArtifactKind.TEX,
        f"{filename_stem}.tex",
        "application/x-tex",
        tex_source.encode("utf-8"),
    )

    compiler = detect_compiler()
    if compiler is None:
        return RenderResponse(
            resume_id=resume.id,
            template_id=template_id,
            status=RenderStatus.COMPILER_UNAVAILABLE,
            compiler=None,
            tex=tex_info,
            message=(
                "No LaTeX compiler is available. Install Tectonic "
                "locally or set latex_compiler."
            ),
            rendered_at=datetime.now(UTC),
        )

    result = compile_latex(tex_source, compiler)
    if result.status == "success" and result.pdf is not None:
        pdf_info = _store_artifact(
            resume,
            ArtifactKind.PDF,
            f"{filename_stem}.pdf",
            "application/pdf",
            result.pdf,
        )
        return RenderResponse(
            resume_id=resume.id,
            template_id=template_id,
            status=RenderStatus.SUCCESS,
            compiler=result.compiler,
            page_count=result.page_count,
            pdf=pdf_info,
            tex=tex_info,
            rendered_at=datetime.now(UTC),
        )

    status_by_result = {
        "compiler_unavailable": RenderStatus.COMPILER_UNAVAILABLE,
        "compilation_failed": RenderStatus.COMPILATION_FAILED,
        "timeout": RenderStatus.TIMEOUT,
        "too_large": RenderStatus.TOO_LARGE,
    }
    message_by_result = {
        "compilation_failed": "LaTeX compilation failed. See the log for details.",
        "timeout": "LaTeX compilation timed out. Try a smaller resume.",
        "too_large": "The rendered document is too large to compile safely.",
    }
    return RenderResponse(
        resume_id=resume.id,
        template_id=template_id,
        status=status_by_result[result.status],
        compiler=result.compiler,
        tex=tex_info,
        log=result.log,
        message=message_by_result.get(result.status),
        rendered_at=datetime.now(UTC),
    )


def prepare_overleaf(resume: StoredResume, template_id: str) -> OverleafResponse:
    """Prepare a self-contained .tex download for manual import into Overleaf."""
    try:
        latex.validate_template(template_id)
    except KeyError as exc:
        raise ApiError(422, "invalid_template", "Unknown template id.") from exc

    structured = parse_resume(resume.effective_text)
    tex_source = latex.render_template(template_id, structured)
    tex_info = _store_artifact(
        resume,
        ArtifactKind.TEX,
        f"{template_id}-resume.tex",
        "application/x-tex",
        tex_source.encode("utf-8"),
    )
    return OverleafResponse(
        resume_id=resume.id,
        template_id=template_id,
        method="download",
        tex=tex_info,
        note=_OVERLEAF_NOTE,
        instructions=_OVERLEAF_INSTRUCTIONS,
    )