"""Unit tests for the deterministic auto-fix planner."""

from __future__ import annotations

from app.models.tailoring import ChangeAction, ChangeCategory, ChangeStatus, GuardStatus
from app.services.autofix import plan_changes
from app.services.parser import parse_resume

from .synthetic import (
    ALIAS_RESUME,
    COMPLETE_RESUME,
    DUPLICATE_SKILLS_RESUME,
    LONG_BULLET_RESUME,
    MISSING_SECTIONS_RESUME,
)


def _plan(text: str):
    return plan_changes(parse_resume(text), text)


def test_change_ids_are_stable_and_unique() -> None:
    first = _plan(ALIAS_RESUME)
    second = _plan(ALIAS_RESUME)
    ids = [change.id for change in first]
    assert ids
    assert len(ids) == len(set(ids))
    assert [change.id for change in second] == ids
    assert all(change_id.startswith("chg_") for change_id in ids)
    assert all(change.status == ChangeStatus.PROPOSED for change in first)


def test_clean_resume_produces_no_false_positive_edits() -> None:
    # A well-formed resume should not trigger speculative rewrites. In particular
    # current-role bullets keep their tense (completed work in a live role is
    # legitimately past tense).
    changes = _plan(COMPLETE_RESUME)
    assert [change for change in changes if change.action == ChangeAction.REPLACE] == []


def test_no_autofix_change_is_unsafe() -> None:
    for text in (COMPLETE_RESUME, DUPLICATE_SKILLS_RESUME, LONG_BULLET_RESUME):
        assert all(change.guard_status != GuardStatus.UNSAFE for change in _plan(text))


def test_duplicate_skills_are_deduplicated() -> None:
    changes = _plan(DUPLICATE_SKILLS_RESUME)
    duplicate_changes = [
        change for change in changes if change.category == ChangeCategory.DUPLICATE_SKILLS
    ]
    assert duplicate_changes
    proposed = duplicate_changes[0].proposed_text or ""
    tokens = [token.strip().lower() for token in proposed.split(",") if token.strip()]
    assert len(tokens) == len(set(tokens))
    assert duplicate_changes[0].action == ChangeAction.REPLACE


def test_first_person_bullet_is_flagged() -> None:
    changes = _plan(LONG_BULLET_RESUME)
    assert any(change.category == ChangeCategory.FIRST_PERSON for change in changes)


def test_long_bullet_produces_a_reviewable_edit() -> None:
    changes = _plan(LONG_BULLET_RESUME)
    long_bullet_edits = [
        change
        for change in changes
        if change.action == ChangeAction.REPLACE
        and change.source_line is not None
        and "Responsible for a very broad" in (change.original_text or "")
    ]
    assert long_bullet_edits


def test_missing_sections_are_reported_as_flags() -> None:
    changes = _plan(MISSING_SECTIONS_RESUME)
    missing = [change for change in changes if change.category == ChangeCategory.MISSING_SECTION]
    assert len(missing) >= 2
    assert all(change.action == ChangeAction.FLAG for change in missing)


def test_plan_changes_never_inserts_unmentioned_skills() -> None:
    changes = _plan(COMPLETE_RESUME)
    resume_skills = set(parse_resume(COMPLETE_RESUME).skills.all_skills)
    for change in changes:
        if change.action != ChangeAction.REPLACE or not change.proposed_text:
            continue
        if change.category not in (
            ChangeCategory.SKILL_GROUPING,
            ChangeCategory.DUPLICATE_SKILLS,
            ChangeCategory.SKILL_ORDERING,
        ):
            continue
        proposed_skills = {
            token.strip() for token in change.proposed_text.split(",") if token.strip()
        }
        assert proposed_skills <= resume_skills
