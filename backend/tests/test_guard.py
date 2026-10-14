"""Unit tests for the deterministic fabrication guard."""

from __future__ import annotations

from app.models.tailoring import GuardStatus
from app.services.guard import check_change
from app.services.parser import parse_resume

from .synthetic import COMPLETE_RESUME, LONG_BULLET_RESUME


def _structured(text: str):
    return parse_resume(text)


def test_safe_rewrite_passes_guard() -> None:
    status, reasons = check_change(
        "Built reliable REST APIs in Python serving internal tools.",
        original="Built REST APIs in Python that serve internal tools reliably.",
        structured=_structured(COMPLETE_RESUME),
        source_text=COMPLETE_RESUME,
    )
    assert status == GuardStatus.SAFE
    assert reasons == []


def test_invented_metric_is_unsafe() -> None:
    status, reasons = check_change(
        "Built 5 REST APIs in Python.",
        original="Built REST APIs in Python.",
        structured=_structured(COMPLETE_RESUME),
        source_text=COMPLETE_RESUME,
    )
    assert status == GuardStatus.UNSAFE
    assert any("number" in reason.lower() for reason in reasons)


def test_invented_skill_is_unsafe() -> None:
    status, reasons = check_change(
        "Built REST APIs in Python and used Kubernetes.",
        original="Built REST APIs in Python.",
        structured=_structured(COMPLETE_RESUME),
        source_text=COMPLETE_RESUME,
    )
    assert status == GuardStatus.UNSAFE
    assert any("skill" in reason.lower() for reason in reasons)


def test_invented_seniority_is_unsafe() -> None:
    status, reasons = check_change(
        "Served as a senior engineer on the platform.",
        original="Worked on the platform.",
        structured=_structured(COMPLETE_RESUME),
        source_text=COMPLETE_RESUME,
    )
    assert status == GuardStatus.UNSAFE
    assert any("seniority" in reason.lower() or "title" in reason.lower() for reason in reasons)


def test_invented_degree_is_unsafe() -> None:
    status, reasons = check_change(
        "Holds a Master of Science in Computer Science.",
        original="Studied computer science.",
        structured=_structured(COMPLETE_RESUME),
        source_text=COMPLETE_RESUME,
    )
    assert status == GuardStatus.UNSAFE
    assert any("qualification" in reason.lower() for reason in reasons)


def test_untraceable_rewrite_needs_review() -> None:
    status, reasons = check_change(
        "Facilitated cross-functional synergy alignment initiatives.",
        original="Wrote SQL queries for monthly reporting.",
        structured=_structured(LONG_BULLET_RESUME),
        source_text=LONG_BULLET_RESUME,
    )
    assert status == GuardStatus.NEEDS_REVIEW
    assert reasons
