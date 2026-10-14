"""Regression tests for the real-PDF quality defects.

Covers the four reported problems:

1. A real PDF (no blank lines, cid-bullet glyphs) must parse fully - name,
   contact, both degrees, all three projects and certifications.
2. Scoring must not report a section as missing when it is present with
   content, must not award full credit to an empty heading, and must not
   double-penalise an uncertain extraction.
3. Rendered templates must compile and the PDF text must contain the content.
4. The pipeline must be deterministic.
"""

from __future__ import annotations

import io

import pytest
from pypdf import PdfReader

from app.services import latex
from app.services.analyzer import analyze_resume
from app.services.compiler import compile_latex, detect_compiler
from app.services.extraction import _join_hyphenated_wraps, _normalize_text, extract_text
from app.services.latex import _href_target
from app.services.parser import parse_resume
from app.services.scoring import score_resume

from .pdf_realistic import (
    EMBEDDED_DATE_RESUME,
    EMPTY_SECTION_RESUME,
    MUST_HAVE_CONTENT,
    NO_PHONE_RESUME,
    REALISTIC_RESUME,
    UNCERTAINTY_WARNING,
    WRAPPED_BULLET_RESUME,
    build_realistic_pdf,
)

ALL_TEMPLATES = ("classic", "compact", "modern")


def _rule(score, rule_id: str):
    return next(rule for rule in score.breakdown if rule.rule_id == rule_id)


def _norm_pdf_text(text: str) -> str:
    replacements = {
        "\ufb01": "fi",
        "\ufb02": "fl",
        "\ufb03": "ffi",
        "\ufb04": "ffl",
    }
    for ligature, plain in replacements.items():
        text = text.replace(ligature, plain)
    return " ".join(text.split()).lower()


class TestRealisticTextParsing:
    def test_single_line_header_recovers_all_contact_fields(self) -> None:
        structured = parse_resume(REALISTIC_RESUME)
        basics = structured.basics
        assert basics.name == "Jordan Rivera"
        assert basics.email == "jordan.rivera@example.com"
        assert basics.phone and "7000 123456" in basics.phone
        assert basics.city == "London, UK"
        assert basics.linkedin and "jordanrivera" in basics.linkedin
        assert basics.github and "jrivera" in basics.github

    def test_both_degrees_are_parsed_without_blank_lines(self) -> None:
        structured = parse_resume(REALISTIC_RESUME)
        institutions = {entry.institution for entry in structured.education}
        assert "University College London" in institutions
        assert "University of Oxford" in institutions
        assert len(structured.education) == 2

    def test_both_experience_entries_and_their_bullets(self) -> None:
        structured = parse_resume(REALISTIC_RESUME)
        assert len(structured.experience) == 2
        first = structured.experience[0]
        assert first.company == "Riverstone Labs"
        assert first.role == "Senior Software Engineer"
        assert len(first.bullets) == 3
        second = structured.experience[1]
        assert second.company == "Northwind Systems Ltd"
        assert len(second.bullets) == 2

    def test_all_three_projects_parsed_with_technologies(self) -> None:
        structured = parse_resume(REALISTIC_RESUME)
        by_name = {project.name: project for project in structured.projects}
        assert set(by_name) == {"SupportPilot", "trustlens", "DocuMind"}
        assert by_name["SupportPilot"].technologies == ["FastAPI", "Docker", "PostgreSQL"]
        assert by_name["trustlens"].technologies == ["Python", "React", "GraphQL"]
        assert by_name["DocuMind"].technologies == ["PyTorch", "FastAPI", "Selenium"]
        assert len(by_name["SupportPilot"].bullets) == 2

    def test_certifications_are_parsed(self) -> None:
        structured = parse_resume(REALISTIC_RESUME)
        assert "AWS Certified Solutions Architect - Associate" in structured.certifications
        assert "Certified Kubernetes Administrator" in structured.certifications

    def test_skills_are_categorised(self) -> None:
        structured = parse_resume(REALISTIC_RESUME)
        skills = structured.skills
        assert {"Python", "TypeScript", "Java", "SQL"} <= set(skills.languages)
        assert {"FastAPI", "React", "Node.js", "Django"} <= set(skills.frameworks)
        assert {"Docker", "Kubernetes", "PostgreSQL", "AWS", "Git"} <= set(skills.tools)

    def test_wrapped_bullet_merges_into_previous_bullet(self) -> None:
        structured = parse_resume(WRAPPED_BULLET_RESUME)
        bullets = structured.experience[0].bullets
        assert len(bullets) == 2
        assert "currencies" in bullets[0].text

    def test_parsing_is_deterministic(self) -> None:
        assert parse_resume(REALISTIC_RESUME) == parse_resume(REALISTIC_RESUME)


class TestEmbeddedDateLayout:
    """Regression tests for the real-PDF extraction defects.

    Covers: a role kept intact across an em-dash (not split into a bogus
    company), the company recovered from a dedicated header line, all projects
    and their technologies, education dates kept with the right entry, wrapped
    certifications joined, wrapped bullet fragments not treated as headings, and
    an uppercase continuation merged into its bullet.
    """

    def test_role_is_kept_intact_and_company_is_recovered(self) -> None:
        structured = parse_resume(EMBEDDED_DATE_RESUME)
        assert len(structured.experience) == 2
        first = structured.experience[0]
        assert first.role == "Senior Developer \u2014 AI Platforms"
        assert first.company == "Riverstone Labs"
        assert first.start_date == "Jul 2021"
        assert first.end_date == "May 2023"
        second = structured.experience[1]
        assert second.role == "Backend Developer (Contract)"
        assert second.company == "Northwind Systems"
        assert second.start_date == "Mar 2020"
        assert second.end_date == "Jul 2021"

    def test_uppercase_bullet_continuation_is_merged(self) -> None:
        structured = parse_resume(EMBEDDED_DATE_RESUME)
        bullets = structured.experience[0].bullets
        assert len(bullets) == 2
        assert "LangChain pipelines" in bullets[1].text
        assert bullets[1].source_line == 18
        assert bullets[1].source_end_line == 19

    def test_all_projects_and_bare_technology_lists(self) -> None:
        structured = parse_resume(EMBEDDED_DATE_RESUME)
        by_name = {project.name: project for project in structured.projects}
        assert set(by_name) == {"Full-Stack Commerce Platform", "Gestures Controller"}
        assert by_name["Full-Stack Commerce Platform"].technologies == [
            "React.js", "Node.js", "Express.js", "MongoDB", "Tailwind CSS"
        ]
        assert by_name["Gestures Controller"].technologies == [
            "Python", "OpenCV", "MediaPipe", "Computer Vision"
        ]
        assert len(by_name["Full-Stack Commerce Platform"].bullets) == 2
        assert "UI." in by_name["Full-Stack Commerce Platform"].bullets[1].text

    def test_education_dates_stay_with_the_right_entry(self) -> None:
        structured = parse_resume(EMBEDDED_DATE_RESUME)
        assert len(structured.education) == 2
        first, second = structured.education
        assert first.institution == "Northfield University \u2014 Faculty of Engineering"
        assert first.degree == (
            "M.Sc. (AI) \u2014 Master of Computer Science, Artificial Intelligence"
        )
        assert first.start_date == "Aug 2021"
        assert first.end_date == "Aug 2023"
        assert first.score == "8.5"
        assert second.institution == "Westbridge University"
        assert second.degree == "B.Sc. (Hons) Mathematics"
        assert second.start_date == "Sep 2018"
        assert second.end_date == "Feb 2021"
        assert second.score == "8.9"

    def test_wrapped_certification_is_joined(self) -> None:
        structured = parse_resume(EMBEDDED_DATE_RESUME)
        assert len(structured.certifications) == 1
        assert "development and deployment." in structured.certifications[0]

    def test_bullet_fragment_is_not_a_nonstandard_heading(self) -> None:
        structured = parse_resume(EMBEDDED_DATE_RESUME)
        assert structured.nonstandard_headings == []
        assert not any("Non-standard" in warning for warning in structured.warnings)



class TestScoringFairness:
    def test_present_sections_are_not_reported_missing(self) -> None:
        structured = parse_resume(REALISTIC_RESUME)
        score = score_resume(structured, REALISTIC_RESUME)
        for section in ("education", "experience", "skills", "projects"):
            rule = _rule(score, f"section_{section}")
            assert rule.status == "passed", f"{section} wrongly flagged: {rule.explanation}"

    def test_empty_heading_does_not_earn_full_section_credit(self) -> None:
        structured = parse_resume(EMPTY_SECTION_RESUME)
        score = score_resume(structured, EMPTY_SECTION_RESUME)
        projects = _rule(score, "section_projects")
        assert projects.status == "warning"
        assert projects.points_earned < projects.points_max
        assert _rule(score, "section_skills").status == "passed"

    def test_uncertain_extraction_downgrades_missing_phone_to_warning(self) -> None:
        structured = parse_resume(NO_PHONE_RESUME)
        structured.warnings.append(UNCERTAINTY_WARNING)
        score = score_resume(structured, NO_PHONE_RESUME)
        assert _rule(score, "contact_phone").status == "warning"

    def test_missing_phone_without_uncertainty_still_fails(self) -> None:
        structured = parse_resume(NO_PHONE_RESUME)
        score = score_resume(structured, NO_PHONE_RESUME)
        assert _rule(score, "contact_phone").status == "failed"

    def test_analyzer_threads_extraction_warnings_into_scoring(self) -> None:
        analysis = analyze_resume(
            "resume-1", NO_PHONE_RESUME, metadata_warnings=[UNCERTAINTY_WARNING]
        )
        rule = _rule(analysis.ats_score, "contact_phone")
        assert rule.status == "warning"
        assert UNCERTAINTY_WARNING in analysis.structured_resume.warnings

    def test_scoring_is_deterministic(self) -> None:
        structured = parse_resume(REALISTIC_RESUME)
        first = score_resume(structured, REALISTIC_RESUME)
        second = score_resume(structured, REALISTIC_RESUME)
        assert first.score == second.score


class TestPdfRoundTrip:
    def test_realistic_pdf_extracts_clean_text(self) -> None:
        result = extract_text("resume.pdf", build_realistic_pdf())
        assert "(cid:" not in result.text
        assert result.page_count == 1

    def test_realistic_pdf_parses_like_the_source_text(self) -> None:
        extracted = extract_text("resume.pdf", build_realistic_pdf()).text
        structured = parse_resume(extracted)
        assert structured.basics.name == "Jordan Rivera"
        assert structured.basics.email == "jordan.rivera@example.com"
        assert len(structured.education) == 2
        assert len(structured.experience) == 2
        assert {p.name for p in structured.projects} == {"SupportPilot", "trustlens", "DocuMind"}
        assert len(structured.certifications) == 2
        assert len(structured.experience[0].bullets) == 3


class TestTextNormalisation:
    def test_ligatures_are_expanded(self) -> None:
        assert _normalize_text("classi\ufb01cation") == "classification"
        assert _normalize_text("Certi\ufb01ed") == "Certified"
        assert _normalize_text("re\ufb02ect") == "reflect"

    def test_line_wrap_hyphenation_is_joined(self) -> None:
        assert _normalize_text(_join_hyphenated_wraps("scalabil-\nity")) == "scalability"

    def test_camel_case_wrap_is_joined(self) -> None:
        assert _normalize_text(_join_hyphenated_wraps("Post-\ngreSQL")) == "PostgreSQL"

    def test_midline_compound_is_preserved(self) -> None:
        assert _join_hyphenated_wraps("long-term") == "long-term"


class TestHrefTargets:
    def test_email_gets_mailto_scheme(self) -> None:
        assert _href_target("jordan.rivera@example.com") == "mailto:jordan.rivera@example.com"

    def test_bare_domains_get_https_scheme(self) -> None:
        assert _href_target("linkedin.com/in/jordanrivera") == (
            "https://linkedin.com/in/jordanrivera"
        )
        assert _href_target("github.com/jrivera") == "https://github.com/jrivera"

    def test_existing_scheme_is_kept(self) -> None:
        assert _href_target("https://example.com") == "https://example.com"

    def test_phone_is_not_a_link(self) -> None:
        assert _href_target("+44 7000 123456") == ""


class TestEducationDedupe:
    def test_shared_line_degree_does_not_repeat_institution(self) -> None:
        structured = parse_resume(REALISTIC_RESUME)
        assert structured.education
        for entry in structured.education:
            if entry.degree and entry.institution:
                assert entry.institution.lower() not in entry.degree.lower(), entry.model_dump()


class TestTemplateSource:
    @pytest.mark.parametrize("template_id", ALL_TEMPLATES)
    def test_certifications_and_links_in_tex_source(self, template_id: str) -> None:
        tex = latex.render_template(template_id, parse_resume(REALISTIC_RESUME))
        assert "Certifications" in tex
        assert "AWS Certified Solutions Architect" in tex
        # Links must carry a scheme so hyperref produces a working annotation.
        assert "\\href{mailto:jordan.rivera@example.com}" in tex
        assert "\\href{https://github.com/jrivera}" in tex
        assert "\\usepackage[hyphens]{url}" in tex

    @pytest.mark.parametrize("template_id", ALL_TEMPLATES)
    def test_institution_not_duplicated_in_tex(self, template_id: str) -> None:
        tex = latex.render_template(template_id, parse_resume(REALISTIC_RESUME))
        assert "University College London | University College London" not in tex
        assert "University of Oxford | University of Oxford" not in tex

    @pytest.mark.parametrize("template_id", ALL_TEMPLATES)
    def test_hyphenation_is_disabled(self, template_id: str) -> None:
        tex = latex.render_template(template_id, parse_resume(REALISTIC_RESUME))
        assert "\\hyphenpenalty=10000" in tex


@pytest.mark.skipif(detect_compiler() is None, reason="no LaTeX compiler installed")
class TestCompiledContent:
    @pytest.mark.parametrize("template_id", ALL_TEMPLATES)
    def test_compiled_pdf_contains_all_content(self, template_id: str) -> None:
        tex = latex.render_template(template_id, parse_resume(REALISTIC_RESUME))
        result = compile_latex(tex, detect_compiler())
        assert result.status == "success", result.log
        assert result.page_count == 1
        assert result.pdf is not None
        reader = PdfReader(io.BytesIO(result.pdf))
        pdf_text = _norm_pdf_text("\n".join(page.extract_text() or "" for page in reader.pages))
        missing = [item for item in MUST_HAVE_CONTENT if _norm_pdf_text(item) not in pdf_text]
        assert not missing, f"{template_id} PDF missing content: {missing}"
