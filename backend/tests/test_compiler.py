"""Tests for compiler detection and isolated compilation behaviour."""

from __future__ import annotations

import subprocess
from types import SimpleNamespace

import pytest

from app.config import get_settings
from app.services import compiler
from app.services.compiler import Compiler, compile_latex, detect_compiler
from app.services.parser import parse_resume

from .synthetic import COMPLETE_RESUME


def _sample_tex() -> str:
    from app.services import latex

    return latex.render_template("classic", parse_resume(COMPLETE_RESUME))


def test_detect_none_when_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(get_settings(), "latex_compiler", "none")
    assert detect_compiler() is None


def test_detect_unknown_compiler_returns_none(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(get_settings(), "latex_compiler", "definitely-not-a-compiler")
    monkeypatch.setattr(compiler.shutil, "which", lambda _: None)
    assert detect_compiler() is None


def test_detect_explicit_executable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(get_settings(), "latex_compiler", "pdflatex")
    monkeypatch.setattr(compiler.shutil, "which", lambda name: "/usr/bin/pdflatex")
    found = detect_compiler()
    assert found == Compiler("pdflatex", "/usr/bin/pdflatex")


def test_detect_explicit_path(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(get_settings(), "latex_compiler", "C:/tex/bin/pdflatex.exe")
    monkeypatch.setattr(compiler.Path, "exists", lambda _: True)
    found = detect_compiler()
    assert found is not None and found.path == "C:/tex/bin/pdflatex.exe"


def test_detect_auto_prefers_local_tectonic(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(compiler.shutil, "which", lambda _: None)
    mono_path = compiler.Path("C:/tools/tectonic.exe")
    monkeypatch.setattr(compiler.Path, "exists", lambda self: self == mono_path)
    monkeypatch.setattr(compiler, "_local_tectonic", lambda: Compiler("tectonic", str(mono_path)))
    found = detect_compiler()
    assert found is not None and found.name == "tectonic"


def test_compile_without_compiler_is_unavailable() -> None:
    result = compile_latex(_sample_tex(), None)
    assert result.status == "compiler_unavailable"
    assert result.pdf is None


def test_compile_oversized_source_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(get_settings(), "latex_max_tex_bytes", 100)
    result = compile_latex(_sample_tex(), Compiler("fake", "fake"))
    assert result.status == "too_large"
    assert result.pdf is None


def test_compile_failure_reports_log(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(*args, **kwargs):
        return SimpleNamespace(returncode=1, stdout="! Emergency stop.\nboom", stderr="")

    monkeypatch.setattr(compiler.subprocess, "run", fake_run)
    result = compile_latex(_sample_tex(), Compiler("fake", "fake"))
    assert result.status == "compilation_failed"
    assert result.log is not None and "boom" in result.log


def test_compile_timeout_is_reported(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd="fake", timeout=1)

    monkeypatch.setattr(compiler.subprocess, "run", fake_run)
    result = compile_latex(_sample_tex(), Compiler("fake", "fake"))
    assert result.status == "timeout"


def test_compile_zero_exit_without_pdf_is_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(*args, **kwargs):
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(compiler.subprocess, "run", fake_run)
    result = compile_latex(_sample_tex(), Compiler("fake", "fake"))
    assert result.status == "compilation_failed"


def test_compile_non_pdf_output_is_failure(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    workdir = tmp_path / "job"
    workdir.mkdir(parents=True, exist_ok=True)

    def fake_run(*args, **kwargs):
        (workdir / "resume.pdf").write_bytes(b"not a real pdf")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(compiler.tempfile, "mkdtemp", lambda prefix="": str(workdir))
    monkeypatch.setattr(compiler.subprocess, "run", fake_run)
    result = compile_latex(_sample_tex(), Compiler("fake", "fake"))
    assert result.status == "compilation_failed"


@pytest.mark.skipif(detect_compiler() is None, reason="no LaTeX compiler installed")
def test_real_compile_succeeds_and_is_bounded() -> None:
    result = compile_latex(_sample_tex(), detect_compiler())
    assert result.status == "success"
    assert result.pdf is not None and result.pdf.startswith(b"%PDF")
    assert result.pdf  # non-empty
    assert result.compiler is not None