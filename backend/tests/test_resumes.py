"""Resume endpoint tests: upload, paste, validation and deletion."""

from __future__ import annotations

from fastapi.testclient import TestClient

from .conftest import SAMPLE_RESUME_TEXT, build_scanned_pdf

RESUMES_URL = "/api/v1/resumes"
MAX_BYTES = 5 * 1024 * 1024


def _post_file(client: TestClient, file: tuple[str, bytes, str]) -> object:
    name, data, mime = file
    return client.post(RESUMES_URL, files={"file": (name, data, mime)})


# --- Successful uploads ---------------------------------------------------


def test_upload_txt_succeeds(client: TestClient, txt_file) -> None:
    response = _post_file(client, txt_file)
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "processed"
    assert "Aisha Khan" in body["extracted_text"]
    assert body["metadata"]["source_type"] == "upload"
    assert body["metadata"]["filename"] == "aisha_resume.txt"
    assert body["metadata"]["parser"] == "plain-text"
    assert body["metadata"]["word_count"] > 0
    assert body["resume_id"]


def test_upload_docx_succeeds(client: TestClient, docx_file) -> None:
    response = _post_file(client, docx_file)
    assert response.status_code == 201, response.text
    body = response.json()
    assert "Student Management System" in body["extracted_text"]
    assert body["metadata"]["parser"] == "python-docx"


def test_upload_pdf_succeeds(client: TestClient, pdf_file) -> None:
    response = _post_file(client, pdf_file)
    assert response.status_code == 201, response.text
    body = response.json()
    assert "Aisha Khan" in body["extracted_text"]
    assert body["metadata"]["parser"] == "pdfplumber"
    assert body["metadata"]["page_count"] == 1


def test_paste_text_as_json_succeeds(client: TestClient) -> None:
    response = client.post(RESUMES_URL, json={"text": SAMPLE_RESUME_TEXT})
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["metadata"]["source_type"] == "paste"
    assert body["metadata"]["filename"] is None
    assert "Python, SQL, HTML, CSS" in body["extracted_text"]


def test_paste_text_as_form_succeeds(client: TestClient) -> None:
    response = client.post(RESUMES_URL, data={"text": SAMPLE_RESUME_TEXT})
    assert response.status_code == 201, response.text
    assert response.json()["metadata"]["source_type"] == "paste"


def test_resume_id_is_opaque_and_unpredictable(client: TestClient) -> None:
    first = client.post(RESUMES_URL, json={"text": SAMPLE_RESUME_TEXT}).json()["resume_id"]
    second = client.post(RESUMES_URL, json={"text": SAMPLE_RESUME_TEXT}).json()["resume_id"]
    assert first != second
    assert len(first) >= 20


# --- Validation failures --------------------------------------------------


def test_empty_paste_is_rejected(client: TestClient) -> None:
    response = client.post(RESUMES_URL, json={"text": ""})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "empty_resume"


def test_whitespace_only_paste_is_rejected(client: TestClient) -> None:
    response = client.post(RESUMES_URL, json={"text": "    \n\t  "})
    assert response.status_code == 422


def test_missing_input_is_rejected(client: TestClient) -> None:
    response = client.post(RESUMES_URL, json={"not_text": "hello"})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_request"


def test_empty_file_is_rejected(client: TestClient) -> None:
    response = client.post(
        RESUMES_URL,
        files={"file": ("empty.txt", b"", "text/plain")},
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "empty_resume"


def test_oversized_file_is_rejected(client: TestClient) -> None:
    payload = b"A" * (MAX_BYTES + 1)
    response = client.post(
        RESUMES_URL,
        files={"file": ("big.txt", payload, "text/plain")},
    )
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "file_too_large"


def test_unsupported_extension_is_rejected(client: TestClient) -> None:
    response = client.post(
        RESUMES_URL,
        files={"file": ("malware.exe", b"MZ\x90\x00\x03", "application/octet-stream")},
    )
    assert response.status_code == 415
    assert response.json()["error"]["code"] == "unsupported_file_type"


def test_content_does_not_match_extension(client: TestClient) -> None:
    # A text body behind a .pdf filename must not be trusted.
    response = client.post(
        RESUMES_URL,
        files={"file": ("fake.pdf", b"just plain text here", "application/pdf")},
    )
    assert response.status_code == 415
    assert response.json()["error"]["code"] == "invalid_content"


def test_scanned_pdf_reports_missing_ocr(client: TestClient) -> None:
    response = client.post(
        RESUMES_URL,
        files={"file": ("scan.pdf", build_scanned_pdf(), "application/pdf")},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "ocr_not_supported"


def test_both_file_and_text_is_rejected(client: TestClient, txt_file) -> None:
    name, data, mime = txt_file
    response = client.post(
        RESUMES_URL,
        files={"file": (name, data, mime)},
        data={"text": SAMPLE_RESUME_TEXT},
    )
    assert response.status_code == 400


# --- Retrieval & deletion -------------------------------------------------


def test_get_resume_round_trips(client: TestClient) -> None:
    created = client.post(RESUMES_URL, json={"text": SAMPLE_RESUME_TEXT}).json()
    fetched = client.get(f"{RESUMES_URL}/{created['resume_id']}")
    assert fetched.status_code == 200
    assert fetched.json()["extracted_text"] == created["extracted_text"]


def test_delete_nonexistent_resume_returns_404(client: TestClient) -> None:
    response = client.delete(f"{RESUMES_URL}/does-not-exist")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "resume_not_found"


def test_delete_existing_resume_succeeds(client: TestClient) -> None:
    resume_id = client.post(RESUMES_URL, json={"text": SAMPLE_RESUME_TEXT}).json()["resume_id"]

    deleted = client.delete(f"{RESUMES_URL}/{resume_id}")
    assert deleted.status_code == 204

    assert client.get(f"{RESUMES_URL}/{resume_id}").status_code == 404
    assert client.delete(f"{RESUMES_URL}/{resume_id}").status_code == 404
