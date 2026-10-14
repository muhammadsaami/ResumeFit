"""Deterministic fabrication guard for proposed resume edits.

The guard does not rely on an LLM. It compares a proposed rewrite against the
original text and the structured resume and flags any change that introduces
information which cannot be traced back to the source: new numbers/metrics,
employers, job titles, degrees or certifications, or skills the resume never
mentions.
"""

from __future__ import annotations

import re

from ..models.structured import StructuredResume
from ..models.tailoring import GuardStatus
from .taxonomy import canonical_skill, known_skill_terms

#: Inserted only as an explicit, human-readable placeholder - never a real value.
METRIC_PLACEHOLDER = "[add real metric if available]"

_NUMBER_RE = re.compile(r"\d[\d,]*(?:\.\d+)?%?")
_WORD_RE = re.compile(r"[a-z0-9][a-z0-9+#.]*")

_DEGREE_TERMS = {
    "bachelor",
    "master",
    "b.sc",
    "bsc",
    "m.sc",
    "msc",
    "bca",
    "mca",
    "b.tech",
    "m.tech",
    "btech",
    "mtech",
    "phd",
    "ph.d",
    "doctorate",
    "diploma",
    "mba",
    "b.com",
    "m.com",
    "b.e",
    "m.e",
    "high school",
    "secondary",
    "intermediate",
    "postgraduate",
    "undergraduate",
}
_CERT_TERMS = {
    "certified",
    "certification",
    "certificate",
    "certifications",
    "credential",
    "licence",
    "license",
}

_TITLE_TERMS = {
    "engineer",
    "developer",
    "manager",
    "intern",
    "analyst",
    "designer",
    "consultant",
    "architect",
    "scientist",
    "administrator",
    "specialist",
    "director",
    "coordinator",
}
_SENIOR_TERMS = ("senior", "junior", "lead", "principal", "head of", "chief")
_COMPANY_HINTS = (
    "inc",
    "ltd",
    "llc",
    "corp",
    "corporation",
    "technologies",
    "solutions",
    "systems",
    "labs",
    "pvt",
    "company",
    "consulting",
    "studios",
)


def _numbers(text: str) -> set[str]:
    return {match.group(0).rstrip("%") for match in _NUMBER_RE.finditer(text)}


def _words(text: str) -> set[str]:
    return {match.group(0).lower() for match in _WORD_RE.finditer(text)}


def _traceability(proposed: str, reference: str) -> float:
    proposed_words = {word for word in _words(proposed) if len(word) >= 3}
    if not proposed_words:
        return 1.0
    reference_words = _words(reference)
    overlap = sum(1 for word in proposed_words if word in reference_words)
    return overlap / len(proposed_words)


def check_change(
    proposed: str,
    *,
    original: str,
    structured: StructuredResume,
    source_text: str,
) -> tuple[GuardStatus, list[str]]:
    """Return the guard verdict and the reasons for any concern."""
    reasons: list[str] = []
    proposed_lower = proposed.lower()
    reference = f"{original}\n{source_text}"

    new_numbers = _numbers(proposed) - _numbers(original) - _numbers(source_text)
    new_numbers.discard("")
    if new_numbers:
        reasons.append(
            "Introduces a number or metric not present in the original: "
            + ", ".join(sorted(new_numbers))
            + "."
        )

    source_words = _words(source_text)
    known_companies = {
        entry.company.lower()
        for entry in structured.experience
        if entry.company
    } | {entry.institution.lower() for entry in structured.education if entry.institution}

    if any(hint in proposed_lower for hint in _COMPANY_HINTS):
        for match in re.finditer(
            r"\b([A-Z][A-Za-z&.']*(?:\s+[A-Z][A-Za-z&.']*){0,3})\s+"
            r"(Inc|Ltd|LLC|Corp|Corporation|Technologies|Solutions|Systems|Labs|Pvt)\b",
            proposed,
        ):
            phrase = match.group(0).lower()
            if phrase not in source_words and not any(phrase in name for name in known_companies):
                reasons.append(f"Mentions a possible new employer: {match.group(0)}.")
                break

    for senior in _SENIOR_TERMS:
        pattern = rf"\b{re.escape(senior)}\s+([A-Za-z]+)\b"
        for match in re.finditer(pattern, proposed_lower):
            if match.group(0) not in source_text.lower():
                reasons.append(f"Suggests a new seniority/title phrase: {match.group(0)}.")
                break

    for title in _TITLE_TERMS:
        if re.search(rf"\b{title}\b", proposed_lower) and title not in source_words:
            reasons.append(f"Introduces a job title keyword not found in the resume: {title}.")
            break

    for degree in _DEGREE_TERMS:
        if re.search(rf"\b{re.escape(degree)}\b", proposed_lower) and degree not in source_words:
            reasons.append(f"Introduces a qualification not found in the resume: {degree}.")
            break

    for cert in _CERT_TERMS:
        if re.search(rf"\b{cert}\b", proposed_lower) and cert not in source_words:
            reasons.append(f"Introduces a credential not found in the resume: {cert}.")
            break

    resume_skills = {canonical_skill(skill) for skill in structured.skills.all_skills}
    for term, canonical in known_skill_terms().items():
        if re.search(rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])", proposed_lower):
            if canonical in resume_skills:
                continue
            if re.search(rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])", source_text.lower()):
                continue
            reasons.append(f"Introduces a skill not supported by the resume: {term}.")
            break

    if reasons:
        return GuardStatus.UNSAFE, reasons

    if _traceability(proposed, reference) < 0.4:
        return (
            GuardStatus.NEEDS_REVIEW,
            ["The rewrite cannot be clearly traced back to the original text."],
        )

    return GuardStatus.SAFE, []
