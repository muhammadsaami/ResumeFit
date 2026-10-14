"""Tests for template registration, escaping and LaTeX rendering."""

from __future__ import annotations

import io

import pytest
from pypdf import PdfReader

from app.services import latex
from app.services.compiler import compile_latex, detect_compiler
from app.services.parser import parse_resume

from .synthetic import COMPLETE_RESUME, MISSING_SECTIONS_RESUME

ALL_TEMPLATES = ("classic", "compact", "modern")

_ESCAPE_RESUME = (
    "Test Person\n"
    "test@example.com\n"
    "\n"
    "Summary:\n"
    "C++ & Rust 100% #1 _score_ {braces} \\backslash ~tilde ^caret <less> >greater $cost\n"
    "\n"
    "Skills:\n"
    "C++, SQL\n"
)

_UNICODE_RESUME = (
    "José Müller\n"
    "jose@example.com\n"
    "\n"
    "Summary:\n"
    "고객 지원 및 네트워크 & 연동. 日本語 OK.\n"
    "\n"
    "Skills:\n"
    "Python, 日本語\n"
)


@pytest.mark.parametrize("template_id", ALL_TEMPLATES)
def test_all_templates_render_tex_source(template_id: str) -> None:
    tex = latex.render_template(template_id, parse_resume(COMPLETE_RESUME))
    assert tex.startswith("\\documentclass")
    assert "\\begin{document}" in tex
    assert "\\end{document}" in tex
    assert "Jordan Rivera" in tex
    assert "jordan.rivera@example.com" in tex
    assert "Portfolio Tracker" in tex
    assert "postgresql" in tex.lower()


def test_render_escapes_special_characters() -> None:
    tex = latex.render_template("classic", parse_resume(_ESCAPE_RESUME))
    for escaped in (
        r"\&",
        r"\%",
        r"\$",
        r"\#",
        r"\_",
        r"\{",
        r"\}",
        r"\textbackslash{}",
        r"\textasciitilde{}",
        r"\textasciicircum{}",
        r"\textless{}",
        r"\textgreater{}",
    ):
        assert escaped in tex, f"missing escape {escaped!r}"


def test_user_latex_commands_are_not_executable() -> None:
    resume = _ESCAPE_RESUME.replace("\\backslash", "\\usepackage{evil}")
    tex = latex.render_template("classic", parse_resume(resume))
    assert "\\usepackage{evil}" not in tex
    assert "\\textbackslash{}usepackage\\{evil\\}" in tex


def test_render_preserves_unicode() -> None:
    tex = latex.render_template("compact", parse_resume(_UNICODE_RESUME))
    assert "José Müller" in tex
    assert "日本語" in tex
    assert "고객" in tex


@pytest.mark.parametrize("template_id", ALL_TEMPLATES)
def test_missing_sections_render_empty_template(template_id: str) -> None:
    tex = latex.render_template(template_id, parse_resume(MISSING_SECTIONS_RESUME))
    assert tex.startswith("\\documentclass")
    assert "\\end{document}" in tex


def test_latex_escape_mapping() -> None:
    assert latex.latex_escape("a&b%c$d#e_f{g}h\\i~j^k<l>m") == (
        "a\\&b\\%c\\$d\\#e\\_f\\{g\\}h\\textbackslash{}i"
        "\\textasciitilde{}j\\textasciicircum{}k\\textless{}l\\textgreater{}m"
    )
    assert latex.latex_escape(None) == ""
    assert latex.latex_escape(123) == "123"


def test_pdf_escape_strips_latex_syntax() -> None:
    assert latex.pdf_escape("A & B {x} 100% \\done") == "A and B x 100 done"
    assert latex.pdf_escape(None) == ""


def test_unknown_template_raises() -> None:
    with pytest.raises(KeyError):
        latex.validate_template("nonexistent")
    with pytest.raises(KeyError):
        latex.render_template("nonexistent", parse_resume(COMPLETE_RESUME))


def test_list_templates_contains_all_and_default() -> None:
    ids = {template.id for template in latex.list_templates()}
    assert ids == set(ALL_TEMPLATES)
    assert latex.DEFAULT_TEMPLATE == "classic"


@pytest.mark.skipif(detect_compiler() is None, reason="no LaTeX compiler installed")
@pytest.mark.parametrize("template_id", ALL_TEMPLATES)
def test_real_templates_compile_to_pdf(template_id: str) -> None:
    tex = latex.render_template(template_id, parse_resume(COMPLETE_RESUME))
    result = compile_latex(tex, detect_compiler())
    assert result.status == "success", result.log
    assert result.pdf is not None and result.pdf.startswith(b"%PDF")
    assert result.page_count == 1


@pytest.mark.skipif(detect_compiler() is None, reason="no LaTeX compiler installed")
def test_compiled_pdf_is_readable_by_pypdf() -> None:
    tex = latex.render_template("classic", parse_resume(COMPLETE_RESUME))
    result = compile_latex(tex, detect_compiler())
    assert result.status == "success"
    assert result.pdf is not None
    reader = PdfReader(io.BytesIO(result.pdf))
    assert len(reader.pages) == 1
    assert reader.pages[0].extract_text().strip()