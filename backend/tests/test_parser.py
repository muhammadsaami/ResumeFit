"""Tests for the deterministic structured resume parser."""

from __future__ import annotations

from app.services.parser import parse_resume

from .synthetic import (
    ALIAS_RESUME,
    COMPLETE_RESUME,
    DUPLICATE_SKILLS_RESUME,
    MISSING_SECTIONS_RESUME,
    REORDERED_RESUME,
)


def test_extracts_name_email_and_phone() -> None:
    parsed = parse_resume(COMPLETE_RESUME)
    assert parsed.basics.name == "Jordan Rivera"
    assert parsed.basics.email == "jordan.rivera@example.com"
    assert parsed.basics.phone == "+1 555 123 4567"
    assert parsed.basics.city == "Seattle, WA"
    assert parsed.basics.linkedin and "linkedin.com/in/jordanrivera" in parsed.basics.linkedin
    assert parsed.basics.github and "github.com/jordanrivera" in parsed.basics.github


def test_extracts_education_entry() -> None:
    parsed = parse_resume(COMPLETE_RESUME)
    assert len(parsed.education) == 1
    entry = parsed.education[0]
    assert entry.degree and "Computer Science" in entry.degree
    assert entry.institution == "University of Example"
    assert entry.start_date == "2018"
    assert entry.end_date == "2022"
    assert entry.score == "3.8"


def test_extracts_experience_with_bullets_and_source_lines() -> None:
    parsed = parse_resume(COMPLETE_RESUME)
    assert len(parsed.experience) == 1
    entry = parsed.experience[0]
    assert entry.role == "Software Engineer"
    assert entry.company == "Example Corp"
    assert entry.start_date == "2022"
    assert entry.end_date == "Present"
    assert len(entry.bullets) == 3
    first = entry.bullets[0]
    assert first.source_line == 18
    assert first.text == "Built REST APIs in Python that serve internal tools reliably."


def test_extracts_projects_with_technologies() -> None:
    parsed = parse_resume(COMPLETE_RESUME)
    assert len(parsed.projects) == 1
    project = parsed.projects[0]
    assert project.name == "Portfolio Tracker"
    assert project.technologies == ["React", "Node.js", "PostgreSQL"]
    assert len(project.bullets) == 2


def test_extracts_and_categorizes_skills() -> None:
    parsed = parse_resume(COMPLETE_RESUME)
    assert parsed.skills.all_skills == [
        "Python",
        "JavaScript",
        "SQL",
        "React",
        "Node.js",
        "Docker",
        "Git",
        "PostgreSQL",
    ]
    assert "Python" in parsed.skills.languages
    assert "React" in parsed.skills.frameworks
    assert "Docker" in parsed.skills.tools
    assert parsed.skills.duplicates == []


def test_section_aliases_are_normalized() -> None:
    parsed = parse_resume(ALIAS_RESUME)
    # Work Experience -> experience, Academic Background -> education,
    # Technical Expertise -> skills, Personal Projects -> projects
    assert set(parsed.sections_detected) == {"education", "experience", "skills", "projects"}
    assert parsed.nonstandard_headings == []
    assert parsed.experience and parsed.experience[0].role == "Data Analyst"
    assert parsed.projects and parsed.projects[0].name == "Budget App"
    assert "Python" in parsed.skills.all_skills


def test_missing_sections_are_not_invented() -> None:
    parsed = parse_resume(MISSING_SECTIONS_RESUME)
    assert parsed.basics.name == "Taylor Morgan"
    assert parsed.basics.email == "taylor.morgan@example.com"
    assert parsed.education == []
    assert parsed.experience == []
    assert parsed.projects == []
    assert parsed.skills.all_skills == []
    assert parsed.sections_detected == []
    assert any("section" in warning.lower() for warning in parsed.warnings)


def test_different_section_orders_are_handled() -> None:
    parsed = parse_resume(REORDERED_RESUME)
    assert set(parsed.sections_detected) == {"skills", "projects", "education", "experience"}
    assert parsed.education[0].institution == "Example Institute of Technology"
    assert parsed.experience[0].company == "Example Labs"
    assert "Java" in parsed.skills.all_skills


def test_duplicate_skills_detected() -> None:
    parsed = parse_resume(DUPLICATE_SKILLS_RESUME)
    assert "Python" in parsed.skills.duplicates
    assert "sql" in parsed.skills.duplicates
    # Duplicates are not repeated in the canonical list.
    assert parsed.skills.all_skills == ["Python", "SQL", "Docker"]


def test_source_line_references_are_accurate() -> None:
    parsed = parse_resume(COMPLETE_RESUME)
    lines = COMPLETE_RESUME.splitlines()
    for entry in [*parsed.education, *parsed.experience, *parsed.projects]:
        for ref in entry.source_lines:
            assert ref.line >= 1
            assert lines[ref.line - 1].strip() == ref.text


def test_parsing_is_deterministic() -> None:
    first = parse_resume(COMPLETE_RESUME).model_dump()
    second = parse_resume(COMPLETE_RESUME).model_dump()
    assert first == second


def test_empty_text_parses_without_invention() -> None:
    parsed = parse_resume("")
    assert parsed.basics.name is None
    assert parsed.basics.email is None
    assert parsed.education == []
    assert parsed.experience == []
    assert parsed.skills.all_skills == []
    assert parsed.confidence.overall == 0.0


def test_confidence_metadata_reported() -> None:
    parsed = parse_resume(COMPLETE_RESUME)
    assert 0.0 <= parsed.confidence.overall <= 1.0
    assert parsed.confidence.sections_found == 4
    assert parsed.confidence.sections_expected == 4
    assert parsed.confidence.contact_fields_found >= 5
