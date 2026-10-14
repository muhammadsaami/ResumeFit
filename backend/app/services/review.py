"""Change-review orchestration: planning, accept/reject and effective resume.

The effective resume starts as the original text. Accepting a replace change
rewrites exactly one source line in the effective text; rejecting restores the
original line. Re-scoring always runs against the effective text so the reported
ATS score reflects accepted changes. Nothing is reported as applied if the
underlying update fails.
"""

from __future__ import annotations

from ..core.errors import ApiError
from ..models.analysis import AnalysisResponse
from ..models.tailoring import (
    ChangeAction,
    ChangeCategory,
    ChangeListResponse,
    ChangeOrigin,
    ChangeStatus,
    ChangeSummary,
    GuardStatus,
    ResumeChange,
    TailorResponse,
)
from .analyzer import analyze_resume
from .autofix import plan_changes
from .guard import check_change
from .parser import parse_resume
from .store import StoredResume, get_store
from .tailoring import analyze_job_description, plan_tailor_changes

_STATUS_ORDER = {
    ChangeStatus.PROPOSED: 0,
    ChangeStatus.ACCEPTED: 1,
    ChangeStatus.REJECTED: 2,
}


def _effective_analysis(resume: StoredResume) -> AnalysisResponse:
    return analyze_resume(resume.id, resume.effective_text)


def _ordered_changes(changes: dict[str, ResumeChange]) -> list[ResumeChange]:
    return sorted(
        changes.values(),
        key=lambda c: (_STATUS_ORDER[c.status], c.source_line or 0, c.id),
    )


def _summary(changes: list[ResumeChange]) -> ChangeSummary:
    return ChangeSummary(
        total=len(changes),
        proposed=sum(1 for c in changes if c.status == ChangeStatus.PROPOSED),
        accepted=sum(1 for c in changes if c.status == ChangeStatus.ACCEPTED),
        rejected=sum(1 for c in changes if c.status == ChangeStatus.REJECTED),
        safe=sum(1 for c in changes if c.guard_status == GuardStatus.SAFE),
        needs_review=sum(1 for c in changes if c.guard_status == GuardStatus.NEEDS_REVIEW),
        unsafe=sum(1 for c in changes if c.guard_status == GuardStatus.UNSAFE),
    )


def _merge_plan(
    existing: dict[str, ResumeChange], planned: list[ResumeChange]
) -> dict[str, ResumeChange]:
    """Refresh pending changes while preserving decisions and user edits."""
    merged = dict(existing)
    for change in planned:
        previous = merged.get(change.id)
        if previous is not None:
            change.status = previous.status
            if previous.user_edited and previous.proposed_text is not None:
                # Keep the user's replacement text and its guard verdict so a
                # refresh never silently discards a manual edit.
                change.proposed_text = previous.proposed_text
                change.guard_status = previous.guard_status
                change.guard_reasons = list(previous.guard_reasons)
                change.applicable = previous.applicable
                change.user_edited = True
        merged[change.id] = change
    return merged


def ensure_plan(resume: StoredResume) -> StoredResume:
    """Generate the auto-fix plan once for this resume."""
    if not resume.plan_generated:
        structured = parse_resume(resume.effective_text)
        resume.changes = _merge_plan(
            resume.changes, plan_changes(structured, resume.effective_text)
        )
        resume.plan_generated = True
        get_store().save(resume)
    return resume


def regenerate_plan(resume: StoredResume) -> None:
    structured = parse_resume(resume.effective_text)
    resume.changes = _merge_plan(
        resume.changes, plan_changes(structured, resume.effective_text)
    )


def build_change_list(resume: StoredResume) -> ChangeListResponse:
    ensure_plan(resume)
    changes = _ordered_changes(resume.changes)
    return ChangeListResponse(
        resume_id=resume.id,
        summary=_summary(changes),
        changes=changes,
        effective_analysis=_effective_analysis(resume),
    )


def _find_change(resume: StoredResume, change_id: str) -> ResumeChange:
    change = resume.changes.get(change_id)
    if change is None:
        raise ApiError(404, "change_not_found", "No proposed change exists for that id.")
    return change


def accept_change(resume: StoredResume, change_id: str) -> tuple[ResumeChange, AnalysisResponse]:
    ensure_plan(resume)
    change = _find_change(resume, change_id)

    if change.action != ChangeAction.REPLACE or not change.proposed_text:
        raise ApiError(
            422,
            "change_not_applicable",
            "This item is an advisory flag; there is no text to apply.",
        )
    if change.guard_status == GuardStatus.UNSAFE:
        raise ApiError(
            422,
            "unsafe_change_blocked",
            "The fabrication guard flagged this change as unsafe and it cannot be applied.",
            details=[{"message": reason} for reason in change.guard_reasons],
        )
    if change.status == ChangeStatus.ACCEPTED:
        return change, _effective_analysis(resume)

    lines = resume.effective_text.splitlines()
    index = (change.source_line or 0) - 1
    end_index = (change.source_end_line or change.source_line or 0) - 1
    if not (0 <= index < len(lines)) or not (index <= end_index < len(lines)):
        raise ApiError(409, "change_conflict", "The source line no longer exists.")
    if "\n".join(lines[index : end_index + 1]).strip() != change.original_text.strip():
        raise ApiError(
            409,
            "change_conflict",
            "The resume text has changed since this edit was proposed; re-run the analysis.",
        )

    candidate_lines = list(lines)
    candidate_lines[index : end_index + 1] = (change.proposed_text or "").split("\n")
    candidate_text = "\n".join(candidate_lines)

    # Score first: if the candidate cannot be parsed the commit never happens.
    effective = analyze_resume(resume.id, candidate_text)

    resume.effective_text = candidate_text
    change.status = ChangeStatus.ACCEPTED
    regenerate_plan(resume)
    get_store().save(resume)
    return change, effective


def reject_change(resume: StoredResume, change_id: str) -> tuple[ResumeChange, AnalysisResponse]:
    ensure_plan(resume)
    change = _find_change(resume, change_id)

    if change.status == ChangeStatus.ACCEPTED and change.source_line is not None:
        lines = resume.effective_text.splitlines()
        index = change.source_line - 1
        proposed_lines = (change.proposed_text or "").split("\n")
        span = len(proposed_lines)
        if (
            0 <= index < len(lines)
            and change.proposed_text
            and "\n".join(lines[index : index + span]).strip() == change.proposed_text.strip()
        ):
            lines[index : index + span] = change.original_text.split("\n")
            resume.effective_text = "\n".join(lines)

    change.status = ChangeStatus.REJECTED
    regenerate_plan(resume)
    get_store().save(resume)
    return change, _effective_analysis(resume)


def edit_change(
    resume: StoredResume, change_id: str, proposed_text: str
) -> tuple[ResumeChange, AnalysisResponse]:
    """Replace a proposed change's text with the user's edit.

    The edit is re-validated by the fabrication guard; it is stored but not applied
    until the user explicitly accepts it, so the original text is never touched.
    """
    ensure_plan(resume)
    change = _find_change(resume, change_id)

    if change.action != ChangeAction.REPLACE or change.proposed_text is None:
        raise ApiError(
            422,
            "change_not_editable",
            "Only text rewrites can be edited; this item is an advisory flag.",
        )
    if change.status == ChangeStatus.ACCEPTED:
        raise ApiError(
            409,
            "change_already_applied",
            "Reject the change before editing it, then accept your version.",
        )

    edited = proposed_text.strip()
    if not edited:
        raise ApiError(422, "empty_edit", "The edited text cannot be empty.")

    structured = parse_resume(resume.effective_text)
    guard_status, guard_reasons = check_change(
        edited,
        original=change.original_text,
        structured=structured,
        source_text=resume.effective_text,
    )

    change.proposed_text = edited
    change.guard_status = guard_status
    change.guard_reasons = guard_reasons
    change.applicable = guard_status != GuardStatus.UNSAFE
    change.user_edited = True
    change.status = ChangeStatus.PROPOSED
    get_store().save(resume)
    return change, _effective_analysis(resume)


def tailor(resume: StoredResume, job_description: str) -> TailorResponse:
    ensure_plan(resume)
    structured = parse_resume(resume.effective_text)
    analysis = analyze_job_description(structured, job_description, resume.effective_text)

    # Refresh tailor-sourced changes only; keep autofix decisions intact.
    preserved = {
        cid: change
        for cid, change in resume.changes.items()
        if change.origin != ChangeOrigin.TAILOR
    }
    resume.changes = preserved
    for change in plan_tailor_changes(structured, analysis, resume.effective_text):
        resume.changes[change.id] = change
    get_store().save(resume)

    change_list = build_change_list(resume)
    bullet_suggestions = [
        change
        for change in change_list.changes
        if change.category == ChangeCategory.BULLET_REWRITE
        and change.origin == ChangeOrigin.TAILOR
    ]
    return TailorResponse(
        resume_id=resume.id,
        job_description_stats=analysis.stats,
        matched_skills=analysis.matched_skills,
        missing_skills=analysis.missing_skills,
        matched_keywords=analysis.matched_keywords,
        missing_keywords=analysis.missing_keywords,
        evidence_backed_skills=analysis.evidence_backed_skills,
        suggested_skill_order=analysis.suggested_skill_order,
        bullet_suggestions=bullet_suggestions,
        explanations=analysis.explanations,
        match_percentage=analysis.match_percentage,
        match_note=analysis.match_note,
        changes=change_list,
    )
