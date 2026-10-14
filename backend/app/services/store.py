"""In-memory temporary store for parsed resumes.

Phase 1 keeps resume data in process memory only. Entries are opaque and
expire after a configurable TTL (one hour by default). A lazy sweep removes
expired entries on every access, and the app runs a periodic cleanup task.
"""

from __future__ import annotations

import secrets
import threading
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from functools import lru_cache

from ..config import get_settings
from ..core.errors import ApiError
from ..models.resume import ExtractionStatus, ParsingMetadata, SourceType
from ..models.tailoring import ResumeChange

_ID_BYTES = 24


def _utcnow() -> datetime:
    return datetime.now(UTC)


@dataclass
class StoredResume:
    """Internal storage record. Never returned to clients directly."""

    id: str
    text: str
    status: ExtractionStatus
    metadata: ParsingMetadata
    created_at: datetime
    expires_at: datetime
    effective_text: str = ""
    changes: dict[str, ResumeChange] = field(default_factory=dict)
    plan_generated: bool = False


@dataclass
class _Entry:
    resume: StoredResume
    created_monotonic: float = field(default=0.0)


class ResumeStore:
    """Thread-safe, TTL-based in-memory store for resumes."""

    def __init__(self, ttl_seconds: int) -> None:
        self._ttl = timedelta(seconds=ttl_seconds)
        self._lock = threading.Lock()
        self._entries: dict[str, StoredResume] = {}

    def create(
        self,
        *,
        text: str,
        source_type: SourceType,
        metadata: ParsingMetadata,
    ) -> StoredResume:
        now = _utcnow()
        resume = StoredResume(
            id=secrets.token_urlsafe(_ID_BYTES),
            text=text,
            status=ExtractionStatus.PROCESSED,
            metadata=metadata,
            created_at=now,
            expires_at=now + self._ttl,
            effective_text=text,
        )
        with self._lock:
            self._purge_locked()
            self._entries[resume.id] = resume
        return resume

    def save(self, resume: StoredResume) -> None:
        """Persist mutations to an existing record, if it is still present."""
        with self._lock:
            self._purge_locked()
            if resume.id not in self._entries:
                raise ApiError(404, "resume_not_found", "No resume exists for that id.")
            self._entries[resume.id] = resume

    def get(self, resume_id: str) -> StoredResume:
        with self._lock:
            self._purge_locked()
            resume = self._entries.get(resume_id)
        if resume is None:
            raise ApiError(404, "resume_not_found", "No resume exists for that id.")
        return resume

    def delete(self, resume_id: str) -> None:
        with self._lock:
            self._purge_locked()
            if self._entries.pop(resume_id, None) is None:
                raise ApiError(404, "resume_not_found", "No resume exists for that id.")

    def purge_expired(self) -> int:
        with self._lock:
            return self._purge_locked()

    def count(self) -> int:
        with self._lock:
            self._purge_locked()
            return len(self._entries)

    def _purge_locked(self) -> int:
        now = _utcnow()
        expired = [key for key, value in self._entries.items() if value.expires_at <= now]
        for key in expired:
            del self._entries[key]
        return len(expired)


@lru_cache
def get_store() -> ResumeStore:
    """Return the process-wide resume store."""
    return ResumeStore(ttl_seconds=get_settings().resume_ttl_seconds)
