"""In-memory store for generated artifacts with access-controlled downloads.

Artifacts are addressed by opaque short identifiers and are never reachable
through any filesystem path derived from user input. They expire together with
their owning resume. The store holds only small, size-capped blobs created by
this service.
"""

from __future__ import annotations

import re
import secrets
import threading
from dataclasses import dataclass, field
from datetime import UTC, datetime

from ..core.errors import ApiError

_ID_RE = re.compile(r"^[A-Za-z0-9_-]{16,64}$")


@dataclass
class Artifact:
    id: str
    resume_id: str
    kind: str
    filename: str
    media_type: str
    data: bytes
    created_at: datetime
    expires_at: datetime


@dataclass
class ArtifactStore:
    _entries: dict[str, Artifact] = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def create(
        self,
        *,
        resume_id: str,
        kind: str,
        filename: str,
        media_type: str,
        data: bytes,
        expires_at: datetime,
    ) -> Artifact:
        artifact = Artifact(
            id=secrets.token_urlsafe(24),
            resume_id=resume_id,
            kind=kind,
            filename=filename,
            media_type=media_type,
            data=data,
            created_at=datetime.now(UTC),
            expires_at=expires_at,
        )
        with self._lock:
            self._purge_locked()
            self._entries[artifact.id] = artifact
        return artifact

    def get(self, artifact_id: str | None) -> Artifact:
        with self._lock:
            self._purge_locked()
            if not artifact_id or not _ID_RE.match(artifact_id):
                raise ApiError(404, "artifact_not_found", "Unknown or malformed artifact id.")
            artifact = self._entries.get(artifact_id)
            if artifact is None:
                raise ApiError(404, "artifact_not_found", "Unknown or malformed artifact id.")
            return artifact

    def delete_for_resume(self, resume_id: str) -> int:
        with self._lock:
            removed = [
                key
                for key, artifact in self._entries.items()
                if artifact.resume_id == resume_id
            ]
            for key in removed:
                self._entries.pop(key, None)
            return len(removed)

    def purge_expired(self) -> int:
        with self._lock:
            return self._purge_locked()

    def count(self) -> int:
        with self._lock:
            return len(self._entries)

    def purge_expired_any_time(self) -> int:
        """Purge entries past their expiry regardless of timezone labels."""
        now = datetime.now(UTC)
        with self._lock:
            expired = [
                key
                for key, artifact in self._entries.items()
                if _as_utc(artifact.expires_at) <= now
            ]
            for key in expired:
                self._entries.pop(key, None)
            return len(expired)

    def _purge_locked(self) -> int:
        now = datetime.now(UTC)
        expired = [
            key
            for key, artifact in self._entries.items()
            if _as_utc(artifact.expires_at) <= now
        ]
        for key in expired:
            self._entries.pop(key, None)
        return len(expired)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


_store: ArtifactStore | None = None


def get_artifact_store() -> ArtifactStore:
    global _store
    if _store is None:
        _store = ArtifactStore()
    return _store