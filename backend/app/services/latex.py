"""Escaping, Jinja2 environment and LaTeX template rendering.

Every bit of user-provided text is treated as plain text and escaped before
being placed in a template. Jinja2 uses custom delimiters so that LaTeX syntax
cannot collide with the templating language. Resume content is never treated as
executable LaTeX.
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from ..models.render import TemplateInfo
from ..models.structured import StructuredResume

TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates" / "latex"

_SPECIALS: dict[str, str] = {
    "\\": r"\textbackslash{}",
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
    "<": r"\textless{}",
    ">": r"\textgreater{}",
}


def latex_escape(value: object) -> str:
    """Escape arbitrary text so it is safe to place in a LaTeX document.

    All special characters (backslash first, followed by &, %, $, #, _, braces,
    tilde, caret and angle brackets) are replaced with their LaTeX-safe forms.
    """
    if value is None:
        return ""
    rendered: list[str] = []
    for char in str(value):
        rendered.append(_SPECIALS.get(char, char))
    return "".join(rendered)


def pdf_escape(value: object) -> str:
    """Return a plain, brace/backslash-free string safe for PDF metadata strings."""
    if value is None:
        return ""
    text = str(value)
    text = text.replace("&", "and").replace("$", " ").replace("#", " ")
    text = text.replace("~", " ").replace("^", " ").replace("\\", " ")
    text = re.sub(r"[{}%_]", " ", text)
    return " ".join(text.split())


def url_filter(value: object) -> str:
    """Pass a validated URL/email through to \\href/\\url without LaTeX escaping.

    Only used for values produced by the parser's pattern-validated contact
    extractors (email, linkedin, github), so the charset is safe. Braces,
    backslashes and whitespace are still stripped defensively.
    """
    if value is None:
        return ""
    return re.sub(r"[{}\\\n\r\s]", "", str(value)).strip()


def _is_link(value: str) -> bool:
    lowered = value.lower()
    if lowered.startswith("http") or "linkedin.com" in lowered or "github.com" in lowered:
        return True
    return bool(
        re.fullmatch(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}", value)
    )


def _href_target(value: str) -> str:
    """Return a clickable URI for a contact value, or "" when it is not a link.

    hyperref only produces a working annotation when the target has a scheme, so
    an email becomes ``mailto:`` and a bare domain becomes ``https://``.
    """
    if not _is_link(value):
        return ""
    if value.lower().startswith(("http://", "https://", "mailto:")):
        return value
    if "@" in value:
        return "mailto:" + value
    return "https://" + value


@lru_cache(maxsize=1)
def _environment() -> Environment:
    """A Jinja2 environment that cannot clash with LaTeX delimiters."""
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        block_start_string="<%",
        block_end_string="%>",
        variable_start_string="<<",
        variable_end_string=">>",
        comment_start_string="<#",
        comment_end_string="#>",
        autoescape=False,
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
    )
    env.filters["tex"] = latex_escape
    env.filters["pdftex"] = pdf_escape
    env.filters["url"] = url_filter
    return env


TEMPLATES: dict[str, TemplateInfo] = {
    "classic": TemplateInfo(
        id="classic",
        name="Classic",
        description="A single-column, traditional layout with ruled section headings.",
    ),
    "compact": TemplateInfo(
        id="compact",
        name="Compact",
        description="Tighter spacing and a smaller body size for dense resumes.",
    ),
    "modern": TemplateInfo(
        id="modern",
        name="Modern",
        description="Restrained accent-coloured headings with an ATS-safe single column.",
    ),
}

DEFAULT_TEMPLATE = "classic"


def list_templates() -> list[TemplateInfo]:
    return list(TEMPLATES.values())


def validate_template(template_id: str) -> str:
    if template_id not in TEMPLATES:
        raise KeyError(template_id)
    return template_id


def _join_dates(start: str | None, end: str | None) -> str | None:
    parts = [part for part in (start, end) if part]
    if not parts:
        return None
    return " - ".join(parts)


def _contact_items(structured: StructuredResume) -> list[dict[str, object]]:
    basics = structured.basics
    items: list[dict[str, object]] = []
    for value in (basics.email, basics.phone, basics.city, basics.linkedin, basics.github):
        if value:
            items.append({"value": value, "url": _href_target(value)})
    return items


def _skills_lines(structured: StructuredResume) -> list[dict[str, str]]:
    skills = structured.skills
    groups = skills.languages + skills.frameworks + skills.tools + skills.other
    if groups != skills.all_skills:
        return [
            {"label": label, "value": ", ".join(items)}
            for label, items in (
                ("Languages", skills.languages),
                ("Frameworks", skills.frameworks),
                ("Tools", skills.tools),
                ("Other", skills.other),
            )
            if items
        ]
    if skills.all_skills:
        return [{"label": "Skills", "value": ", ".join(skills.all_skills)}]
    return []


def _dedupe_subtitle(title: str | None, subtitle: str | None) -> str | None:
    """Drop a subtitle that is already contained in the title (e.g. a school
    name captured inside the degree field) so it is not shown twice."""
    if title and subtitle and subtitle.lower().strip() in title.lower():
        return None
    return subtitle


def build_render_model(structured: StructuredResume) -> dict:
    """Build the plain data model the Jinja2 templates consume."""
    contact = _contact_items(structured)
    education = [
        {
            "title": entry.degree,
            "subtitle": _dedupe_subtitle(entry.degree, entry.institution),
            "dates": _join_dates(entry.start_date, entry.end_date),
            "score": entry.score,
        }
        for entry in structured.education
    ]
    experience = [
        {
            "title": entry.role,
            "subtitle": entry.company,
            "dates": _join_dates(entry.start_date, entry.end_date),
            "bullets": [bullet.text for bullet in entry.bullets],
        }
        for entry in structured.experience
    ]
    projects = [
        {
            "title": entry.name,
            "subtitle": "Tech: " + ", ".join(entry.technologies) if entry.technologies else None,
            "bullets": [bullet.text for bullet in entry.bullets],
        }
        for entry in structured.projects
    ]
    skills_lines = _skills_lines(structured)
    certifications = structured.certifications or []

    return {
        "name": structured.basics.name,
        "contact": contact,
        "summary": structured.summary,
        "education": education,
        "experience": experience,
        "projects": projects,
        "certifications": certifications,
        "skills_lines": skills_lines,
        "has_contact": bool(contact),
        "has_summary": bool(structured.summary),
        "has_education": bool(education),
        "has_experience": bool(experience),
        "has_projects": bool(projects),
        "has_certifications": bool(certifications),
        "has_skills": bool(skills_lines),
        "pdf_title": structured.basics.name or "Resume",
        "pdf_author": structured.basics.name or "ResumeFit",
    }


def render_template(template_id: str, structured: StructuredResume) -> str:
    """Render the ``template_id`` template for the given canonical resume."""
    validate_template(template_id)
    template = _environment().get_template(f"{template_id}.tex.j2")
    return template.render(**build_render_model(structured)).strip()