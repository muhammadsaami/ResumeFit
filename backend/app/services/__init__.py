"""Service layer: text extraction, parsing, scoring and temporary storage."""

from .analyzer import analyze_resume
from .autofix import plan_changes
from .extraction import ExtractionResult, extract_text
from .guard import check_change
from .parser import parse_resume
from .review import (
    accept_change,
    build_change_list,
    reject_change,
    tailor,
)
from .scoring import build_issues, score_resume
from .store import StoredResume, get_store
from .tailoring import analyze_job_description

__all__ = [
    "ExtractionResult",
    "StoredResume",
    "accept_change",
    "analyze_job_description",
    "analyze_resume",
    "build_change_list",
    "build_issues",
    "check_change",
    "extract_text",
    "get_store",
    "parse_resume",
    "plan_changes",
    "reject_change",
    "score_resume",
    "tailor",
]
