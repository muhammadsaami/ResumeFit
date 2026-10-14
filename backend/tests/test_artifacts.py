"""Tests for the in-memory artifact store."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.core.errors import ApiError
from app.services.artifacts import ArtifactStore


def _make(store: ArtifactStore, *, resume_id: str = "res_1", data: bytes = b"hello world"):
    return store.create(
        resume_id=resume_id,
        kind="tex",
        filename="resume.tex",
        media_type="application/x-tex",
        data=data,
        expires_at=datetime.now(UTC) + timedelta(hours=1),
    )


def test_create_and_get_roundtrip() -> None:
    store = ArtifactStore()
    artifact = _make(store)
    fetched = store.get(artifact.id)
    assert fetched.data == b"hello world"
    assert fetched.kind == "tex"
    assert fetched.filename == "resume.tex"
    assert fetched.resume_id == "res_1"


def test_get_unknown_id_returns_404() -> None:
    store = ArtifactStore()
    with pytest.raises(ApiError) as exc:
        store.get("does-not-exist-at-all")
    assert exc.value.status_code == 404
    assert exc.value.code == "artifact_not_found"


def test_get_malformed_id_returns_404() -> None:
    store = ArtifactStore()
    for bad in ("x" * 160, "", "../etc/passwd", "..%2F..%2F..%2Fetc%2Fpasswd", "..\\..\\win.ini"):
        with pytest.raises(ApiError) as exc:
            store.get(bad)
        assert exc.value.status_code == 404
        assert exc.value.code == "artifact_not_found", bad


def test_get_none_returns_404() -> None:
    with pytest.raises(ApiError):
        ArtifactStore().get(None)


def test_delete_for_resume_only_removes_its_artifacts() -> None:
    store = ArtifactStore()
    a1 = _make(store, resume_id="r1")
    a2 = _make(store, resume_id="r2")
    _make(store, resume_id="r1")
    assert store.delete_for_resume("r1") == 2
    assert store.get(a2.id).resume_id == "r2"
    with pytest.raises(ApiError):
        store.get(a1.id)


def test_expired_artifact_is_unreachable() -> None:
    store = ArtifactStore()
    artifact = store.create(
        resume_id="r1",
        kind="tex",
        filename="resume.tex",
        media_type="application/x-tex",
        data=b"x",
        expires_at=datetime.now(UTC) - timedelta(seconds=1),
    )
    with pytest.raises(ApiError) as exc:
        store.get(artifact.id)
    assert exc.value.code == "artifact_not_found"
    assert store.count() == 0


def test_purge_expired_counts_removed() -> None:
    store = ArtifactStore()
    _make(store)
    store.create(
        resume_id="r2",
        kind="tex",
        filename="resume.tex",
        media_type="application/x-tex",
        data=b"x",
        expires_at=datetime.now(UTC) - timedelta(seconds=1),
    )
    assert store.purge_expired() == 1
    assert store.count() == 1


def test_ids_are_opaque_and_unique() -> None:
    store = ArtifactStore()
    one = _make(store)
    two = _make(store)
    assert one.id != two.id
    assert one.id != "resume.tex"