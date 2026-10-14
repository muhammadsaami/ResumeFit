"""Orchestrates parsing + scoring into a single analysis response."""

from __future__ import annotations

from ..core.errors import ApiError
from ..models.analysis import AnalysisResponse
from .parser import parse_resume
from .scoring import analyzed_timestamp, build_issues, score_resume


def analyze_resume(
    resume_id: str,
    text: str,
    metadata_warnings: list[str] | None = None,
) -> AnalysisResponse:
    """Parse and score ``text`` for ``resume_id``.

    ``metadata_warnings`` (for example extraction-quality warnings recorded at
    upload time) are merged into the parser warnings so scoring can distinguish
    "genuinely missing" from "likely not extracted".

    Raises ``ApiError`` when nothing usable can be extracted, so callers never
    receive a fabricated or empty analysis presented as a real result.
    """
    structured = parse_resume(text)
    if metadata_warnings:
        for warning in metadata_warnings:
            if warning not in structured.warnings:
                structured.warnings.append(warning)

    has_entries = bool(
        structured.education
        or structured.experience
        or structured.projects
        or structured.skills.all_skills
        or structured.sections_detected
    )
    has_basics = any(
        [
            structured.basics.name,
            structured.basics.email,
            structured.basics.phone,
            structured.basics.city,
            structured.basics.linkedin,
            structured.basics.github,
        ]
    )

    if not has_basics and not has_entries:
        raise ApiError(
            422,
            "unparseable_resume",
            "The resume text could not be parsed into a usable structure. "
            "Check that it contains standard resume sections and contact details.",
        )

    score = score_resume(structured, text)

    return AnalysisResponse(
        resume_id=resume_id,
        status="analyzed",
        structured_resume=structured,
        ats_score=score,
        detected_issues=build_issues(score),
        parsing_warnings=structured.warnings,
        analyzed_at=analyzed_timestamp(),
    )
