"""Deterministic, explainable ATS-readiness scoring engine.

The engine runs a fixed set of weighted rules (max points sum to exactly 100)
against the structured resume and the original text. Every rule returns a stable
id, status, points, explanation, a suggested correction and source references.

Rule weights (total 100):

    Contact       contact_email 10, contact_phone 7, contact_name 5, contact_presence 3
    Sections      section_education 8, section_experience 9, section_skills 7,
                  section_projects 6
    Headings      standard_headings 5
    Content       experience_evidence 7, bullet_presence 5, bullet_length 4,
                  skills_organized 5, skills_no_duplicates 3, date_consistency 2
    Language      no_first_person 5, characters_clean 4, content_length 5

Status semantics: ``passed`` earns full points, ``warning`` earns half points,
``failed`` earns none. The total is a deterministic function of the input text -
no randomness is involved.

A ``warning`` is also used for two fairness cases: a section heading that is
present but yielded no parseable content (no points for empty headings), and a
conclusion of "missing" when the extraction layer reported the text looks
incomplete (so a poor PDF does not double-penalise already-broken uploads).
"""

from __future__ import annotations

import re
from datetime import UTC, datetime

from ..models.analysis import (
    AtsScore,
    DetectedIssue,
    RuleResult,
    RuleStatus,
    ScoreSummary,
)
from ..models.structured import SourceLine, StructuredResume

DISCLAIMER = (
    "This is an estimated ATS-readiness indicator produced by ResumeFit's local, "
    "rule-based checks. It is not a score from Workday, Greenhouse, Lever or any other "
    "commercial applicant tracking system."
)
LABEL = "Estimated ATS-readiness score"

_FACTOR = {RuleStatus.PASSED: 1.0, RuleStatus.WARNING: 0.5, RuleStatus.FAILED: 0.0}

_FIRST_PERSON_RE = re.compile(r"\b(?:I|I'm|I've|my|me|we|our)\b")
_FILLER_PHRASES = (
    "responsible for",
    "hard worker",
    "team player",
    "go-getter",
    "go getter",
    "think outside the box",
    "detail oriented",
    "detail-oriented",
    "self-motivated",
    "self motivated",
    "results-driven",
    "results driven",
    "synergy",
    "hard-working",
)
_SCOREABLE_SECTIONS = ("education", "experience", "skills", "projects")

# Warnings that indicate a parser/extraction miss rather than genuinely missing
# content. Printed by the extraction layer when the recovered text looks short or
# malformed. Rules that conclude "missing" are downgraded so a bad parse does not
# count as a double penalty on top of a bad upload.
_EXTRACTION_UNCERTAIN_MARKERS = (
    "looks incomplete",
    "missing the spaces",
    "hard to read programmatically",
)


def _extraction_uncertain(structured: StructuredResume) -> bool:
    blob = " ".join(structured.warnings).lower()
    return any(marker in blob for marker in _EXTRACTION_UNCERTAIN_MARKERS)


def _section_content(structured: StructuredResume, section: str) -> bool:
    """Whether a recognised section actually yielded parseable content."""
    if section == "education":
        return bool(structured.education)
    if section == "experience":
        return bool(structured.experience)
    if section == "projects":
        return bool(structured.projects)
    if section == "skills":
        return bool(structured.skills.all_skills)
    return False


def _line_refs(lines: list[tuple[int, str]], pattern: re.Pattern[str]) -> list[SourceLine]:
    return [
        SourceLine(line=number, text=raw.strip())
        for number, raw in lines
        if pattern.search(raw)
    ]


def _result(
    rule_id: str,
    name: str,
    category: str,
    status: RuleStatus,
    points_max: float,
    explanation: str,
    suggestion: str | None = None,
    source_lines: list[SourceLine] | None = None,
) -> RuleResult:
    return RuleResult(
        rule_id=rule_id,
        name=name,
        category=category,
        status=status,
        points_earned=round(points_max * _FACTOR[status], 1),
        points_max=float(points_max),
        explanation=explanation,
        suggestion=suggestion,
        source_lines=source_lines or [],
    )


def _year(value: str | None) -> int | None:
    if not value:
        return None
    match = re.search(r"(?:19|20)\d{2}", value)
    return int(match.group(0)) if match else None


def _rule_contact_email(structured: StructuredResume, lines: list[tuple[int, str]]) -> RuleResult:
    email = structured.basics.email
    if email:
        return _result(
            "contact_email",
            "Professional email present",
            "Contact",
            RuleStatus.PASSED,
            10,
            f"A valid email address was found: {email}.",
            source_lines=_line_refs(lines, re.compile(re.escape(email))),
        )
    if any("@" in raw for _, raw in lines):
        return _result(
            "contact_email",
            "Professional email present",
            "Contact",
            RuleStatus.WARNING,
            10,
            "An '@' symbol was found, but no valid email address could be parsed.",
            "Check the email address for typos.",
            _line_refs(lines, re.compile(r"@")),
        )
    if _extraction_uncertain(structured):
        return _result(
            "contact_email",
            "Professional email present",
            "Contact",
            RuleStatus.WARNING,
            10,
            "No email address was detected and the extracted text looks incomplete, "
            "so this is likely an extraction issue rather than a missing email.",
            "Re-upload a text-based PDF or paste the resume text to preserve the address.",
        )
    return _result(
        "contact_email",
        "Professional email present",
        "Contact",
        RuleStatus.FAILED,
        10,
        "No email address was detected in the resume.",
        "Add a professional email address, e.g. name@example.com.",
    )


def _rule_contact_phone(structured: StructuredResume, lines: list[tuple[int, str]]) -> RuleResult:
    phone = structured.basics.phone
    if phone:
        digits = re.sub(r"\D", "", phone)
        if 8 <= len(digits) <= 15:
            return _result(
                "contact_phone",
                "Phone number present and plausible",
                "Contact",
                RuleStatus.PASSED,
                7,
                f"A phone number with {len(digits)} digits was detected.",
                source_lines=_line_refs(lines, re.compile(re.escape(phone))),
            )
        return _result(
            "contact_phone",
            "Phone number present and plausible",
            "Contact",
            RuleStatus.WARNING,
            7,
            f"A phone-like value was found ({phone}) but its digit count is unusual.",
            "Use a standard format such as +1 555 123 4567.",
            _line_refs(lines, re.compile(re.escape(phone))),
        )
    if _extraction_uncertain(structured):
        return _result(
            "contact_phone",
            "Phone number present and plausible",
            "Contact",
            RuleStatus.WARNING,
            7,
            "No phone number was detected and the extracted text looks incomplete, "
            "so this is likely an extraction issue rather than a missing phone.",
            "Re-upload a text-based PDF or paste the resume text to preserve the phone number.",
        )
    return _result(
        "contact_phone",
        "Phone number present and plausible",
        "Contact",
        RuleStatus.FAILED,
        7,
        "No phone number was detected in the resume.",
        "Add a contact phone number.",
    )


def _rule_contact_name(structured: StructuredResume) -> RuleResult:
    name = structured.basics.name
    if name:
        return _result(
            "contact_name",
            "Candidate name detected",
            "Contact",
            RuleStatus.PASSED,
            5,
            f"A name was detected at the top of the resume: {name}.",
        )
    if _extraction_uncertain(structured):
        return _result(
            "contact_name",
            "Candidate name detected",
            "Contact",
            RuleStatus.WARNING,
            5,
            "The candidate name could not be confidently detected and the extracted "
            "text looks incomplete, so this may be an extraction issue.",
            "Re-upload a text-based PDF or paste the resume text so the name is preserved.",
        )
    return _result(
        "contact_name",
        "Candidate name detected",
        "Contact",
        RuleStatus.FAILED,
        5,
        "The candidate name could not be confidently detected.",
        "Put your full name on the first line of the resume.",
    )


def _rule_contact_presence(structured: StructuredResume) -> RuleResult:
    present = [
        label
        for label, value in (
            ("location", structured.basics.city),
            ("LinkedIn", structured.basics.linkedin),
            ("GitHub", structured.basics.github),
        )
        if value
    ]
    if present:
        return _result(
            "contact_presence",
            "Additional contact or profile details",
            "Contact",
            RuleStatus.PASSED,
            3,
            "Found additional contact details: " + ", ".join(present) + ".",
        )
    return _result(
        "contact_presence",
        "Additional contact or profile details",
        "Contact",
        RuleStatus.FAILED,
        3,
        "No location, LinkedIn or GitHub details were detected.",
        "Add your city and a LinkedIn or GitHub profile.",
    )


def _rule_section(
    section: str, name: str, weight: float, structured: StructuredResume
) -> RuleResult:
    if section in structured.sections_detected and _section_content(structured, section):
        return _result(
            f"section_{section}",
            name,
            "Sections",
            RuleStatus.PASSED,
            weight,
            f"A '{section.title()}' section heading was detected.",
        )
    if section in structured.sections_detected:
        return _result(
            f"section_{section}",
            name,
            "Sections",
            RuleStatus.WARNING,
            weight,
            f"A '{section.title()}' heading was found but no content could be extracted "
            "from it, so it earns no full credit.",
            f"Check that the '{section.title()}' section contains parseable detail.",
        )
    if _extraction_uncertain(structured):
        return _result(
            f"section_{section}",
            name,
            "Sections",
            RuleStatus.WARNING,
            weight,
            f"The '{section.title()}' section could not be confirmed because text "
            "extraction looks incomplete.",
            "Re-upload a text-based PDF or paste the resume text so sections are preserved.",
        )
    return _result(
        f"section_{section}",
        name,
        "Sections",
        RuleStatus.FAILED,
        weight,
        f"No '{section.title()}' section heading was detected.",
        f"Add a clearly labelled '{section.title()}' section.",
    )


def _rule_standard_headings(structured: StructuredResume) -> RuleResult:
    if not structured.sections_detected:
        return _result(
            "standard_headings",
            "Standard section headings",
            "Headings",
            RuleStatus.FAILED,
            5,
            "No recognised section headings were detected.",
            "Use standard headings such as Education, Experience, Skills and Projects.",
        )
    if structured.nonstandard_headings:
        return _result(
            "standard_headings",
            "Standard section headings",
            "Headings",
            RuleStatus.WARNING,
            5,
            "Some non-standard headings were found: "
            + ", ".join(structured.nonstandard_headings)
            + ".",
            "Rename non-standard headings to standard equivalents.",
        )
    return _result(
        "standard_headings",
        "Standard section headings",
        "Headings",
        RuleStatus.PASSED,
        5,
        "All detected section headings use standard, ATS-friendly names.",
    )


def _rule_experience_evidence(structured: StructuredResume) -> RuleResult:
    exp_entries = len(structured.experience)
    proj_entries = len(structured.projects)
    if exp_entries or proj_entries:
        return _result(
            "experience_evidence",
            "Experience or project evidence",
            "Content",
            RuleStatus.PASSED,
            7,
            f"Found {exp_entries} experience entr(ies) and {proj_entries} project(s).",
        )
    if "experience" in structured.sections_detected or "projects" in structured.sections_detected:
        return _result(
            "experience_evidence",
            "Experience or project evidence",
            "Content",
            RuleStatus.WARNING,
            7,
            "An Experience or Projects section exists but no entries could be extracted.",
            "List each role or project with a title and supporting detail.",
        )
    return _result(
        "experience_evidence",
        "Experience or project evidence",
        "Content",
        RuleStatus.FAILED,
        7,
        "No experience or project evidence was found.",
        "Add an Experience or Projects section even if you are a fresher.",
    )


def _all_bullets(structured: StructuredResume) -> list[tuple[str, int | None]]:
    bullets: list[tuple[str, int | None]] = []
    for entry in structured.experience:
        bullets.extend((bullet.text, bullet.source_line) for bullet in entry.bullets)
    for project in structured.projects:
        bullets.extend((bullet.text, bullet.source_line) for bullet in project.bullets)
    return bullets


def _rule_bullet_presence(structured: StructuredResume) -> RuleResult:
    count = len(_all_bullets(structured))
    if count >= 2:
        return _result(
            "bullet_presence",
            "Bullet points used",
            "Content",
            RuleStatus.PASSED,
            5,
            f"Found {count} bullet points across experience and projects.",
        )
    if count == 1:
        return _result(
            "bullet_presence",
            "Bullet points used",
            "Content",
            RuleStatus.WARNING,
            5,
            "Only one bullet point was found; ATS systems read bulleted achievements well.",
            "Convert achievements into concise bullet points.",
        )
    return _result(
        "bullet_presence",
        "Bullet points used",
        "Content",
        RuleStatus.FAILED,
        5,
        "No bullet points were found under experience or projects.",
        "Describe each role or project with 2-4 bullet points.",
    )


def _rule_bullet_length(structured: StructuredResume) -> RuleResult:
    bullets = _all_bullets(structured)
    if not bullets:
        return _result(
            "bullet_length",
            "Bullet length is reasonable",
            "Content",
            RuleStatus.FAILED,
            4,
            "There are no bullet points to evaluate.",
            "Add concise bullet points.",
        )
    longest_text, longest_line = max(bullets, key=lambda item: len(item[0]))
    length = len(longest_text)
    source = (
        [SourceLine(line=longest_line, text=longest_text)] if longest_line else []
    )
    if length > 320:
        return _result(
            "bullet_length",
            "Bullet length is reasonable",
            "Content",
            RuleStatus.FAILED,
            4,
            f"The longest bullet is {length} characters, which is too long for ATS parsing.",
            "Split long bullets into shorter, focused statements (aim under 220 characters).",
            source,
        )
    if length > 220:
        return _result(
            "bullet_length",
            "Bullet length is reasonable",
            "Content",
            RuleStatus.WARNING,
            4,
            f"The longest bullet is {length} characters and may be trimmed.",
            "Keep bullets under about 220 characters.",
            source,
        )
    return _result(
        "bullet_length",
        "Bullet length is reasonable",
        "Content",
        RuleStatus.PASSED,
        4,
        f"The longest bullet is {length} characters, which is within a readable range.",
        source_lines=source,
    )


def _rule_skills_organized(structured: StructuredResume) -> RuleResult:
    count = len(structured.skills.all_skills)
    if count >= 3:
        return _result(
            "skills_organized",
            "Skills are organised",
            "Content",
            RuleStatus.PASSED,
            5,
            f"Found {count} distinct skills under a Skills section.",
        )
    if count >= 1:
        return _result(
            "skills_organized",
            "Skills are organised",
            "Content",
            RuleStatus.WARNING,
            5,
            f"Only {count} skill(s) were found; a stronger skills list is recommended.",
            "List your languages, frameworks and tools as comma-separated skills.",
        )
    if "skills" in structured.sections_detected:
        return _result(
            "skills_organized",
            "Skills are organised",
            "Content",
            RuleStatus.WARNING,
            5,
            "A Skills section was detected but no skills could be extracted from it.",
            "Check that the Skills section lists concrete tools and technologies.",
        )
    if _extraction_uncertain(structured):
        return _result(
            "skills_organized",
            "Skills are organised",
            "Content",
            RuleStatus.WARNING,
            5,
            "No skills could be confirmed and text extraction looks incomplete.",
            "Re-upload a text-based PDF or paste the resume text so skills are preserved.",
        )
    return _result(
        "skills_organized",
        "Skills are organised",
        "Content",
        RuleStatus.FAILED,
        5,
        "No skills were extracted from the resume.",
        "Add a Skills section with your languages, frameworks and tools.",
    )


def _rule_skills_no_duplicates(structured: StructuredResume) -> RuleResult:
    duplicates = structured.skills.duplicates
    if not structured.skills.all_skills:
        return _result(
            "skills_no_duplicates",
            "No duplicate skills",
            "Content",
            RuleStatus.FAILED,
            3,
            "No skills were found, so duplicates could not be checked.",
            "Add a Skills section.",
        )
    if duplicates:
        return _result(
            "skills_no_duplicates",
            "No duplicate skills",
            "Content",
            RuleStatus.FAILED,
            3,
            "Duplicate skills were found: " + ", ".join(sorted(set(duplicates))) + ".",
            "Remove repeated skills to keep the list concise.",
            structured.skills.source_lines,
        )
    return _result(
        "skills_no_duplicates",
        "No duplicate skills",
        "Content",
        RuleStatus.PASSED,
        3,
        "No duplicate skills were found.",
    )


def _rule_date_consistency(structured: StructuredResume) -> RuleResult:
    entries: list[tuple[str, str | None, str | None]] = []
    for item in structured.education:
        entries.append(("education", item.start_date, item.end_date))
    for item in structured.experience:
        entries.append(("experience", item.start_date, item.end_date))

    dated = [entry for entry in entries if entry[1] or entry[2]]
    if not dated:
        return _result(
            "date_consistency",
            "Consistent dates",
            "Content",
            RuleStatus.FAILED,
            2,
            "No dates were detected for education or experience entries.",
            "Add start and end dates (e.g. 2021 - 2024) to each entry.",
        )

    invalid: list[str] = []
    for _, start, end in dated:
        start_year = _year(start)
        end_year = _year(end) if end and end.lower() != "present" else None
        if start_year and end_year and end_year < start_year:
            invalid.append(f"{start} - {end}")
    if invalid:
        return _result(
            "date_consistency",
            "Consistent dates",
            "Content",
            RuleStatus.FAILED,
            2,
            "Inconsistent date ranges were found: " + "; ".join(invalid) + ".",
            "Correct date ranges so the end date is not earlier than the start date.",
        )

    complete = all(bool(start) and bool(end) for _, start, end in dated)
    if complete:
        return _result(
            "date_consistency",
            "Consistent dates",
            "Content",
            RuleStatus.PASSED,
            2,
            "All dated entries have a consistent start and end date.",
        )
    return _result(
        "date_consistency",
        "Consistent dates",
        "Content",
        RuleStatus.WARNING,
        2,
        "Some entries are missing a start or end date.",
        "Provide complete date ranges for every entry.",
    )


def _rule_no_first_person(lines: list[tuple[int, str]]) -> RuleResult:
    pronoun_pattern = _FIRST_PERSON_RE
    filler_pattern = re.compile("|".join(re.escape(p) for p in _FILLER_PHRASES), re.I)
    hits: list[SourceLine] = []
    for number, raw in lines:
        if pronoun_pattern.search(raw) or filler_pattern.search(raw):
            hits.append(SourceLine(line=number, text=raw.strip()))
    if not hits:
        return _result(
            "no_first_person",
            "No first-person or filler wording",
            "Language",
            RuleStatus.PASSED,
            5,
            "No first-person pronouns or common filler phrases were detected.",
        )
    if len(hits) <= 2:
        return _result(
            "no_first_person",
            "No first-person or filler wording",
            "Language",
            RuleStatus.WARNING,
            5,
            f"{len(hits)} line(s) use first-person pronouns or filler phrases.",
            "Prefer third-person, action-led phrasing (e.g. 'Built' instead of 'I built').",
            hits,
        )
    return _result(
        "no_first_person",
        "No first-person or filler wording",
        "Language",
        RuleStatus.FAILED,
        5,
        f"{len(hits)} line(s) use first-person pronouns or filler phrases.",
        "Rewrite using third-person, action-led phrasing and drop filler phrases.",
        hits,
    )


def _is_unusual_char(char: str) -> bool:
    code = ord(char)
    if char in "\t\n\r":
        return False
    if code < 32:
        return True
    if char == "\ufffd":
        return True
    if 0xE000 <= code <= 0xF8FF:
        return True
    return False


def _rule_characters_clean(lines: list[tuple[int, str]]) -> RuleResult:
    offenders: list[SourceLine] = []
    total = 0
    for number, raw in lines:
        count = sum(1 for char in raw if _is_unusual_char(char))
        if count:
            total += count
            offenders.append(SourceLine(line=number, text=raw.strip()))
    if total == 0:
        return _result(
            "characters_clean",
            "No unsupported characters",
            "Language",
            RuleStatus.PASSED,
            4,
            "No unsupported or unusual characters were detected.",
        )
    if total <= 3:
        return _result(
            "characters_clean",
            "No unsupported characters",
            "Language",
            RuleStatus.WARNING,
            4,
            f"{total} unusual character(s) were detected, likely from formatting artefacts.",
            "Replace unusual symbols with plain text or standard punctuation.",
            offenders,
        )
    return _result(
        "characters_clean",
        "No unsupported characters",
        "Language",
        RuleStatus.FAILED,
        4,
        f"{total} unusual character(s) were detected and may confuse ATS parsers.",
        "Remove decorative symbols and private-use glyphs from the resume.",
        offenders[:10],
    )


def _rule_content_length(text: str) -> RuleResult:
    words = len(text.split())
    if words >= 120:
        return _result(
            "content_length",
            "Sufficient content",
            "Language",
            RuleStatus.PASSED,
            5,
            f"The resume contains about {words} words.",
        )
    if words >= 60:
        return _result(
            "content_length",
            "Sufficient content",
            "Language",
            RuleStatus.WARNING,
            5,
            f"The resume contains about {words} words, which is on the short side.",
            "Expand sections with specific, relevant detail.",
        )
    return _result(
        "content_length",
        "Sufficient content",
        "Language",
        RuleStatus.FAILED,
        5,
        f"The resume contains only about {words} words.",
        "Add education, skills, projects and (if any) experience detail.",
    )


def score_resume(structured: StructuredResume, text: str) -> AtsScore:
    """Compute the deterministic ATS-readiness score for a parsed resume."""
    lines = list(enumerate(text.splitlines(), start=1))

    results: list[RuleResult] = [
        _rule_contact_email(structured, lines),
        _rule_contact_phone(structured, lines),
        _rule_contact_name(structured),
        _rule_contact_presence(structured),
        _rule_section("education", "Education section present", 8, structured),
        _rule_section("experience", "Experience section present", 9, structured),
        _rule_section("skills", "Skills section present", 7, structured),
        _rule_section("projects", "Projects section present", 6, structured),
        _rule_standard_headings(structured),
        _rule_experience_evidence(structured),
        _rule_bullet_presence(structured),
        _rule_bullet_length(structured),
        _rule_skills_organized(structured),
        _rule_skills_no_duplicates(structured),
        _rule_date_consistency(structured),
        _rule_no_first_person(lines),
        _rule_characters_clean(lines),
        _rule_content_length(text),
    ]

    earned = sum(result.points_earned for result in results)
    maximum = sum(result.points_max for result in results)
    raw_score = round(earned / maximum * 100) if maximum else 0
    score = max(0, min(100, int(raw_score)))

    summary = ScoreSummary(
        passed=sum(1 for result in results if result.status == RuleStatus.PASSED),
        warnings=sum(1 for result in results if result.status == RuleStatus.WARNING),
        failed=sum(1 for result in results if result.status == RuleStatus.FAILED),
    )

    return AtsScore(
        score=score,
        max_score=100,
        label=LABEL,
        disclaimer=DISCLAIMER,
        summary=summary,
        breakdown=results,
    )


def build_issues(score: AtsScore) -> list[DetectedIssue]:
    """Derive an actionable issue list from failing and warning rules."""
    issues: list[DetectedIssue] = []
    for rule in score.breakdown:
        if rule.status == RuleStatus.PASSED:
            continue
        issues.append(
            DetectedIssue(
                rule_id=rule.rule_id,
                severity="error" if rule.status == RuleStatus.FAILED else "warning",
                message=rule.explanation,
                suggestion=rule.suggestion,
                source_lines=rule.source_lines,
            )
        )
    return issues


def analyzed_timestamp() -> datetime:
    """Return the current UTC timestamp (kept separate for testability)."""
    return datetime.now(UTC)
