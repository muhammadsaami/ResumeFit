"""Deterministic structured resume parser.

Turns raw extracted resume text into a :class:`StructuredResume`. The parser is
pure and deterministic: the same input text always produces the same output, no
randomness is used, and unknown information is left as ``None`` rather than
guessed. Section heading aliases are normalised to canonical names.
"""

from __future__ import annotations

import re

from ..models.structured import (
    Basics,
    BulletItem,
    EducationEntry,
    ExperienceEntry,
    ParsingConfidence,
    ProjectEntry,
    Skills,
    SourceLine,
    StructuredResume,
)
from .taxonomy import canonical_skill, categorize_skill

# --- Section heading aliases ------------------------------------------------

SECTION_ALIASES: dict[str, str] = {
    # summary
    "summary": "summary",
    "professional summary": "summary",
    "career summary": "summary",
    "profile": "summary",
    "professional profile": "summary",
    "objective": "summary",
    "career objective": "summary",
    "about": "summary",
    "about me": "summary",
    # education
    "education": "education",
    "academic background": "education",
    "academic qualifications": "education",
    "educational qualifications": "education",
    "qualifications": "education",
    "academics": "education",
    "education details": "education",
    # experience
    "experience": "experience",
    "work experience": "experience",
    "professional experience": "experience",
    "employment history": "experience",
    "employment": "experience",
    "work history": "experience",
    "career history": "experience",
    "internships": "experience",
    "internship": "experience",
    "experience and internships": "experience",
    # skills
    "skills": "skills",
    "technical skills": "skills",
    "technical expertise": "skills",
    "technical proficiencies": "skills",
    "core competencies": "skills",
    "key skills": "skills",
    "skills and expertise": "skills",
    "skills expertise": "skills",
    "technologies": "skills",
    "technical skills and tools": "skills",
    "areas of expertise": "skills",
    # projects
    "projects": "projects",
    "project": "projects",
    "personal projects": "projects",
    "academic projects": "projects",
    "key projects": "projects",
    "selected projects": "projects",
    # other recognised sections
    "certifications": "certifications",
    "certification": "certifications",
    "certificates": "certifications",
    "licenses certifications": "certifications",
    "achievements": "achievements",
    "accomplishments": "achievements",
    "awards": "achievements",
    "honors": "achievements",
    "awards honors": "achievements",
    "publications": "publications",
    "languages": "languages",
    "interests": "interests",
    "hobbies": "interests",
    "contact": "contact",
    "contact information": "contact",
    "contact details": "contact",
}

CANONICAL_SECTIONS = set(SECTION_ALIASES.values())

_BULLET_CHARS = "•\u2023\u25e6\u25aa\u2022\u25cf\u25cb\u00b7\u2219-\u2013\u2014*"
_ROLE_KEYWORDS = {
    "developer", "engineer", "intern", "analyst", "manager", "designer", "consultant",
    "lead", "specialist", "architect", "administrator", "scientist", "programmer",
    "tester", "qa", "devops", "associate", "executive", "officer", "coordinator",
    "trainee", "fresher", "student", "freelancer", "founder", "cto", "ceo",
    "researcher", "teacher", "instructor", "editor", "writer",
}
_COMPANY_HINTS = {
    "inc", "ltd", "llc", "corp", "corporation", "technologies", "technology",
    "solutions", "systems", "labs", "pvt", "private", "company", "group",
    "software", "services", "bank", "consulting", "studios", "media", "tech",
}
_DEGREE_KEYWORDS = {
    "bachelor", "master", "b.sc", "bsc", "m.sc", "msc", "bca", "mca", "b.tech",
    "m.tech", "btech", "mtech", "phd", "ph.d", "doctorate", "diploma", "associate",
    "b.a", "ba", "m.a", "ma", "b.com", "m.com", "b.e", "be", "m.e", "me",
    "high school", "secondary", "intermediate", "graduation", "undergraduate",
    "postgraduate", "degree",
}
_INSTITUTION_KEYWORDS = {
    "university", "college", "institute", "institution", "school", "academy",
    "polytechnic", "faculty",
}

_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
_LINKEDIN_RE = re.compile(
    r"(?:https?://)?(?:www\.)?linkedin\.com/(?:in|pub)/[A-Za-z0-9\-_%]+", re.I
)
_GITHUB_RE = re.compile(r"(?:https?://)?(?:www\.)?github\.com/[A-Za-z0-9\-_]+", re.I)
_PHONE_CANDIDATE_RE = re.compile(r"\+?\d[\d\s().\-]{6,}\d")
_DATE_RANGE_RE = re.compile(
    r"^\s*(?:19|20)\d{2}\s*[-\u2013\u2014]\s*(?:(?:19|20)\d{2}|present|current)\s*$", re.I
)
_MONTH_YEAR_RE = re.compile(
    r"(?:(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?\s*)?(?:19|20)\d{2}",
    re.I,
)
_PRESENT_RE = re.compile(r"\b(present|current|ongoing|now)\b", re.I)
_SCORE_RE = re.compile(
    r"(?i)\b(?:gpa|cgpa|sgpa|grade|percentage|score)\b\s*[:\-]?\s*"
    r"([0-9]{1,3}(?:\.[0-9]+)?(?:\s*/\s*[0-9.]+)?\s*%?)"
)
_PERCENT_RE = re.compile(r"\b([0-9]{1,3}(?:\.[0-9]+)?\s*%)\b")


# --- Low-level helpers ------------------------------------------------------


def _normalize_heading(line: str) -> str:
    value = line.strip().lower()
    value = value.strip("#*•-–— ")
    value = value.rstrip(":").strip()
    value = re.sub(r"[\u2013\u2014]", "-", value)
    value = re.sub(r"\s+", " ", value)
    return value


def _looks_like_unknown_heading(raw: str) -> bool:
    value = raw.strip()
    if not value or len(value) > 45:
        return False
    if len(value) < 4:
        # A 1-3 character token (e.g. a wrapped bullet fragment like "UI.") is
        # never a section heading.
        return False
    if "@" in value or "http" in value.lower():
        return False
    if re.match(r"^[A-Za-z][A-Za-z0-9 /&'\-,.]*:\s+\S", value):
        # A "Label: value" data line (e.g. "GPA: 3.8") is not a heading.
        return False
    words = value.split()
    if len(words) > 5:
        return False
    if value.endswith("."):
        # A sentence fragment accidentally uppercased (e.g. "Full.") is not a heading.
        return False
    if value.endswith(":"):
        return True
    if value.isupper() and re.search(r"[A-Za-z]", value) and not re.search(r"\d", value):
        return True
    return False


def _is_bullet(raw: str) -> bool:
    value = raw.lstrip()
    if not value:
        return False
    if value[0] in _BULLET_CHARS:
        return True
    return bool(re.match(r"^\d+[.)]\s+", value))


def _bullet_text(raw: str) -> str:
    value = raw.strip()
    value = re.sub(r"^\d+[.)]\s+", "", value)
    return value.lstrip(_BULLET_CHARS).strip()


def _split_blocks(section_lines: list[tuple[int, str]]) -> list[list[tuple[int, str]]]:
    """Split on blank lines. Retained for headings/fallbacks that segment by line only."""
    blocks: list[list[tuple[int, str]]] = []
    current: list[tuple[int, str]] = []
    for number, raw in section_lines:
        if not raw.strip():
            if current:
                blocks.append(current)
                current = []
        else:
            current.append((number, raw))
    if current:
        blocks.append(current)
    return blocks


def _has_degree_keyword(text: str) -> bool:
    lowered = text.lower()
    return any(keyword in lowered for keyword in _DEGREE_KEYWORDS)


def _has_institution_keyword(text: str) -> bool:
    lowered = text.lower()
    return any(keyword in lowered for keyword in _INSTITUTION_KEYWORDS)


_MONTH = r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?"


def _strip_trailing_date(value: str) -> str:
    """Remove a trailing date range (and any separator before it) from a value.

    Handles bare-year ranges (``2018 - 2022``) as well as month/year ranges
    (``Aug 2023 - Aug 2025``) so an institution or degree is not left with a
    dangling date fragment such as ``... Studies Aug 2023 - Aug``.
    """
    value = re.sub(
        rf"(?i)[\s,;|•*\-–—]*\s*(?:{_MONTH}\s+)?(?:19|20)\d{{2}}\s*[-–—]\s*"
        rf"(?:(?:{_MONTH}\s+)?(?:19|20)\d{{2}}|present|current|now)\s*$",
        "",
        value,
    )
    value = re.sub(
        rf"(?i)[\s,;|•*\-–—]*\s*(?:{_MONTH}\s+)?(?:19|20)\d{{2}}\s*$", "", value
    )
    return value.strip(" |•*,-–—;:").strip()


def _clean_entry_value(value: str) -> str:
    """Trim bullets, separators and trailing dates from a single header value."""
    if not value:
        return value
    value = re.sub(r"\s+", " ", value.strip())
    value = value.strip(_BULLET_CHARS).strip()
    value = _strip_trailing_date(value)
    return value.strip().rstrip(" |•,-–—;:").strip()


def _clean_degree(value: str) -> str | None:
    """Clean a degree line, keeping only the text before any ``|`` metadata.

    Real resumes often pack score and location onto the degree line, e.g.
    ``MCA (AI) - Master of ..., Artificial Intelligence | CGPA: 8.02 Dehradun``.
    Only the degree text before the separator is kept.
    """
    cleaned = _clean_entry_value(value)
    if "|" in cleaned:
        cleaned = cleaned.split("|", 1)[0].strip()
    cleaned = _clean_entry_value(cleaned)
    return cleaned or None


def _is_continuation(raw: str) -> bool:
    """True when a line is a wrapped continuation of the previous bullet/line.

    These lines start with lowercase text and carry no entry-separator signals,
    so they belong to the block that is currently open.
    """
    value = raw.strip()
    if not value:
        return False
    if "|" in value:
        return False
    if _DATE_RANGE_RE.match(value):
        return False
    if re.match(r"(?i)^(?:tech|stack|built with|tools used)\s*[:)]", value):
        return False
    if re.match(r"^\d+[.):]\s+", value):
        return False
    return value[0].islower()


def _should_merge_continuation(raw: str, last_text: str) -> bool:
    """True when ``raw`` is a wrapped continuation of the previous bullet.

    PDF text layers wrap a bullet across physical lines. The continuation usually
    starts lowercase, but can start with a capitalised word or punctuation
    (``UI.``, ``(backend).``) when the previous line did not end a sentence. We
    therefore also treat a line as a continuation when the open bullet does not
    end with terminal punctuation.
    """
    if _is_continuation(raw):
        return True
    value = raw.strip()
    if not value or not last_text:
        return False
    if _looks_like_unknown_heading(value):
        return False
    return not last_text.rstrip().endswith((".", "!", "?", ":", ";"))


def _is_entry_header_after_bullets(
    raw: str, current: list[tuple[int, str]]
) -> bool:
    """Decide whether ``raw`` starts a new entry inside an open block.

    Only considered once the current block already contains bullet points (so a
    first line can never be mistaken for a new entry). Entry separators such as
    ``Role, Company | 2022 - Present`` or ``Project | Tech, Stack`` are detected
    structurally; short upper-case header-like lines are accepted too.
    """
    if not any(_is_bullet(text) for _, text in current):
        return False
    value = raw.strip()
    if not value:
        return False
    if _DATE_RANGE_RE.match(value):
        return False
    if "|" in value or "\t" in value:
        return True
    if _is_continuation(raw):
        return False
    if len(value) > 100:
        return False
    if _has_role_keyword(value) or _looks_like_company(value) or _looks_like_name(value):
        return True
    return False


def _segment_entries(
    section_lines: list[tuple[int, str]],
    kind: str,
) -> list[list[tuple[int, str]]]:
    """Split a section into entry blocks even when blank lines are absent.

    Real PDF extraction rarely preserves blank lines between jobs, projects or
    degrees, so boundaries are also recognised structurally. ``kind`` is one of
    ``education``, ``experience`` or ``projects`` — each has slightly different
    rules for what starts a new entry.
    """
    blocks: list[list[tuple[int, str]]] = []
    current: list[tuple[int, str]] = []

    def _close() -> None:
        nonlocal current
        if current:
            blocks.append(current)
        current = []

    for number, raw in section_lines:
        if not raw.strip():
            _close()
            continue
        if not current:
            current.append((number, raw))
            continue
        if _is_bullet(raw):
            current.append((number, raw))
            continue
        if kind == "education":
            starts_new = _has_degree_keyword(raw) or _has_institution_keyword(raw)
            current_is_complete = any(
                _has_degree_keyword(text) for _, text in current
            ) and any(_has_institution_keyword(text) for _, text in current)
            if starts_new and current_is_complete:
                _close()
                current = [(number, raw)]
            else:
                current.append((number, raw))
            continue
        if (
            kind == "projects"
            and any(_is_bullet(text) for _, text in current)
            and _looks_like_project_title(raw)
        ):
            _close()
            current = [(number, raw)]
            continue
        if _is_entry_header_after_bullets(raw, current):
            _close()
            current = [(number, raw)]
        else:
            current.append((number, raw))
    _close()
    return blocks


def _extract_institution(value: str) -> str | None:
    """Pull the institution from a line that mixes degree, school and dates."""
    match = re.search(
        r"(?i)\b(university|college|institute|institution|school|academy|polytechnic|faculty)\b",
        value,
    )
    if not match:
        return None
    return _clean_entry_value(value[match.start():])


def _split_list(text: str) -> list[str]:
    normalized = text.replace("•", " ").replace("\u2023", " ").replace("\u25e6", " ")
    parts = re.split(r"[,;|\n]|\s{2,}|\band\b", normalized)
    results: list[str] = []
    for part in parts:
        token = part.strip().strip(".*-\u2013\u2014/").strip()
        if token and token.lower() not in {"etc", "and"}:
            results.append(token)
    return results


def _extract_dates(text: str) -> tuple[str | None, str | None, list[str]]:
    present = bool(_PRESENT_RE.search(text))
    tokens = [token.strip() for token in _MONTH_YEAR_RE.findall(text)]
    if not tokens:
        return (None, "Present" if present else None, [])
    if len(tokens) == 1:
        if present:
            return (tokens[0], "Present", tokens)
        return (None, tokens[0], tokens)
    start = tokens[0]
    end = "Present" if present else tokens[-1]
    return (start, end, tokens)


def _extract_score(text: str) -> str | None:
    match = _SCORE_RE.search(text)
    if match:
        return match.group(1).strip()
    match = _PERCENT_RE.search(text)
    if match:
        return match.group(1).strip()
    return None


def _has_dates(text: str) -> bool:
    return bool(_MONTH_YEAR_RE.search(text)) or bool(_PRESENT_RE.search(text))


def _looks_like_name(line: str) -> bool:
    value = line.strip()
    if not value or len(value) > 45:
        return False
    if any(ch.isdigit() for ch in value):
        return False
    lowered = value.lower()
    if "@" in value or "http" in lowered or "linkedin" in lowered or "github" in lowered:
        return False
    words = value.split()
    if not 1 <= len(words) <= 4:
        return False
    if not re.fullmatch(r"[^\W\d_][\w'\-. ]*", value, re.UNICODE):
        return False
    if value.isupper() and len(words) == 1:
        return False
    return True


def _name_from_line(raw: str) -> str | None:
    """Recover a name from a header line where name and contacts share one line.

    Reads the leading run of letter-only tokens and stops at the first token that
    looks like contact data (digits, email, URL). ``None`` means no reliable name
    could be recovered, so the caller can keep looking.
    """
    leading: list[str] = []
    strip_chars = " \t,;|•\u2022-–—"
    for token in raw.strip().split():
        clean = token.strip(strip_chars)
        if not clean:
            continue
        lowered = clean.lower()
        if "@" in lowered or "http" in lowered or "linkedin" in lowered or "github" in lowered:
            continue
        if any(ch.isdigit() for ch in clean):
            break
        if not re.fullmatch(r"[^\W\d_][\w'’.-]*", clean, re.UNICODE):
            break
        leading.append(clean)
    if not leading or leading[0][0].islower():
        return None
    if len(leading) <= 4:
        candidate = " ".join(leading)
        if _looks_like_name(candidate):
            return candidate
    return None


def _looks_like_company(text: str) -> bool:
    lowered = text.lower()
    return any(hint in lowered for hint in _COMPANY_HINTS)


def _looks_like_project_title(raw: str) -> bool:
    """Heuristically identify a project title line inside a projects section.

    Most real resumes pack project entries without blank lines. A title is a
    short, capitalised phrase that carries no link or ``Tech:`` label; a trailing
    year is a strong signal. Wrapped bullet fragments (``UI.``, ``(backend).``)
    end with punctuation and are excluded.
    """
    value = raw.strip()
    if not value or len(value) > 80 or value[0].islower():
        return False
    if value.endswith("."):
        return False
    if "://" in value or value.startswith(("github.com", "www.")):
        return False
    if re.match(
        r"(?i)^(?:tech(?:nologies|nology)?|tech stack|stack|built with|tools used)\s*[:\-]",
        value,
    ):
        return False
    if _has_dates(value):
        return True
    words = value.split()
    capitalized = sum(1 for word in words if word[:1].isupper())
    return len(words) >= 2 and capitalized >= len(words) - 1


def _looks_like_tech_list(text: str) -> bool:
    """True for a bare, comma-separated technology list (no ``Tech:`` label)."""
    value = text.strip()
    if not value or "://" in value or value.lower().startswith(("github", "www.")):
        return False
    if _has_dates(value):
        return False
    parts = [part.strip() for part in re.split(r"[,;|]", value) if part.strip()]
    if len(parts) < 2:
        return False
    return all(1 <= len(part.split()) <= 3 for part in parts)


def _has_role_keyword(text: str) -> bool:
    lowered = text.lower()
    return any(keyword in lowered for keyword in _ROLE_KEYWORDS)


def _split_role_company(header_text: str) -> tuple[str | None, str | None]:
    text = header_text.strip()
    parts = [part.strip() for part in re.split(
        r"\s+(?:at|@)\s+|\s*[|•]\s*|\s+[-\u2013\u2014]\s+|\s*,\s*", text
    ) if part.strip()]
    if len(parts) >= 2:
        first, second = parts[0], parts[1]
        first_role = _has_role_keyword(first)
        second_role = _has_role_keyword(second)
        if first_role and not second_role:
            return first, second
        if second_role and not first_role:
            return second, first
        if _looks_like_company(first) and not _looks_like_company(second):
            return second, first
        return first, second
    if _has_role_keyword(text):
        return text, None
    if _looks_like_company(text):
        return None, text
    return text, None


def _entry_confidence(*values: object) -> float:
    present = sum(1 for value in values if value)
    total = len(values)
    if total == 0:
        return 0.0
    return round(present / total, 2)


# --- Section splitting ------------------------------------------------------


def _match_section(raw: str) -> tuple[str | None, str | None]:
    """Identify a section heading, possibly with trailing content on the same line.

    Returns ``(canonical_section, consumed_content)``. ``consumed_content`` is
    non-None when a heading and its first line of content were merged onto one
    line during extraction (e.g. ``Technical Skills: Python, SQL``), so that
    content is fed into the section instead of being lost.

    Only recognised aliases are ever treated as headings. A prefix is accepted
    only when it is immediately followed by an explicit separator (``:``, ``|``,
    ``-``, ``-``), so sentences such as "Experience working in fast-paced teams"
    are never mistaken for headings.
    """
    value = _normalize_heading(raw)
    if not value:
        return None, None
    exact = SECTION_ALIASES.get(value)
    if exact:
        return exact, None

    # "Projects (Academic)", "Technical Skills (Resume)" -> strip trailing parens.
    parenthetical = re.sub(r"\s*\([^)]*\)\s*$", "", value).strip()
    if parenthetical and parenthetical != value:
        exact = SECTION_ALIASES.get(parenthetical)
        if exact:
            return exact, None

    for key in sorted(SECTION_ALIASES, key=len, reverse=True):
        if not value.startswith(key):
            continue
        remainder = value[len(key):].strip()
        if not remainder:
            continue
        if remainder.startswith(("|", ":", ";")):
            return SECTION_ALIASES[key], remainder[1:].lstrip(" |;:-–—").strip()
        if remainder.startswith(("-", "\u2013", "\u2014")):
            return SECTION_ALIASES[key], remainder[1:].strip().lstrip("|:; ").strip()
    return None, None


def _split_sections(
    lines: list[tuple[int, str]],
) -> tuple[
    list[tuple[int, str]],
    dict[str, list[tuple[int, str]]],
    list[str],
    list[str],
]:
    header: list[tuple[int, str]] = []
    sections: dict[str, list[tuple[int, str]]] = {}
    order: list[str] = []
    nonstandard: list[str] = []
    current: str | None = None

    for number, raw in lines:
        canonical, consumed = _match_section(raw)
        key = canonical
        if canonical is None and _looks_like_unknown_heading(raw):
            key = "other"
        # A "Languages:" label inside a Skills section is a category line, not a
        # new section heading. Without this guard the skills content vanishes.
        if current == "skills" and canonical == "languages":
            key = None
        if key is not None:
            if canonical is None:
                nonstandard.append(raw.strip())
            current = key
            sections.setdefault(key, [])
            if key not in order:
                order.append(key)
            if consumed:
                sections[key].append((number, consumed))
            continue
        if current is None:
            header.append((number, raw))
        else:
            sections[current].append((number, raw))

    return header, sections, order, nonstandard


# --- Field extraction -------------------------------------------------------


def _find_by_regex(
    lines: list[tuple[int, str]], pattern: re.Pattern[str]
) -> tuple[str, int] | None:
    for number, raw in lines:
        match = pattern.search(raw)
        if match:
            return match.group(0).strip(), number
    return None


def _find_phone(lines: list[tuple[int, str]]) -> tuple[str, int] | None:
    for number, raw in lines:
        for match in _PHONE_CANDIDATE_RE.finditer(raw):
            candidate = match.group(0).strip()
            if _DATE_RANGE_RE.match(candidate):
                continue
            start = match.start()
            end = match.end()
            if start > 0 and raw[start - 1].isalpha():
                continue
            if end < len(raw) and raw[end].isalpha():
                continue
            digits = re.sub(r"\D", "", candidate)
            if 8 <= len(digits) <= 15:
                return candidate, number
    return None


def _find_name(header: list[tuple[int, str]]) -> str | None:
    for _, raw in header:
        match = re.match(r"(?i)^\s*name\s*[:\-]\s*(.+)$", raw.strip())
        if match and _looks_like_name(match.group(1)):
            return match.group(1).strip()
    for _, raw in header:
        if _looks_like_name(raw):
            return raw.strip()
    for _, raw in header:
        candidate = _name_from_line(raw)
        if candidate:
            return candidate
    return None


def _find_city(lines: list[tuple[int, str]], header: list[tuple[int, str]]) -> str | None:
    for _, raw in lines:
        match = re.match(r"(?i)^\s*(?:location|city|address|based in)\s*[:\-]\s*(.+)$", raw.strip())
        if match:
            return match.group(1).strip()
    for _, raw in header:
        value = raw.strip()
        if len(value) <= 40 and re.fullmatch(
            r"[A-Za-z][A-Za-z .'\-]+,\s*[A-Za-z][A-Za-z .'\-]+", value
        ):
            return value
    # A city often shares a separator-separated header line with other contacts,
    # e.g. "email | +44 7000 123456 | London, UK | linkedin.com/in/jordan".
    for _, raw in header:
        for segment in re.split(r"\s*[|•]\s*", raw):
            segment = segment.strip()
            if len(segment) <= 40 and re.fullmatch(
                r"[A-Za-z][A-Za-z .'\-]+,\s*[A-Za-z][A-Za-z .'\-]+", segment
            ):
                return segment
    return None


def _parse_summary(section_lines: list[tuple[int, str]]) -> str | None:
    """Join a summary/profile section into a single plain-text paragraph."""
    parts: list[str] = []
    for _, raw in section_lines:
        text = _bullet_text(raw) if _is_bullet(raw) else raw.strip()
        text = text.strip().strip(_BULLET_CHARS).strip()
        if text:
            parts.append(text)
    if not parts:
        return None
    return " ".join(parts)


def _parse_basics(
    lines: list[tuple[int, str]],
    header: list[tuple[int, str]],
    sections: dict[str, list[tuple[int, str]]],
) -> Basics:
    contact_lines = header + sections.get("contact", [])
    email = _find_by_regex(lines, _EMAIL_RE)
    linkedin = _find_by_regex(lines, _LINKEDIN_RE)
    github = _find_by_regex(lines, _GITHUB_RE)
    phone = (
        _find_phone(contact_lines)
        or _find_phone(lines[:1])
        or _find_phone(lines)
    )
    return Basics(
        name=_find_name(header),
        email=email[0] if email else None,
        phone=phone[0] if phone else None,
        city=_find_city(lines, header),
        linkedin=linkedin[0] if linkedin else None,
        github=github[0] if github else None,
    )


def _parse_education(section_lines: list[tuple[int, str]]) -> list[EducationEntry]:
    entries: list[EducationEntry] = []
    for block in _segment_entries(section_lines, "education"):
        joined = " ".join(raw for _, raw in block)
        start, end, _ = _extract_dates(joined)
        score = _extract_score(joined)
        degree = institution = None
        degree_line = inst_line = None
        for index, (_, raw) in enumerate(block):
            value = raw.strip()
            lowered = value.lower()
            if degree is None and any(keyword in lowered for keyword in _DEGREE_KEYWORDS):
                degree = _clean_degree(value)
                degree_line = index
            if institution is None and any(
                keyword in lowered for keyword in _INSTITUTION_KEYWORDS
            ):
                institution = _clean_entry_value(value)
                inst_line = index
        if degree is None and block:
            degree = _clean_degree(block[0][1])
        if not degree:
            degree = None
        # When degree and institution share a single extracted line, keep only
        # the school part for the institution field.
        if degree_line is not None and degree_line == inst_line:
            extracted = _extract_institution(institution or "") if institution else None
            institution = extracted if extracted else None
        if not institution:
            institution = None
        # Lines like "M.Sc. Computer Science, University College London | 2014"
        # list the school inside the degree text as well as in its own field.
        # Drop the duplicated trailing school so it is not rendered twice.
        if degree and institution:
            lowered_degree = degree.lower().rstrip()
            lowered_institution = institution.lower().rstrip()
            if lowered_degree.endswith(lowered_institution):
                degree = degree[: lowered_degree.rfind(lowered_institution)]
                degree = degree.rstrip(" ,;|-\u2013\u2014").strip() or None
        source_lines = [
            SourceLine(line=number, text=raw.strip()) for number, raw in block if raw.strip()
        ]
        entries.append(
            EducationEntry(
                institution=institution,
                degree=degree,
                start_date=start,
                end_date=end,
                score=score,
                source_lines=source_lines,
                confidence=_entry_confidence(degree, institution, start or end),
            )
        )
    return entries


def _parse_experience(section_lines: list[tuple[int, str]]) -> list[ExperienceEntry]:
    entries: list[ExperienceEntry] = []
    for block in _segment_entries(section_lines, "experience"):
        bullets: list[BulletItem] = []
        header: list[tuple[int, str]] = []
        for number, raw in block:
            if _is_bullet(raw):
                text = _bullet_text(raw)
                if text:
                    bullets.append(
                        BulletItem(text=text, source_line=number, source_end_line=number)
                    )
            elif bullets and _should_merge_continuation(raw, bullets[-1].text):
                text = raw.strip()
                if text:
                    last = bullets[-1]
                    bullets[-1] = BulletItem(
                        text=(last.text + " " + text).strip(),
                        source_line=last.source_line,
                        source_end_line=number,
                    )
            else:
                header.append((number, raw))
        header_text = " ".join(raw for _, raw in header)
        start, end, _ = _extract_dates(header_text or " ".join(raw for _, raw in block))
        role: str | None = None
        company: str | None = None
        if header:
            first_raw = header[0][1]
            role, company = _split_role_company(first_raw)
            role = _clean_entry_value(role) if role else None
            has_date_first = _has_dates(first_raw)
            company_line: str | None = None
            for _, raw in header[1:]:
                candidate = raw.strip()
                if not candidate:
                    continue
                if _has_dates(candidate) and "|" not in candidate:
                    continue
                if "|" in candidate or _looks_like_company(candidate):
                    company_line = candidate
                    break
            if (
                company_line is None
                and (company is None or has_date_first)
                and len(header) > 1
            ):
                candidate = header[1][1].strip()
                if candidate and not _has_dates(candidate):
                    company_line = candidate
            if company_line:
                company = _clean_entry_value(company_line.split("|")[0]) or company
                stripped_role = _clean_entry_value(_strip_trailing_date(first_raw))
                if stripped_role:
                    role = stripped_role
        if company:
            company = _clean_entry_value(company)
        if not role:
            role = None
        if not company:
            company = None
        source_lines = [
            SourceLine(line=number, text=raw.strip()) for number, raw in block if raw.strip()
        ]
        entries.append(
            ExperienceEntry(
                company=company,
                role=role,
                start_date=start,
                end_date=end,
                bullets=bullets,
                source_lines=source_lines,
                confidence=_entry_confidence(role, company, start or end, bullets),
            )
        )
    return entries


def _parse_projects(section_lines: list[tuple[int, str]]) -> list[ProjectEntry]:
    entries: list[ProjectEntry] = []
    for block in _segment_entries(section_lines, "projects"):
        bullets: list[BulletItem] = []
        header: list[tuple[int, str]] = []
        for number, raw in block:
            if _is_bullet(raw):
                text = _bullet_text(raw)
                if text:
                    bullets.append(
                        BulletItem(text=text, source_line=number, source_end_line=number)
                    )
            elif bullets and _should_merge_continuation(raw, bullets[-1].text):
                text = raw.strip()
                if text:
                    last = bullets[-1]
                    bullets[-1] = BulletItem(
                        text=(last.text + " " + text).strip(),
                        source_line=last.source_line,
                        source_end_line=number,
                    )
            else:
                header.append((number, raw))
        name: str | None = None
        technologies: list[str] = []
        if header:
            first = _clean_entry_value(header[0][1])
            if first and "|" in first:
                parts = [part.strip() for part in first.split("|")]
                first_part_tech = _split_list(" ".join(parts[1:]))
                if first_part_tech:
                    name = _clean_entry_value(parts[0])
                    technologies = first_part_tech
                else:
                    name = first
            else:
                name = first
        for _, raw in header[1:]:
            match = re.match(
                r"(?i)^(?:tech(?:nologies|nology)?|tech stack|stack|built with|tools used)"
                r"\s*[:\-]\s*(.+)$",
                raw.strip(),
            )
            if match:
                technologies = _split_list(match.group(1))
                break
        if not technologies:
            # A bare comma-separated list on the line after the title is the
            # technologies even without a "Tech:" label, e.g.
            # "React.js, Node.js, Express.js, MongoDB".
            for _, raw in header[1:]:
                if _looks_like_tech_list(raw):
                    technologies = _split_list(raw)
                    break
        if name:
            parenthetical = re.search(r"[\(\[](.*?)[\)\]]", name)
            if parenthetical:
                if not technologies:
                    technologies = _split_list(parenthetical.group(1))
                name = re.sub(r"\s*[\(\[](.*?)[\)\]]\s*", " ", name).strip()
            name = _clean_entry_value(name)
        if not name:
            name = None
        source_lines = [
            SourceLine(line=number, text=raw.strip()) for number, raw in block if raw.strip()
        ]
        entries.append(
            ProjectEntry(
                name=name,
                technologies=technologies,
                bullets=bullets,
                source_lines=source_lines,
                confidence=_entry_confidence(name, technologies, bullets),
            )
        )
    return entries


def _parse_certifications(section_lines: list[tuple[int, str]]) -> list[str]:
    certifications: list[str] = []
    for _, raw in section_lines:
        value = raw.strip()
        if _is_bullet(value):
            value = _bullet_text(value)
        value = _clean_entry_value(value)
        if not value:
            continue
        if certifications and value[:1].islower():
            # A wrapped certification line continues the previous entry.
            certifications[-1] = f"{certifications[-1]} {value}".strip()
        else:
            certifications.append(value)
    return certifications


def _parse_skills(section_lines: list[tuple[int, str]]) -> tuple[Skills, list[SourceLine]]:
    tokens: list[tuple[str, int]] = []
    for number, raw in section_lines:
        value = raw.strip()
        if not value:
            continue
        labeled = re.match(r"^[A-Za-z][A-Za-z /&+]{1,30}\s*:\s*(.+)$", value)
        content = labeled.group(1) if labeled else value
        for token in _split_list(content):
            tokens.append((token, number))

    source_lines = [
        SourceLine(line=number, text=raw.strip()) for number, raw in section_lines if raw.strip()
    ]

    languages: list[str] = []
    frameworks: list[str] = []
    tools: list[str] = []
    other: list[str] = []
    all_skills: list[str] = []
    duplicates: list[str] = []
    seen: dict[str, str] = {}

    for token, _ in tokens:
        canonical = canonical_skill(token)
        if canonical in seen:
            duplicates.append(token)
            continue
        seen[canonical] = token
        all_skills.append(token)
        bucket = categorize_skill(token)
        if bucket == "languages":
            languages.append(token)
        elif bucket == "frameworks":
            frameworks.append(token)
        elif bucket == "tools":
            tools.append(token)
        else:
            other.append(token)

    skills = Skills(
        languages=languages,
        frameworks=frameworks,
        tools=tools,
        other=other,
        all_skills=all_skills,
        duplicates=duplicates,
        source_lines=source_lines,
        confidence=round(min(len(all_skills), 5) / 5, 2) if all_skills else 0.0,
    )
    return skills, source_lines


# --- Public entry point -----------------------------------------------------


def parse_resume(text: str) -> StructuredResume:
    """Parse extracted resume ``text`` into a :class:`StructuredResume`."""
    for invisible in ("\ufeff", "\u200b", "\u200c", "\u200d"):
        text = text.replace(invisible, "")
    raw_lines = text.splitlines()
    lines: list[tuple[int, str]] = list(enumerate(raw_lines, start=1))

    header, sections, order, nonstandard = _split_sections(lines)

    basics = _parse_basics(lines, header, sections)
    summary = _parse_summary(sections.get("summary", []))
    education = _parse_education(sections.get("education", []))
    experience = _parse_experience(sections.get("experience", []))
    projects = _parse_projects(sections.get("projects", []))
    certifications = _parse_certifications(sections.get("certifications", []))
    skills, _ = _parse_skills(sections.get("skills", []))

    sections_detected = [name for name in order if name in CANONICAL_SECTIONS]

    warnings: list[str] = []
    if basics.name is None:
        warnings.append("Could not confidently detect the candidate name.")
    if basics.email is None:
        warnings.append("No email address was detected.")
    if basics.phone is None:
        warnings.append("No phone number was detected.")
    expected = ["education", "experience", "skills", "projects"]
    for name in expected:
        if name not in sections_detected:
            warnings.append(f"No standard '{name.title()}' section heading was detected.")
    if nonstandard:
        warnings.append(
            "Non-standard section headings detected: " + ", ".join(sorted(nonstandard)) + "."
        )

    contact_fields = [
        basics.name,
        basics.email,
        basics.phone,
        basics.city,
        basics.linkedin,
        basics.github,
    ]
    contact_found = sum(1 for field in contact_fields if field)
    sections_found = sum(1 for name in expected if name in sections_detected)
    overall = round(0.6 * (sections_found / len(expected)) + 0.4 * (contact_found / 6), 2)

    return StructuredResume(
        basics=basics,
        summary=summary,
        education=education,
        experience=experience,
        projects=projects,
        certifications=certifications,
        skills=skills,
        sections_detected=sections_detected,
        nonstandard_headings=sorted(nonstandard),
        warnings=warnings,
        confidence=ParsingConfidence(
            overall=overall,
            sections_found=sections_found,
            sections_expected=len(expected),
            contact_fields_found=contact_found,
        ),
    )
