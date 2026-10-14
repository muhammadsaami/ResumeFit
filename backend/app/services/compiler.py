"""Detection and isolated execution of a LaTeX compiler.

Compilation runs in a fresh temporary directory that contains only the generated
``.tex`` file. Untrusted input is never executed: content is escaped before it
reaches the document, ``-no-shell-escape`` is enforced for classic engines and
``--untrusted`` for Tectonic, and timeouts plus size ceilings bound the run.

Windows does not expose POSIX rlimits; resource containment here is time-based
and size-based. For production, run the process under an OS-level sandbox.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from ..config import get_settings


@dataclass(frozen=True)
class Compiler:
    name: str
    path: str


@dataclass
class CompileResult:
    status: str  # success | compiler_unavailable | compilation_failed | timeout | too_large
    pdf: bytes | None = None
    compiler: str | None = None
    page_count: int | None = None
    log: str | None = None


def _local_tectonic() -> Compiler | None:
    """Prefer a repo-local Tectonic binary so no system install is required."""
    candidates = [
        shutil.which("tectonic"),
        str(Path(__file__).resolve().parents[2] / ".tools" / "tectonic" / "tectonic.exe"),
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return Compiler("tectonic", candidate)
    return None


def detect_compiler() -> Compiler | None:
    """Resolve the configured compiler, or ``None`` when none is available."""
    setting = get_settings().latex_compiler.strip()
    if not setting or setting.lower() == "none":
        return None

    if setting.lower() != "auto":
        if Path(setting).exists():
            return Compiler(Path(setting).stem, setting)
        path = shutil.which(setting)
        if path:
            return Compiler(setting, path)
        return None

    tectonic = _local_tectonic()
    if tectonic:
        return tectonic
    for name in ("xelatex", "pdflatex"):
        path = shutil.which(name)
        if path:
            return Compiler(name, path)
    return None


def _truncate_log(log: str | None, limit: int) -> str | None:
    if not log:
        return None
    log = log.strip()
    if len(log) <= limit:
        return log
    return "...\n" + log[-limit:]


def _page_count(pdf_bytes: bytes) -> int | None:
    try:
        from io import BytesIO

        from pypdf import PdfReader

        return len(PdfReader(BytesIO(pdf_bytes)).pages)
    except Exception:
        return None


def compile_latex(tex_source: str, compiler: Compiler | None) -> CompileResult:
    """Compile ``tex_source`` into PDF bytes inside an isolated directory."""
    settings = get_settings()
    if compiler is None:
        return CompileResult("compiler_unavailable")

    if len(tex_source.encode("utf-8")) > settings.latex_max_tex_bytes:
        return CompileResult("too_large", compiler=compiler.name)

    workdir = Path(tempfile.mkdtemp(prefix="resumefit_tex_"))
    tex_path = workdir / "resume.tex"
    tex_path.write_text(tex_source, encoding="utf-8")
    try:
        if compiler.name == "tectonic":
            command = [
                compiler.path,
                "--untrusted",
                "--chatter",
                "minimal",
                "-o",
                str(workdir),
                str(tex_path),
            ]
            if settings.latex_only_cached:
                command.insert(2, "--only-cached")
        else:
            command = [
                compiler.path,
                "-no-shell-escape",
                "-halt-on-error",
                "-interaction=nonstopmode",
                "-file-line-error",
                f"-output-directory={workdir}",
                str(tex_path),
            ]

        env = dict(os.environ)
        env["TEXMFOUTPUT"] = str(workdir)
        env["openin_any"] = "p"
        env["openout_any"] = "p"

        try:
            proc = subprocess.run(
                command,
                cwd=str(workdir),
                env=env,
                capture_output=True,
                text=True,
                timeout=settings.latex_timeout_seconds,
                shell=False,
            )
        except subprocess.TimeoutExpired:
            return CompileResult(
                "timeout",
                compiler=compiler.name,
                log=_truncate_log("Compilation timed out.", settings.latex_max_log_chars),
            )

        log = _truncate_log(
            (proc.stdout or "") + "\n" + (proc.stderr or ""), settings.latex_max_log_chars
        )
        pdf_path = workdir / "resume.pdf"
        if proc.returncode != 0 or not pdf_path.exists():
            return CompileResult("compilation_failed", compiler=compiler.name, log=log)

        pdf_bytes = pdf_path.read_bytes()
        if (
            len(pdf_bytes) > settings.latex_max_pdf_bytes
            or not pdf_bytes.startswith(b"%PDF")
        ):
            return CompileResult(
                "compilation_failed",
                compiler=compiler.name,
                log=_truncate_log(
                    "Produced file is not a valid PDF.", settings.latex_max_log_chars
                ),
            )

        return CompileResult(
            "success",
            pdf=pdf_bytes,
            compiler=compiler.name,
            page_count=_page_count(pdf_bytes),
        )
    finally:
        shutil.rmtree(workdir, ignore_errors=True)