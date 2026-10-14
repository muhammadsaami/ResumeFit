"""Models for the deterministic ATS-readiness analysis."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from .structured import SourceLine, StructuredResume


class RuleStatus(str, Enum):
    """Outcome of a single scoring rule."""

    PASSED = "passed"
    WARNING = "warning"
    FAILED = "failed"


class RuleResult(BaseModel):
    """A single, explainable ATS-readiness check."""

    model_config = ConfigDict(extra="forbid")

    rule_id: str = Field(..., description="Stable identifier, e.g. 'contact_email'.")
    name: str
    category: str
    status: RuleStatus
    points_earned: float = Field(..., ge=0)
    points_max: float = Field(..., ge=0)
    explanation: str
    suggestion: str | None = None
    source_lines: list[SourceLine] = Field(default_factory=list)


class ScoreSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    passed: int = 0
    warnings: int = 0
    failed: int = 0


class AtsScore(BaseModel):
    """An estimated, rule-based ATS-readiness indicator (not a real ATS score)."""

    model_config = ConfigDict(extra="forbid")

    score: int = Field(..., ge=0, le=100)
    max_score: int = 100
    label: str
    disclaimer: str
    summary: ScoreSummary
    breakdown: list[RuleResult] = Field(default_factory=list)


class DetectedIssue(BaseModel):
    """A failed or warning rule surfaced as an actionable issue."""

    model_config = ConfigDict(extra="forbid")

    rule_id: str
    severity: str = Field(..., description="'error' for failed rules, 'warning' otherwise.")
    message: str
    suggestion: str | None = None
    source_lines: list[SourceLine] = Field(default_factory=list)


class AnalysisResponse(BaseModel):
    """Response body for ``POST /api/v1/resumes/{resume_id}/analyze``."""

    model_config = ConfigDict(extra="forbid")

    resume_id: str
    status: str
    structured_resume: StructuredResume
    ats_score: AtsScore
    detected_issues: list[DetectedIssue] = Field(default_factory=list)
    parsing_warnings: list[str] = Field(default_factory=list)
    analyzed_at: datetime
