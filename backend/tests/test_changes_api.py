"""Endpoint tests for auto-fix, tailoring and change review."""

from __future__ import annotations

from fastapi.testclient import TestClient

from .conftest import SAMPLE_RESUME_TEXT
from .synthetic import ALIAS_RESUME, COMPLETE_RESUME, DUPLICATE_SKILLS_RESUME

RESUMES_URL = "/api/v1/resumes"

JOB_DESCRIPTION = (
    "We need a backend engineer with Python and PostgreSQL experience. "
    "Docker is essential and Kubernetes is a plus."
)
DOCKER_FIRST_JD = "Docker Docker Docker and Python backend engineering positions available now."


def _create(client: TestClient, text: str) -> str:
    response = client.post(RESUMES_URL, json={"text": text})
    assert response.status_code == 201, response.text
    return response.json()["resume_id"]


def _first_replace(changes: list[dict]) -> dict:
    return next(c for c in changes if c["action"] == "replace" and c["applicable"])


def _first_flag(changes: list[dict]) -> dict:
    return next(c for c in changes if c["action"] == "flag")


def test_change_list_returns_summary_and_effective_analysis(client: TestClient) -> None:
    resume_id = _create(client, COMPLETE_RESUME)
    response = client.get(f"{RESUMES_URL}/{resume_id}/changes")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["resume_id"] == resume_id
    assert body["summary"]["total"] == len(body["changes"])
    assert all(change["status"] == "proposed" for change in body["changes"])
    assert body["effective_analysis"]["ats_score"]["score"] >= 0


def test_accept_replace_change_updates_status(client: TestClient) -> None:
    resume_id = _create(client, DUPLICATE_SKILLS_RESUME)
    changes = client.get(f"{RESUMES_URL}/{resume_id}/changes").json()["changes"]
    change = _first_replace(changes)

    response = client.post(f"{RESUMES_URL}/{resume_id}/changes/{change['id']}/accept")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["applied"] is True
    assert body["change"]["status"] == "accepted"
    assert body["effective_analysis"]["ats_score"]["score"] >= 0

    refreshed = client.get(f"{RESUMES_URL}/{resume_id}/changes").json()
    accepted = next(c for c in refreshed["changes"] if c["id"] == change["id"])
    assert accepted["status"] == "accepted"
    assert refreshed["summary"]["accepted"] >= 1


def test_accepting_same_change_twice_is_idempotent(client: TestClient) -> None:
    resume_id = _create(client, DUPLICATE_SKILLS_RESUME)
    changes = client.get(f"{RESUMES_URL}/{resume_id}/changes").json()["changes"]
    change = _first_replace(changes)
    url = f"{RESUMES_URL}/{resume_id}/changes/{change['id']}/accept"
    assert client.post(url).status_code == 200
    assert client.post(url).json()["change"]["status"] == "accepted"


def test_reject_flag_change_preserves_text(client: TestClient) -> None:
    resume_id = _create(client, SAMPLE_RESUME_TEXT)
    changes = client.get(f"{RESUMES_URL}/{resume_id}/changes").json()["changes"]
    change = _first_flag(changes)

    response = client.post(f"{RESUMES_URL}/{resume_id}/changes/{change['id']}/reject")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["applied"] is False
    assert body["change"]["status"] == "rejected"


def test_accepting_a_flag_is_rejected(client: TestClient) -> None:
    resume_id = _create(client, SAMPLE_RESUME_TEXT)
    changes = client.get(f"{RESUMES_URL}/{resume_id}/changes").json()["changes"]
    change = _first_flag(changes)

    response = client.post(f"{RESUMES_URL}/{resume_id}/changes/{change['id']}/accept")
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "change_not_applicable"


def test_unknown_change_id_returns_404(client: TestClient) -> None:
    resume_id = _create(client, COMPLETE_RESUME)
    response = client.post(f"{RESUMES_URL}/{resume_id}/changes/chg_missing/accept")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "change_not_found"


def test_edit_replace_change_stores_user_text(client: TestClient) -> None:
    resume_id = _create(client, ALIAS_RESUME)
    changes = client.get(f"{RESUMES_URL}/{resume_id}/changes").json()["changes"]
    change = _first_replace(changes)
    edited = "Reworked wording supplied by the user"

    response = client.post(
        f"{RESUMES_URL}/{resume_id}/changes/{change['id']}/edit",
        json={"proposed_text": edited},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["applied"] is False
    assert body["change"]["user_edited"] is True
    assert body["change"]["proposed_text"] == edited
    assert body["change"]["status"] == "proposed"
    assert body["change"]["original_text"] == change["original_text"]

    refreshed = client.get(f"{RESUMES_URL}/{resume_id}/changes").json()["changes"]
    stored = next(c for c in refreshed if c["id"] == change["id"])
    assert stored["proposed_text"] == edited
    assert stored["user_edited"] is True


def test_accepting_edited_change_applies_the_edit(client: TestClient) -> None:
    resume_id = _create(client, ALIAS_RESUME)
    changes = client.get(f"{RESUMES_URL}/{resume_id}/changes").json()["changes"]
    change = _first_replace(changes)
    edited = "Edited heading text"

    client.post(
        f"{RESUMES_URL}/{resume_id}/changes/{change['id']}/edit",
        json={"proposed_text": edited},
    )
    accepted = client.post(f"{RESUMES_URL}/{resume_id}/changes/{change['id']}/accept")
    assert accepted.status_code == 200, accepted.text
    body = accepted.json()
    assert body["change"]["status"] == "accepted"
    assert body["change"]["proposed_text"] == edited
    assert body["change"]["user_edited"] is True


def test_edit_flag_is_rejected(client: TestClient) -> None:
    resume_id = _create(client, SAMPLE_RESUME_TEXT)
    changes = client.get(f"{RESUMES_URL}/{resume_id}/changes").json()["changes"]
    change = _first_flag(changes)
    response = client.post(
        f"{RESUMES_URL}/{resume_id}/changes/{change['id']}/edit",
        json={"proposed_text": "anything"},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "change_not_editable"


def test_edit_empty_text_is_rejected(client: TestClient) -> None:
    resume_id = _create(client, ALIAS_RESUME)
    changes = client.get(f"{RESUMES_URL}/{resume_id}/changes").json()["changes"]
    change = _first_replace(changes)
    response = client.post(
        f"{RESUMES_URL}/{resume_id}/changes/{change['id']}/edit",
        json={"proposed_text": "   "},
    )
    assert response.status_code == 422


def test_editing_an_accepted_change_is_rejected(client: TestClient) -> None:
    resume_id = _create(client, ALIAS_RESUME)
    changes = client.get(f"{RESUMES_URL}/{resume_id}/changes").json()["changes"]
    change = _first_replace(changes)
    accepted = client.post(f"{RESUMES_URL}/{resume_id}/changes/{change['id']}/accept")
    assert accepted.status_code == 200
    response = client.post(
        f"{RESUMES_URL}/{resume_id}/changes/{change['id']}/edit",
        json={"proposed_text": "late edit"},
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "change_already_applied"


def test_tailor_reports_match_percentage(client: TestClient) -> None:
    resume_id = _create(client, COMPLETE_RESUME)
    response = client.post(
        f"{RESUMES_URL}/{resume_id}/tailor", json={"job_description": JOB_DESCRIPTION}
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert 0.0 <= body["match_percentage"] <= 100.0
    assert body["match_note"]


def test_changes_unknown_resume_returns_404(client: TestClient) -> None:
    response = client.get(f"{RESUMES_URL}/does-not-exist/changes")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "resume_not_found"


def test_tailor_reports_matched_and_missing_skills(client: TestClient) -> None:
    resume_id = _create(client, COMPLETE_RESUME)
    response = client.post(
        f"{RESUMES_URL}/{resume_id}/tailor", json={"job_description": JOB_DESCRIPTION}
    )
    assert response.status_code == 200, response.text
    body = response.json()
    matched = {match["canonical"] for match in body["matched_skills"]}
    missing = {match["canonical"] for match in body["missing_skills"]}
    assert "python" in matched
    assert "postgresql" in matched
    assert "kubernetes" in missing
    assert not (matched & missing)
    assert body["changes"]["effective_analysis"]["ats_score"]["score"] >= 0
    assert body["explanations"]


def test_tailor_short_job_description_is_rejected(client: TestClient) -> None:
    resume_id = _create(client, COMPLETE_RESUME)
    response = client.post(
        f"{RESUMES_URL}/{resume_id}/tailor", json={"job_description": "too short"}
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_tailor_unknown_resume_returns_404(client: TestClient) -> None:
    response = client.post(
        f"{RESUMES_URL}/does-not-exist/tailor", json={"job_description": JOB_DESCRIPTION}
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "resume_not_found"


def test_accept_skill_ordering_after_tailoring(client: TestClient) -> None:
    resume_id = _create(client, COMPLETE_RESUME)
    tailored = client.post(
        f"{RESUMES_URL}/{resume_id}/tailor", json={"job_description": DOCKER_FIRST_JD}
    )
    assert tailored.status_code == 200, tailored.text
    ordering = next(
        change
        for change in tailored.json()["changes"]["changes"]
        if change["category"] == "skill_ordering"
    )
    assert ordering["proposed_text"].startswith("Docker")

    accepted = client.post(
        f"{RESUMES_URL}/{resume_id}/changes/{ordering['id']}/accept"
    )
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["change"]["status"] == "accepted"

    rejected = client.post(
        f"{RESUMES_URL}/{resume_id}/changes/{ordering['id']}/reject"
    )
    assert rejected.status_code == 200, rejected.text
    assert rejected.json()["change"]["status"] == "rejected"
    assert rejected.json()["applied"] is False


def test_change_ids_are_deterministic_across_resumes(client: TestClient) -> None:
    first_id = _create(client, COMPLETE_RESUME)
    second_id = _create(client, COMPLETE_RESUME)
    first = client.get(f"{RESUMES_URL}/{first_id}/changes").json()["changes"]
    second = client.get(f"{RESUMES_URL}/{second_id}/changes").json()["changes"]
    assert [c["id"] for c in first] == [c["id"] for c in second]


def test_tailor_does_not_mutate_original_analysis_contract(client: TestClient) -> None:
    resume_id = _create(client, COMPLETE_RESUME)
    before = client.post(f"{RESUMES_URL}/{resume_id}/analyze").json()
    client.post(f"{RESUMES_URL}/{resume_id}/tailor", json={"job_description": JOB_DESCRIPTION})
    after = client.post(f"{RESUMES_URL}/{resume_id}/analyze").json()
    assert before["ats_score"] == after["ats_score"]
    assert before["structured_resume"] == after["structured_resume"]
