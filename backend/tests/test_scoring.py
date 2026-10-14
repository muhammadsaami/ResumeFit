"""Tests for the deterministic ATS-readiness scoring engine."""

from __future__ import annotations

from app.models.analysis import RuleStatus
from app.services.parser import parse_resume
from app.services.scoring import build_issues, score_resume

from .synthetic import (
    COMPLETE_RESUME,
    DUPLICATE_SKILLS_RESUME,
    INCONSISTENT_DATES_RESUME,
    LONG_BULLET_RESUME,
    MISSING_SECTIONS_RESUME,
)


def _score(text: str):
    return score_resume(parse_resume(text), text)


def _rule(score, rule_id: str):
    return next(rule for rule in score.breakdown if rule.rule_id == rule_id)


def test_rule_weights_sum_to_one_hundred() -> None:
    score = _score(COMPLETE_RESUME)
    assert sum(rule.points_max for rule in score.breakdown) == 100
    assert score.max_score == 100


def test_rule_ids_are_unique_and_stable() -> None:
    first = _score(COMPLETE_RESUME)
    second = _score(COMPLETE_RESUME)
    ids_first = [rule.rule_id for rule in first.breakdown]
    ids_second = [rule.rule_id for rule in second.breakdown]
    assert ids_first == ids_second
    assert len(ids_first) == len(set(ids_first))


def test_score_is_within_bounds_for_all_samples() -> None:
    for text in (
        COMPLETE_RESUME,
        MISSING_SECTIONS_RESUME,
        DUPLICATE_SKILLS_RESUME,
        LONG_BULLET_RESUME,
        INCONSISTENT_DATES_RESUME,
    ):
        score = _score(text)
        assert 0 <= score.score <= 100


def test_score_is_stable_for_identical_input() -> None:
    assert _score(COMPLETE_RESUME).score == _score(COMPLETE_RESUME).score
    assert _score(MISSING_SECTIONS_RESUME).model_dump() == _score(
        MISSING_SECTIONS_RESUME
    ).model_dump()


def test_points_are_within_their_maximum() -> None:
    for rule in _score(COMPLETE_RESUME).breakdown:
        assert 0 <= rule.points_earned <= rule.points_max


def test_every_rule_has_an_explanation_and_failures_have_suggestions() -> None:
    for rule in _score(MISSING_SECTIONS_RESUME).breakdown:
        assert rule.explanation.strip()
        if rule.status == RuleStatus.FAILED:
            assert rule.suggestion and rule.suggestion.strip()


def test_complete_resume_scores_higher_than_sparse_resume() -> None:
    complete = _score(COMPLETE_RESUME).score
    sparse = _score(MISSING_SECTIONS_RESUME).score
    assert complete > sparse


def test_contact_and_section_rules_pass_for_complete_resume() -> None:
    score = _score(COMPLETE_RESUME)
    for rule_id in ("contact_email", "contact_phone", "contact_name", "section_education"):
        assert _rule(score, rule_id).status == RuleStatus.PASSED


def test_duplicate_skills_rule_fails() -> None:
    score = _score(DUPLICATE_SKILLS_RESUME)
    rule = _rule(score, "skills_no_duplicates")
    assert rule.status == RuleStatus.FAILED
    assert rule.points_earned == 0


def test_long_and_weak_bullets_are_flagged() -> None:
    score = _score(LONG_BULLET_RESUME)
    length_rule = _rule(score, "bullet_length")
    assert length_rule.status != RuleStatus.PASSED
    assert length_rule.source_lines


def test_first_person_and_filler_wording_is_flagged() -> None:
    score = _score(LONG_BULLET_RESUME)
    rule = _rule(score, "no_first_person")
    assert rule.status != RuleStatus.PASSED
    assert rule.source_lines


def test_inconsistent_date_ranges_fail_the_date_rule() -> None:
    score = _score(INCONSISTENT_DATES_RESUME)
    rule = _rule(score, "date_consistency")
    assert rule.status == RuleStatus.FAILED


def test_detected_issues_match_non_passing_rules() -> None:
    score = _score(LONG_BULLET_RESUME)
    issues = build_issues(score)
    non_passing = [
        rule for rule in score.breakdown if rule.status != RuleStatus.PASSED
    ]
    assert len(issues) == len(non_passing)
    severities = {issue.severity for issue in issues}
    assert severities <= {"error", "warning"}


def test_disclaimer_is_present_and_not_a_real_ats() -> None:
    score = _score(COMPLETE_RESUME)
    assert "not a score from Workday" in score.disclaimer
    assert score.label == "Estimated ATS-readiness score"
