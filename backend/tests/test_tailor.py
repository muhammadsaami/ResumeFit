"""Tests for the tailor service."""
from tests.test_quality_regression import *
from tests.synthetic import *


def test_tailor_analysis_basic() -> None:
    """Basic tailor analysis should work."""
    structured = parse_resume(COMPLETE_RESUME)
    jd = "We are hiring a backend engineer. Required: Python and PostgreSQL. Nice to have: Docker."
    analysis = analyze_job_description(structured, jd, COMPLETE_RESUME)
    assert analysis.match_percentage is not None
    assert isinstance(analysis.explanations, list)


def test_matched_skills_listed() -> None:
    """Matched skills should be explicitly listed in analysis."""
    structured = parse_resume(COMPLETE_RESUME)
    jd = "We are hiring a backend engineer. Required: Python and PostgreSQL."
    analysis = analyze_job_description(structured, jd, COMPLETE_RESUME)
    assert len(analysis.matched_skills) > 0


def test_missing_required_skills_listed() -> None:
    """Missing required skills should be explicitly listed in explanations."""
    structured = parse_resume(COMPLETE_RESUME)
    jd = (
        "We are hiring a backend engineer. Required: Python and PostgreSQL and "
        "Kubernetes. Nice to have: Terraform."
    )
    analysis = analyze_job_description(structured, jd, COMPLETE_RESUME)
    # The explanations should reference the required/preferred status of missing skills;
    # check that at least one explanation mentions required skills not in the resume.
    has_required_ref = any(
        "required" in exp.lower() and ("not in resume" in exp.lower() or "missing" in exp.lower())
        for exp in analysis.explanations
    )
    assert has_required_ref, "Explanations should mention required skills not in resume"


def test_match_percentage_weighting() -> None:
    """With requirement markers, the match percentage should reflect weighting."""
    analysis_with = analyze_job_description(
        parse_resume(COMPLETE_RESUME),
        "Required: Python and PostgreSQL. Nice to have: Terraform.",
        COMPLETE_RESUME,
    )
    analysis_without = analyze_job_description(
        parse_resume(COMPLETE_RESUME),
        "Python and PostgreSQL and Terraform.",
        COMPLETE_RESUME,
    )
    # With requirement markers, the match percentage should reflect weighting
    assert analysis_with.match_percentage != analysis_without.match_percentage