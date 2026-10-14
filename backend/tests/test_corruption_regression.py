"""Failing-first regression tests for the reported corruption classes.

Covers three confirmed defects in the existing pipeline:

1. A word hyphenated across a PDF line wrap ("scalabil-" + "ity") was left with
   the hyphen and the newline, corrupting the word.
2. Accepting an auto-fix for a bullet that wrapped onto a second physical line
   replaced only the first line, leaving the continuation behind as a duplicate
   sentence.
3. Accepting a skills re-grouping for skills spread across several lines
   replaced only the first line, leaving the original labelled lines behind -
   duplicating every skill.

All fixtures are privacy-safe placeholders.
"""

from __future__ import annotations

from app.models.resume import ParsingMetadata, SourceType
from app.models.tailoring import ChangeAction, ChangeCategory, ResumeChange
from app.services.autofix import plan_changes
from app.services.extraction import extract_text
from app.services.parser import parse_resume
from app.services.review import accept_change
from app.services.store import get_store
from app.services.tailoring import analyze_job_description, plan_tailor_changes

from .pdf_realistic import (
    MULTILINE_SKILLS_RESUME,
    WRAPPED_BULLET_RESUME,
    build_pdf_from_lines,
)


def _metadata(text: str) -> ParsingMetadata:
    return ParsingMetadata(
        source_type=SourceType.PASTE,
        size_bytes=len(text),
        parser="manual",
        character_count=len(text),
        word_count=len(text.split()),
        line_count=len(text.splitlines()),
    )


def _stored(text: str):
    return get_store().create(text=text, source_type=SourceType.PASTE, metadata=_metadata(text))


def _plan(resume) -> list[ResumeChange]:
    return plan_changes(parse_resume(resume.effective_text), resume.effective_text)


def _first_replace(resume, predicate) -> ResumeChange:
    change = next(
        c for c in _plan(resume) if c.action == ChangeAction.REPLACE and predicate(c)
    )
    resume.changes[change.id] = change
    return change


class TestPdfHyphenation:
    def test_line_wrap_hyphenation_is_joined(self) -> None:
        pdf = build_pdf_from_lines(
            [
                "Jordan Rivera",
                "PROFESSIONAL EXPERIENCE",
                "Senior Engineer, Acme Ltd | 2020 - Present",
                "- Improved platform scalabil-",
                "ity and reliability across teams.",
            ]
        )
        text = extract_text("resume.pdf", pdf).text
        assert "scalability" in text
        assert "scalabil-" not in text

    def test_genuine_midline_hyphen_is_preserved(self) -> None:
        pdf = build_pdf_from_lines(
            [
                "Jordan Rivera",
                "PROFESSIONAL SUMMARY",
                "Built state-of-the-art tooling for the engineering team.",
            ]
        )
        text = extract_text("resume.pdf", pdf).text
        assert "state-of-the-art" in text


class TestChangeApplicationIntegrity:
    def test_accepting_wrapped_bullet_change_does_not_duplicate(self) -> None:
        resume = _stored(WRAPPED_BULLET_RESUME)
        before = parse_resume(resume.effective_text)
        assert len(before.experience[0].bullets) == 2

        change = _first_replace(resume, lambda c: c.source_line == 5)
        accept_change(resume, change.id)

        effective = resume.effective_text
        assert effective.count("currencies") == 1
        assert effective.count("across multiple regions") == 1
        after = parse_resume(effective)
        assert len(after.experience[0].bullets) == 2

    def test_accepting_skills_change_leaves_no_duplicate_skills(self) -> None:
        resume = _stored(MULTILINE_SKILLS_RESUME)
        change = _first_replace(
            resume, lambda c: c.category == ChangeCategory.SKILL_GROUPING
        )
        accept_change(resume, change.id)

        effective = resume.effective_text
        assert "Frameworks:" not in effective
        assert "Tools:" not in effective
        assert effective.count("Docker") == 1
        assert effective.count("Django") == 1
        skills = parse_resume(effective).skills
        assert skills.duplicates == []
        assert set(skills.all_skills) == {"Python", "SQL", "Docker", "Django", "React"}

    def test_replace_change_original_matches_its_source_range(self) -> None:
        for text in (WRAPPED_BULLET_RESUME, MULTILINE_SKILLS_RESUME):
            resume = _stored(text)
            lines = resume.effective_text.splitlines()
            for change in _plan(resume):
                if change.action != ChangeAction.REPLACE or change.source_line is None:
                    continue
                end = change.source_end_line or change.source_line
                physical = "\n".join(lines[change.source_line - 1 : end])
                assert physical.strip() == change.original_text.strip(), (
                    f"{change.category} original does not match its source range"
                )

    def test_tailor_skill_ordering_replaces_whole_block(self) -> None:
        resume = _stored(MULTILINE_SKILLS_RESUME)
        structured = parse_resume(resume.effective_text)
        job = "Backend role using Django and React and Python at scale."
        analysis = analyze_job_description(structured, job, resume.effective_text)
        tailor_changes = plan_tailor_changes(structured, analysis, resume.effective_text)
        order = [
            c for c in tailor_changes if c.category == ChangeCategory.SKILL_ORDERING
        ]
        assert order, "expected a skill-ordering change"
        for change in tailor_changes:
            resume.changes[change.id] = change
        accept_change(resume, order[0].id)

        effective = resume.effective_text
        assert effective.count("Docker") == 1
        assert effective.count("Django") == 1
        assert "Frameworks:" not in effective
        assert parse_resume(effective).skills.duplicates == []
