"""Deterministic, rule-based resume auto-fixes.

``plan_changes`` inspects the canonical structured resume plus the original text
and proposes a list of :class:`ResumeChange` objects. Every proposed edit keeps a
reference to the original text, an explanation and a fabrication-guard verdict.
No numbers, employers, titles, dates, qualifications or skills are ever invented.
"""

from __future__ import annotations

import hashlib
import re

from ..models.structured import SourceLine, StructuredResume
from ..models.tailoring import (
    ChangeAction,
    ChangeCategory,
    ChangeOrigin,
    ChangeStatus,
    GuardStatus,
    ResumeChange,
)
from .guard import check_change
from .parser import SECTION_ALIASES, _normalize_heading
from .scoring import _FILLER_PHRASES

# Canonical heading label for each recognised section.
SECTION_LABELS: dict[str, str] = {
    "summary": "Summary",
    "education": "Education",
    "experience": "Experience",
    "skills": "Skills",
    "projects": "Projects",
    "certifications": "Certifications",
    "achievements": "Achievements",
    "publications": "Publications",
    "languages": "Languages",
    "interests": "Interests",
    "contact": "Contact",
}

_EXPECTED_SECTIONS = ("education", "experience", "skills", "projects")

# --- Date handling ----------------------------------------------------------

_MONTH = r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)"
_YEAR = r"(?:19|20)\d{2}"
_DATE_TOKEN = rf"(?:{_MONTH}[a-z]*\.?\s*)?{_YEAR}"
_PRESENT = r"(?:present|current|ongoing|now)"
_DATE_RANGE_LINE_RE = re.compile(rf"(?i)^\s*{_DATE_TOKEN}\s*[-\u2013\u2014]\s*{_DATE_TOKEN}\s*$")
_DATE_PRESENT_LINE_RE = re.compile(
    rf"(?i)^\s*{_DATE_TOKEN}\s*[-\u2013\u2014]\s*{_PRESENT}\s*$"
)

# --- Bullet rewriting -------------------------------------------------------

_FIRST_PERSON_PATTERNS = (
    r"(?i)^\s*I\s+was\s+",
    r"(?i)^\s*I\s+have\s+",
    r"(?i)^\s*I'm\s+",
    r"(?i)^\s*I've\s+",
    r"(?i)\bI\b",
    r"(?i)\bmy\b",
    r"(?i)\bme\b",
    r"(?i)\bwe're\b",
    r"(?i)\bwe\b",
    r"(?i)\bour\b",
    r"(?i)\bus\b",
)

_REMOVABLE_FILLERS = tuple(phrase for phrase in _FILLER_PHRASES if phrase != "responsible for")
_FILLER_WORDS = ("very", "really", "basically", "actually", "just", "simply")

_GERUND_TO_PAST = {
    "managing": "Managed",
    "developing": "Developed",
    "maintaining": "Maintained",
    "creating": "Created",
    "building": "Built",
    "designing": "Designed",
    "implementing": "Implemented",
    "leading": "Led",
    "testing": "Tested",
    "deploying": "Deployed",
    "automating": "Automated",
    "writing": "Wrote",
    "coordinating": "Coordinated",
    "supporting": "Supported",
    "analyzing": "Analyzed",
    "improving": "Improved",
    "reducing": "Reduced",
    "handling": "Handled",
    "preparing": "Prepared",
    "working": "Worked",
    "overseeing": "Oversaw",
    "ensuring": "Ensured",
    "providing": "Provided",
    "performing": "Performed",
    "collaborating": "Collaborated",
    "delivering": "Delivered",
    "resolving": "Resolved",
    "optimizing": "Optimized",
    "documenting": "Documented",
    "training": "Trained",
    "mentoring": "Mentored",
    "launching": "Launched",
    "streamlining": "Streamlined",
}

_PAST_TO_BASE = {
    "built": "build",
    "developed": "develop",
    "created": "create",
    "managed": "manage",
    "designed": "design",
    "implemented": "implement",
    "wrote": "write",
    "led": "lead",
    "improved": "improve",
    "reduced": "reduce",
    "automated": "automate",
    "maintained": "maintain",
    "tested": "test",
    "deployed": "deploy",
    "handled": "handle",
    "prepared": "prepare",
    "analyzed": "analyze",
    "coordinated": "coordinate",
    "supported": "support",
    "added": "add",
    "fixed": "fix",
    "integrated": "integrate",
    "delivered": "deliver",
    "performed": "perform",
    "provided": "provide",
    "collaborated": "collaborate",
    "oversaw": "oversee",
    "ensured": "ensure",
    "worked": "work",
    "documented": "document",
    "optimized": "optimize",
    "streamlined": "streamline",
    "launched": "launch",
    "trained": "train",
    "mentored": "mentor",
    "resolved": "resolve",
}
_BASE_TO_PAST = {base: past for past, base in _PAST_TO_BASE.items()}

_LONG_BULLET_LIMIT = 320

# --- Personal-detail detection ----------------------------------------------

_PERSONAL_DETAIL_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("date of birth", re.compile(r"(?i)\b(date of birth|d\.?o\.?b\.?|birth date|born on)\b")),
    (
        "marital status",
        re.compile(r"(?i)\b(marital status|married|unmarried|divorced|widowed|single)\b"),
    ),
    ("photograph", re.compile(r"(?i)\b(photograph|photo|passport[- ]size)\b")),
    (
        "full street address",
        re.compile(
            r"(?i)\b\d{1,5}\s+[A-Za-z][A-Za-z.]*(?:\s+[A-Za-z][A-Za-z.]*)*\s+"
            r"(street|st|avenue|ave|road|rd|lane|ln|drive|dr|boulevard|blvd|way|court|ct|"
            r"place|pl|terrace|close)\b"
        ),
    ),
)


def _change_id(
    category: ChangeCategory,
    source_line: int | None,
    original: str,
) -> str:
    """A stable id that does not depend on the proposed text.

    Excluding the proposed text means a user edit keeps the same identity, so the
    edited change is preserved (rather than replaced) when the plan is refreshed.
    """
    raw = f"{category.value}|{source_line}|{original}"
    return "chg_" + hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]


def _replace_change(
    *,
    category: ChangeCategory,
    title: str,
    original: str,
    proposed: str,
    reason: str,
    source_line: int | None,
    structured: StructuredResume,
    source_text: str,
    origin: ChangeOrigin = ChangeOrigin.AUTOFIX,
    source_end_line: int | None = None,
) -> ResumeChange:
    guard_status, guard_reasons = check_change(
        proposed, original=original, structured=structured, source_text=source_text
    )
    evidence = [SourceLine(line=source_line, text=original)] if source_line else []
    return ResumeChange(
        id=_change_id(category, source_line, original),
        category=category,
        action=ChangeAction.REPLACE,
        origin=origin,
        title=title,
        original_text=original,
        proposed_text=proposed,
        reason=reason,
        source_line=source_line,
        source_end_line=source_end_line,
        evidence=evidence,
        guard_status=guard_status,
        guard_reasons=guard_reasons,
        status=ChangeStatus.PROPOSED,
        applicable=guard_status != GuardStatus.UNSAFE,
    )


def _flag_change(
    *,
    category: ChangeCategory,
    title: str,
    reason: str,
    source_line: int | None = None,
    original_text: str = "",
    evidence: list[SourceLine] | None = None,
    origin: ChangeOrigin = ChangeOrigin.AUTOFIX,
) -> ResumeChange:
    return ResumeChange(
        id=_change_id(category, source_line, title),
        category=category,
        action=ChangeAction.FLAG,
        origin=origin,
        title=title,
        original_text=original_text,
        proposed_text=None,
        reason=reason,
        source_line=source_line,
        evidence=evidence or [],
        guard_status=GuardStatus.NEEDS_REVIEW,
        guard_reasons=[],
        status=ChangeStatus.PROPOSED,
        applicable=False,
    )


# --- Individual fix planners ------------------------------------------------


def _plan_headings(
    structured: StructuredResume, text: str, source_text: str
) -> list[ResumeChange]:
    changes: list[ResumeChange] = []
    for number, raw in enumerate(text.splitlines(), start=1):
        canonical = SECTION_ALIASES.get(_normalize_heading(raw))
        if canonical is None or canonical not in SECTION_LABELS:
            continue
        current = raw.strip().rstrip(":").strip()
        label = SECTION_LABELS[canonical]
        if not current or current.lower() == label.lower():
            continue
        changes.append(
            _replace_change(
                category=ChangeCategory.HEADING_NORMALIZATION,
                title=f"Use the standard '{label}' heading",
                original=raw.strip(),
                proposed=label,
                reason=(
                    f"'{current}' is recognised as the {label} section but is not a "
                    f"standard heading; ATS parsers match '{label}' most reliably."
                ),
                source_line=number,
                structured=structured,
                source_text=source_text,
            )
        )
    return changes


def _normalize_date_line(value: str) -> str:
    result = value.strip().replace("\u2013", "-").replace("\u2014", "-")
    result = re.sub(r"\s*-\s*", " - ", result)
    result = re.sub(r"(?i)\b(present|current|ongoing|now)\b", "Present", result)
    return re.sub(r"\s{2,}", " ", result).strip()


def _plan_dates(structured: StructuredResume, text: str, source_text: str) -> list[ResumeChange]:
    changes: list[ResumeChange] = []
    for number, raw in enumerate(text.splitlines(), start=1):
        if not (_DATE_RANGE_LINE_RE.match(raw) or _DATE_PRESENT_LINE_RE.match(raw)):
            continue
        proposed = _normalize_date_line(raw)
        if proposed == raw.strip():
            continue
        changes.append(
            _replace_change(
                category=ChangeCategory.DATE_NORMALIZATION,
                title="Standardise the date format",
                original=raw.strip(),
                proposed=proposed,
                reason=(
                    "Use a consistent 'YYYY - YYYY' or 'YYYY - Present' format; no missing "
                    "dates were added."
                ),
                source_line=number,
                structured=structured,
                source_text=source_text,
            )
        )
    return changes


def _strip_first_person(text: str) -> str:
    result = text
    for pattern in _FIRST_PERSON_PATTERNS:
        result = re.sub(pattern, "", result)
    return re.sub(r"\s{2,}", " ", result)


def _strip_filler(text: str) -> str:
    result = text
    for phrase in _REMOVABLE_FILLERS:
        result = re.sub(re.escape(phrase), "", result, flags=re.I)
    for word in _FILLER_WORDS:
        result = re.sub(rf"(?i)\b{word}\b", "", result)
    return re.sub(r"\s{2,}", " ", result)


def _strengthen_opener(text: str) -> str | None:
    match = re.match(r"(?i)^\s*responsible for\s+(.+)$", text)
    if not match:
        return None
    rest = match.group(1).strip()
    first, _, remainder = rest.partition(" ")
    word = first.lower()
    past = _GERUND_TO_PAST.get(word) or _BASE_TO_PAST.get(word)
    if not past:
        return None
    return f"{past} {remainder}".strip()


def _apply_case(sample: str, replacement: str) -> str:
    if sample[:1].isupper():
        return replacement[:1].upper() + replacement[1:]
    return replacement


def _normalize_tense(text: str, is_current: bool) -> str:
    # Only normalise tense for past roles (present/base verbs -> past). For a
    # current role, completed achievements and ongoing duties legitimately use
    # different tenses, so rewriting them would change meaning. Leave them alone.
    if is_current:
        return text
    first, sep, remainder = text.partition(" ")
    past = _BASE_TO_PAST.get(first.lower())
    if past:
        return _apply_case(first, past) + sep + remainder
    return text


def _recapitalize(text: str) -> str:
    value = text.strip()
    if not value:
        return value
    if value[0].islower() and value[:2].lower() not in {"a "}:
        return value[0].upper() + value[1:]
    return value


def _rewrite_bullet(text: str, is_current: bool | None) -> tuple[str, list[str]]:
    result = text
    flags: list[str] = []

    before = result
    result = _strip_first_person(result)
    if result != before:
        flags.append("first_person")

    before = result
    result = _strip_filler(result)
    if result != before and "first_person" not in flags:
        flags.append("first_person")

    before = result
    strengthened = _strengthen_opener(result)
    if strengthened is not None:
        result = strengthened
        flags.append("weak_opener")

    if is_current is not None:
        before = result
        result = _normalize_tense(result, is_current)
        if result != before:
            flags.append("tense_normalization")

    result = _recapitalize(re.sub(r"\s{2,}", " ", result).strip())
    return result, flags


def _bullets_with_context(
    structured: StructuredResume,
) -> list[tuple[str, int | None, int | None, bool | None]]:
    bullets: list[tuple[str, int | None, int | None, bool | None]] = []
    for entry in structured.experience:
        is_current = bool(entry.end_date and entry.end_date.lower() in {"present", "current"})
        for bullet in entry.bullets:
            bullets.append(
                (bullet.text, bullet.source_line, bullet.source_end_line, is_current)
            )
    for project in structured.projects:
        for bullet in project.bullets:
            bullets.append((bullet.text, bullet.source_line, bullet.source_end_line, None))
    return bullets


def _plan_bullets(
    structured: StructuredResume, text: str, source_text: str
) -> list[ResumeChange]:
    lines = text.splitlines()
    changes: list[ResumeChange] = []
    for bullet_text, source_line, source_end_line, is_current in _bullets_with_context(structured):
        if source_line is None or not (1 <= source_line <= len(lines)):
            continue
        end_line = source_end_line or source_line
        if not (source_line <= end_line <= len(lines)):
            end_line = source_line
        span = lines[source_line - 1 : end_line]
        # Replace the whole physical range the bullet occupies. For a wrapped
        # bullet this collapses the continuation line instead of leaving it
        # behind as a duplicated sentence.
        original = "\n".join(span) if end_line > source_line else lines[source_line - 1].strip()
        rewritten, flags = _rewrite_bullet(bullet_text, is_current)
        rewritten = re.sub(r"\s{2,}", " ", rewritten).strip()
        proposed = f"- {rewritten}"
        if proposed.strip() == original.strip():
            continue
        range_end = end_line if end_line > source_line else None

        if flags:
            category = ChangeCategory(flags[0])
            title = {
                "first_person": "Remove first-person or filler wording",
                "weak_opener": "Strengthen the opening verb",
                "tense_normalization": "Match the verb tense to the role",
            }[flags[0]]
            reason = {
                "first_person": (
                    "Rewritten in third person with filler removed; no factual claims changed."
                ),
                "weak_opener": (
                    "Replaced a weak opening with a strong action verb; meaning preserved."
                ),
                "tense_normalization": (
                    "Adjusted to the tense implied by the role's dates; no facts changed."
                ),
            }[flags[0]]
            change = _replace_change(
                category=category,
                title=title,
                original=original,
                proposed=proposed,
                reason=reason,
                source_line=source_line,
                source_end_line=range_end,
                structured=structured,
                source_text=source_text,
            )
            changes.append(change)
            continue

        if len(bullet_text) > _LONG_BULLET_LIMIT:
            shortened = _recapitalize(_strip_filler(bullet_text).strip())
            shortened = re.sub(r"\s{2,}", " ", shortened).strip()
            if shortened and len(shortened) < len(bullet_text):
                change = _replace_change(
                    category=ChangeCategory.BULLET_SHORTENING,
                    title="Shorten an over-long bullet",
                    original=original,
                    proposed=f"- {shortened}",
                    reason=(
                        "Trimmed filler wording from a long bullet while keeping all facts. "
                        "Consider splitting it further if detail was lost."
                    ),
                    source_line=source_line,
                    source_end_line=range_end,
                    structured=structured,
                    source_text=source_text,
                )
                if (
                    len(shortened) > _LONG_BULLET_LIMIT
                    and change.guard_status != GuardStatus.UNSAFE
                ):
                    change.guard_status = GuardStatus.NEEDS_REVIEW
                    change.guard_reasons = [
                        "The bullet is still long after trimming; manual shortening recommended."
                    ]
                changes.append(change)
                continue

        changes.append(
            _replace_change(
                category=ChangeCategory.BULLET_NORMALIZATION,
                title="Normalise the bullet formatting",
                original=original,
                proposed=proposed,
                reason="Standardise the bullet marker and spacing for consistent parsing.",
                source_line=source_line,
                source_end_line=range_end,
                structured=structured,
                source_text=source_text,
            )
        )
    return changes


def _grouped_skills(structured: StructuredResume) -> list[str]:
    skills = structured.skills
    ordered = [*skills.languages, *skills.frameworks, *skills.tools, *skills.other]
    remaining = [skill for skill in skills.all_skills if skill not in ordered]
    return [*ordered, *remaining]


def _plan_skills(structured: StructuredResume, source_text: str) -> list[ResumeChange]:
    skills = structured.skills
    if not skills.all_skills or not skills.source_lines:
        return []
    lines = source_text.splitlines()
    first_line = min(line.line for line in skills.source_lines)
    last_line = max(line.line for line in skills.source_lines)
    if not (1 <= first_line <= len(lines) and first_line <= last_line <= len(lines)):
        return []
    # Replace every physical line the skills section occupies, so labelled
    # category lines are consumed rather than left behind duplicating the list.
    original = "\n".join(lines[first_line - 1 : last_line])
    grouped = _grouped_skills(structured)
    proposed = ", ".join(grouped)
    if skills.duplicates:
        category = ChangeCategory.DUPLICATE_SKILLS
        title = "Remove duplicate skills"
        reason = (
            "Duplicate skills were found ("
            + ", ".join(dict.fromkeys(skills.duplicates))
            + "); each skill is kept once with no additions."
        )
    elif grouped != skills.all_skills:
        category = ChangeCategory.SKILL_GROUPING
        title = "Group existing skills by category"
        reason = (
            "Reorders existing skills into languages, frameworks and tools for a cleaner list; "
            "no skills are added or removed."
        )
    else:
        return []
    if proposed.strip() == original.strip():
        return []
    return [
        _replace_change(
            category=category,
            title=title,
            original=original,
            proposed=proposed,
            reason=reason,
            source_line=first_line,
            source_end_line=last_line if last_line > first_line else None,
            structured=structured,
            source_text=source_text,
        )
    ]


def _plan_missing_contact(structured: StructuredResume) -> list[ResumeChange]:
    changes: list[ResumeChange] = []
    missing = [
        label
        for label, value in (
            ("email address", structured.basics.email),
            ("phone number", structured.basics.phone),
            ("full name", structured.basics.name),
        )
        if not value
    ]
    if missing:
        changes.append(
            _flag_change(
                category=ChangeCategory.MISSING_CONTACT,
                title="Missing contact information",
                reason=(
                    "The resume does not include: "
                    + ", ".join(missing)
                    + ". Add these details; nothing was invented for you."
                ),
            )
        )
    return changes


def _plan_missing_sections(structured: StructuredResume) -> list[ResumeChange]:
    changes: list[ResumeChange] = []
    for section in _EXPECTED_SECTIONS:
        if section not in structured.sections_detected:
            changes.append(
                _flag_change(
                    category=ChangeCategory.MISSING_SECTION,
                    title=f"Add a '{section.title()}' section",
                    reason=(
                        f"No '{section.title()}' section heading was detected. Add one with your "
                        "real content; nothing was invented for you."
                    ),
                )
            )
    return changes


def _plan_personal_details(text: str) -> list[ResumeChange]:
    changes: list[ResumeChange] = []
    for number, raw in enumerate(text.splitlines(), start=1):
        for label, pattern in _PERSONAL_DETAIL_PATTERNS:
            if pattern.search(raw):
                changes.append(
                    _flag_change(
                        category=ChangeCategory.PERSONAL_DETAIL,
                        title=f"Review possible {label}",
                        reason=(
                            f"Line {number} may contain {label}. Personal details of this kind are "
                            "often unnecessary and can be removed for privacy; review it yourself. "
                            "Nothing was removed automatically."
                        ),
                        source_line=number,
                        original_text=raw.strip(),
                        evidence=[SourceLine(line=number, text=raw.strip())],
                    )
                )
                break
    return changes


def plan_changes(structured: StructuredResume, text: str) -> list[ResumeChange]:
    """Return the full deterministic list of proposed changes for ``text``."""
    changes: list[ResumeChange] = []
    changes.extend(_plan_headings(structured, text, text))
    changes.extend(_plan_dates(structured, text, text))
    changes.extend(_plan_bullets(structured, text, text))
    changes.extend(_plan_skills(structured, text))
    changes.extend(_plan_missing_contact(structured))
    changes.extend(_plan_missing_sections(structured))
    changes.extend(_plan_personal_details(text))

    deduped: dict[str, ResumeChange] = {}
    for change in changes:
        deduped.setdefault(change.id, change)
    return list(deduped.values())
