"""Endpoint tests for POST /api/v1/resumes/{resume_id}/analyze."""

from __future__ import annotations

from fastapi.testclient import TestClient

from .conftest import SAMPLE_RESUME_TEXT
from .synthetic import COMPLETE_RESUME, UNPARSEABLE_TEXT

RESUMES_URL = "/api/v1/resumes"


def _create(client: TestClient, text: str) -> str:
    response = client.post(RESUMES_URL, json={"text": text})
    assert response.status_code == 201, response.text
    return response.json()["resume_id"]


def test_analyze_pasted_text_returns_full_payload(client: TestClient) -> None:
    resume_id = _create(client, COMPLETE_RESUME)
    response = client.post(f"{RESUMES_URL}/{resume_id}/analyze")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["resume_id"] == resume_id
    assert body["status"] == "analyzed"
    assert body["structured_resume"]["basics"]["name"] == "Jordan Rivera"
    assert body["structured_resume"]["basics"]["email"] == "jordan.rivera@example.com"
    assert len(body["structured_resume"]["experience"]) == 1
    assert body["ats_score"]["label"] == "Estimated ATS-readiness score"
    assert 0 <= body["ats_score"]["score"] <= 100
    assert len(body["ats_score"]["breakdown"]) == 18
    assert body["analyzed_at"]


def test_analyze_after_upload_uses_stored_text(client: TestClient, txt_file) -> None:
    name, data, mime = txt_file
    uploaded = client.post(RESUMES_URL, files={"file": (name, data, mime)})
    resume_id = uploaded.json()["resume_id"]

    response = client.post(f"{RESUMES_URL}/{resume_id}/analyze")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["structured_resume"]["basics"]["name"] == "Aisha Khan"
    assert body["structured_resume"]["skills"]["all_skills"]


def test_analyze_sample_resume_reports_known_gaps(client: TestClient) -> None:
    resume_id = _create(client, SAMPLE_RESUME_TEXT)
    body = client.post(f"{RESUMES_URL}/{resume_id}/analyze").json()
    warnings = " ".join(body["parsing_warnings"]).lower()
    assert "phone" in warnings
    assert body["detected_issues"]


def test_analyze_unknown_id_returns_404(client: TestClient) -> None:
    response = client.post(f"{RESUMES_URL}/does-not-exist/analyze")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "resume_not_found"


def test_analyze_unparseable_text_returns_422(client: TestClient) -> None:
    resume_id = _create(client, UNPARSEABLE_TEXT)
    response = client.post(f"{RESUMES_URL}/{resume_id}/analyze")
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "unparseable_resume"


def test_analyze_response_is_deterministic_for_same_text(client: TestClient) -> None:
    first_id = _create(client, COMPLETE_RESUME)
    second_id = _create(client, COMPLETE_RESUME)
    first = client.post(f"{RESUMES_URL}/{first_id}/analyze").json()
    second = client.post(f"{RESUMES_URL}/{second_id}/analyze").json()
    assert first["ats_score"] == second["ats_score"]
    assert first["structured_resume"] == second["structured_resume"]


def test_analyze_does_not_break_deletion(client: TestClient) -> None:
    resume_id = _create(client, COMPLETE_RESUME)
    assert client.post(f"{RESUMES_URL}/{resume_id}/analyze").status_code == 200
    assert client.delete(f"{RESUMES_URL}/{resume_id}").status_code == 204
    assert client.post(f"{RESUMES_URL}/{resume_id}/analyze").status_code == 404
