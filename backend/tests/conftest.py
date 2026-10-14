"""Shared pytest fixtures and sample resume builders.

The sample resume intentionally contains only the facts provided in the
product brief. No employers, metrics, certifications or skills are invented.
"""

from __future__ import annotations

import io

import pytest
from docx import Document
from fastapi.testclient import TestClient

SAMPLE_RESUME_TEXT = (
    "Aisha Khan\n"
    "Email: aisha.example@example.com\n"
    "\n"
    "Education:\n"
    "Bachelor of Computer Applications, 2025\n"
    "\n"
    "Project:\n"
    "Student Management System\n"
    "\n"
    "Skills:\n"
    "Python, SQL, HTML, CSS\n"
    "\n"
    "Experience:\n"
    "Fresher\n"
)

SAMPLE_LINES = [line for line in SAMPLE_RESUME_TEXT.splitlines() if line]


def build_txt() -> bytes:
    return SAMPLE_RESUME_TEXT.encode("utf-8")


def build_docx() -> bytes:
    document = Document()
    for line in SAMPLE_RESUME_TEXT.splitlines():
        document.add_paragraph(line)
    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def build_text_pdf() -> bytes:
    """A simple text-based PDF containing the sample resume."""
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas

    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    _, height = letter
    y = height - 72
    for line in SAMPLE_LINES:
        pdf.drawString(72, y, line)
        y -= 18
    pdf.showPage()
    pdf.save()
    return buffer.getvalue()


def build_scanned_pdf() -> bytes:
    """A structurally valid PDF with no text layer (simulates a scan)."""
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas

    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    pdf.rect(100, 400, 300, 200, fill=1)
    pdf.showPage()
    pdf.save()
    return buffer.getvalue()


@pytest.fixture()
def client() -> TestClient:
    from app.main import create_app

    with TestClient(create_app()) as test_client:
        yield test_client


@pytest.fixture()
def txt_file() -> tuple[str, bytes, str]:
    return ("aisha_resume.txt", build_txt(), "text/plain")


@pytest.fixture()
def docx_file() -> tuple[str, bytes, str]:
    return (
        "aisha_resume.docx",
        build_docx(),
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )


@pytest.fixture()
def pdf_file() -> tuple[str, bytes, str]:
    return ("aisha_resume.pdf", build_text_pdf(), "application/pdf")
