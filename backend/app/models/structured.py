"""Canonical structured resume models.

These models represent whatever was genuinely recovered from the resume text.
Every optional field defaults to ``None`` (or an empty list) so that missing
information is reported as missing rather than invented.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class SourceLine(BaseModel):
    """A reference back to a line in the original extracted text."""

    model_config = ConfigDict(extra="forbid")

    line: int = Field(..., ge=1, description="1-based line number in the extracted text.")
    text: str = Field(..., description="The exact original line content.")


class BulletItem(BaseModel):
    """A single resume bullet point with an optional source reference.

    ``source_end_line`` is set when the bullet wrapped onto following physical
    lines in the extracted text, so a rewrite can replace the whole range rather
    than a single line (which would leave the wrapped fragment behind).
    """

    model_config = ConfigDict(extra="forbid")

    text: str
    source_line: int | None = None
    source_end_line: int | None = None


class Basics(BaseModel):
    """Contact and identity fields parsed from the resume header."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    email: str | None = None
    phone: str | None = None
    city: str | None = None
    linkedin: str | None = None
    github: str | None = None


class EducationEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    institution: str | None = None
    degree: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    score: str | None = None
    source_lines: list[SourceLine] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class ExperienceEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company: str | None = None
    role: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    bullets: list[BulletItem] = Field(default_factory=list)
    source_lines: list[SourceLine] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class ProjectEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    technologies: list[str] = Field(default_factory=list)
    bullets: list[BulletItem] = Field(default_factory=list)
    source_lines: list[SourceLine] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class Skills(BaseModel):
    model_config = ConfigDict(extra="forbid")

    languages: list[str] = Field(default_factory=list)
    frameworks: list[str] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)
    other: list[str] = Field(default_factory=list)
    all_skills: list[str] = Field(default_factory=list)
    duplicates: list[str] = Field(default_factory=list)
    source_lines: list[SourceLine] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class ParsingConfidence(BaseModel):
    """Transparent provenance metadata about the extraction."""

    model_config = ConfigDict(extra="forbid")

    overall: float = Field(default=0.0, ge=0.0, le=1.0)
    sections_found: int = 0
    sections_expected: int = 0
    contact_fields_found: int = 0


class StructuredResume(BaseModel):
    """The canonical, validated representation of a parsed resume."""

    model_config = ConfigDict(extra="forbid")

    basics: Basics = Field(default_factory=Basics)
    summary: str | None = None
    education: list[EducationEntry] = Field(default_factory=list)
    experience: list[ExperienceEntry] = Field(default_factory=list)
    projects: list[ProjectEntry] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    skills: Skills = Field(default_factory=Skills)
    sections_detected: list[str] = Field(default_factory=list)
    nonstandard_headings: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    confidence: ParsingConfidence = Field(default_factory=ParsingConfidence)
