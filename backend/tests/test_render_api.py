"""Endpoint tests for templates, rendering, artifacts and Overleaf export."""

from __future__ import annotations

from datetime import UTC

import pytest
from fastapi.testclient import TestClient

from app.services.compiler import CompileResult, detect_compiler

from .synthetic import COMPLETE_RESUME

RESUMES_URL = "/api/v1/resumes"
ARTIFACTS_URL = "/api/v1/artifacts"


def _create(client: TestClient, text: str = COMPLETE_RESUME) -> str:
    response = client.post(RESUMES_URL, json={"text": text})
    assert response.status_code == 201, response.text
    return response.json()["resume_id"]


def test_list_templates(client: TestClient) -> None:
    resume_id = _create(client)
    response = client.get(f"{RESUMES_URL}/{resume_id}/render/templates")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["default_template"] == "classic"
    ids = {template["id"] for template in body["templates"]}
    assert ids == {"classic", "compact", "modern"}
    assert all({"id", "name", "description"} <= set(t) for t in body["templates"])


def test_list_templates_unknown_resume_returns_404(client: TestClient) -> None:
    response = client.get(f"{RESUMES_URL}/does-not-exist/render/templates")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "resume_not_found"


def test_render_unknown_resume_returns_404(client: TestClient) -> None:
    response = client.post(f"{RESUMES_URL}/does-not-exist/render", json={"template_id": "classic"})
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "resume_not_found"


def test_render_invalid_template_returns_422(client: TestClient) -> None:
    resume_id = _create(client)
    response = client.post(f"{RESUMES_URL}/{resume_id}/render", json={"template_id": "fancy"})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_template"


def test_render_returns_tex_even_without_compiler(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.services import rendering

    resume_id = _create(client)
    monkeypatch.setattr(rendering, "detect_compiler", lambda: None)
    response = client.post(f"{RESUMES_URL}/{resume_id}/render", json={"template_id": "classic"})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "compiler_unavailable"
    assert body["tex"]["kind"] == "tex"
    assert body["pdf"] is None
    assert body["message"]

    download = client.get(body["tex"]["download_url"])
    assert download.status_code == 200
    assert "\\begin{document}" in download.text


def test_render_compile_failure_is_reported(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.services import rendering

    resume_id = _create(client)
    monkeypatch.setattr(
        rendering, "compile_latex",
        lambda tex, compiler: CompileResult("compilation_failed", compiler="tectonic", log="boom"),
    )
    response = client.post(f"{RESUMES_URL}/{resume_id}/render", json={"template_id": "classic"})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "compilation_failed"
    assert body["log"] == "boom"
    assert body["pdf"] is None
    assert body["tex"]["kind"] == "tex"


def test_render_compile_timeout_is_reported(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.services import rendering

    resume_id = _create(client)
    monkeypatch.setattr(
        rendering, "compile_latex",
        lambda tex, compiler: CompileResult("timeout", compiler="tectonic", log="timed out"),
    )
    response = client.post(f"{RESUMES_URL}/{resume_id}/render", json={"template_id": "classic"})
    assert response.status_code == 200
    assert response.json()["status"] == "timeout"
    assert response.json()["log"] == "timed out"


@pytest.mark.skipif(detect_compiler() is None, reason="no LaTeX compiler installed")
def test_render_produces_downloadable_pdf(client: TestClient) -> None:
    resume_id = _create(client)
    response = client.post(f"{RESUMES_URL}/{resume_id}/render", json={"template_id": "compact"})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "success"
    assert body["pdf"]["kind"] == "pdf"
    assert body["page_count"] >= 1

    download = client.get(body["pdf"]["download_url"])
    assert download.status_code == 200
    assert download.headers["content-type"].startswith("application/pdf")
    assert download.content.startswith(b"%PDF")


def test_overleaf_returns_download_workflow(client: TestClient) -> None:
    resume_id = _create(client)
    response = client.post(f"{RESUMES_URL}/{resume_id}/overleaf", json={"template_id": "modern"})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["method"] == "download"
    assert body["tex"]["kind"] == "tex"
    assert body["note"]
    assert body["instructions"]

    download = client.get(body["tex"]["download_url"])
    assert download.status_code == 200
    assert "\\documentclass" in download.text


def test_overleaf_unknown_template_returns_422(client: TestClient) -> None:
    resume_id = _create(client)
    response = client.post(f"{RESUMES_URL}/{resume_id}/overleaf", json={"template_id": "fancy"})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_template"


def test_artifact_malformed_or_unknown_id_returns_404(client: TestClient) -> None:
    for bad in ("..%2F..%2Fetc%2Fpasswd", "../config.py", "short", "x" * 200):
        response = client.get(f"{ARTIFACTS_URL}/{bad}")
        assert response.status_code == 404, bad
        assert response.json()["error"]["code"] in ("artifact_not_found", "not_found"), bad
    assert client.get(f"{ARTIFACTS_URL}/{'a'*24}").status_code == 404


def test_deleting_resume_deletes_its_artifacts(client: TestClient) -> None:
    resume_id = _create(client)
    rendered = client.post(f"{RESUMES_URL}/{resume_id}/render", json={"template_id": "classic"})
    assert rendered.status_code == 200
    tex_url = rendered.json()["tex"]["download_url"]
    assert client.get(tex_url).status_code == 200

    assert client.delete(f"{RESUMES_URL}/{resume_id}").status_code == 204
    assert client.get(tex_url).status_code == 404


def test_expired_resume_cannot_render(client: TestClient) -> None:
    from datetime import datetime, timedelta

    from app.models.resume import ParsingMetadata, SourceType
    from app.services import store

    resume = store.get_store().create(
        text=COMPLETE_RESUME,
        source_type=SourceType.PASTE,
        metadata=ParsingMetadata(
            source_type=SourceType.PASTE,
            size_bytes=len(COMPLETE_RESUME.encode()),
            parser="test",
            character_count=len(COMPLETE_RESUME),
            word_count=len(COMPLETE_RESUME.split()),
            line_count=len(COMPLETE_RESUME.splitlines()),
        ),
    )
    resume.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    response = client.post(f"{RESUMES_URL}/{resume.id}/render", json={"template_id": "classic"})
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "resume_not_found"