import { useEffect, useState } from "react";
import { ApiError, absoluteArtifactUrl, downloadArtifact, fetchTemplates, prepareOverleaf, renderResume } from "../api/client";
import type {
  OverleafResponse,
  RenderResponse,
  ResumeResponse,
  TemplateInfo,
} from "../types";

interface ExportWorkspaceProps {
  resume: ResumeResponse | null;
}

const FALLBACK_TEMPLATES: TemplateInfo[] = [
  {
    id: "classic",
    name: "Classic",
    description: "A single-column, traditional layout with ruled section headings.",
  },
  {
    id: "compact",
    name: "Compact",
    description: "Tighter spacing and a smaller body size for dense resumes.",
  },
  {
    id: "modern",
    name: "Modern",
    description: "Restrained accent-coloured headings with an ATS-safe single column.",
  },
];

const STATUS_MESSAGES: Record<string, string> = {
  success: "Your PDF was generated successfully.",
  compiler_unavailable: "PDF generation is unavailable because no LaTeX compiler is installed.",
  compilation_failed: "LaTeX compilation failed. Review the log below.",
  timeout: "LaTeX compilation timed out. Try choosing a smaller resume.",
  too_large: "The rendered document is too large to compile safely.",
};

type BusyAction = "render" | "overleaf" | null;

function triggerDownload(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

function Spinner() {
  return (
    <span
      className="h-5 w-5 animate-spin rounded-full border-2 border-brand-600/30 border-t-brand-400"
      aria-hidden="true"
    />
  );
}

function TemplateCard({
  info,
  selected,
  onSelect,
}: {
  info: TemplateInfo;
  selected: boolean;
  onSelect: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onSelect}
      aria-pressed={selected}
      className={`relative rounded-xl p-5 text-left transition-colors ${
        selected
          ? "border-2 border-brand-600 bg-base-elevated shadow-glow"
          : "border border-line bg-base-card hover:border-brand-400/60 hover:bg-brand-50/40"
      }`}
    >
      {selected ? (
        <span className="badge absolute right-4 top-4 bg-brand-gradient text-white">
          Selected
        </span>
      ) : null}
      <h3 className="pr-16 font-display text-base font-semibold text-ink-900">{info.name}</h3>
      <p className="mt-1.5 text-xs leading-relaxed text-ink-500">{info.description}</p>
    </button>
  );
}

function BusyPanel({
  label,
  note,
}: {
  label: string;
  note: string;
}) {
  return (
    <section
      className="card flex flex-col items-center justify-center gap-4 p-12 text-center"
      aria-busy="true"
      role="status"
    >
      <Spinner />
      <div>
        <p className="font-display text-lg font-semibold text-ink-900">{label}</p>
        <p className="mt-1 text-sm text-ink-500">{note}</p>
      </div>
    </section>
  );
}

export function ExportWorkspace({ resume }: ExportWorkspaceProps) {
  const [templates, setTemplates] = useState<TemplateInfo[] | null>(null);
  const [templateId, setTemplateId] = useState("classic");
  const [render, setRender] = useState<RenderResponse | null>(null);
  const [overleaf, setOverleaf] = useState<OverleafResponse | null>(null);
  const [busy, setBusy] = useState<BusyAction>(null);
  const [error, setError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState<"render" | "overleaf">("render");

  useEffect(() => {
    if (!resume) {
      setTemplates(null);
      setRender(null);
      setOverleaf(null);
      setError(null);
      return;
    }
    let active = true;
    fetchTemplates(resume.resume_id)
      .then((list) => {
        if (!active) return;
        setTemplates(list.templates);
        setTemplateId(list.default_template);
      })
      .catch(() => {
        if (active) setTemplates(FALLBACK_TEMPLATES);
      });
    return () => {
      active = false;
    };
  }, [resume]);

  const handleRender = async () => {
    if (!resume) return;
    setBusy("render");
    setAttempt("render");
    setError(null);
    setRender(null);
    setOverleaf(null);
    try {
      setRender(await renderResume(resume.resume_id, templateId));
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : "Rendering failed. Please try again.",
      );
    } finally {
      setBusy(null);
    }
  };

  const handleOverleaf = async () => {
    if (!resume) return;
    setBusy("overleaf");
    setAttempt("overleaf");
    setError(null);
    setOverleaf(null);
    try {
      setOverleaf(await prepareOverleaf(resume.resume_id, templateId));
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : "Preparing Overleaf export failed. Please try again.",
      );
    } finally {
      setBusy(null);
    }
  };

  const handleDownload = async (artifact: RenderResponse["tex"]) => {
    try {
      const { blob, filename } = await downloadArtifact(artifact);
      triggerDownload(blob, filename);
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Download failed. Please try again.",
      );
    }
  };

  if (!resume) {
    return (
      <div className="card mx-auto max-w-2xl p-12 text-center">
        <span className="eyebrow">Export</span>
        <h2 className="mt-2 font-display text-2xl font-semibold tracking-tight text-ink-900">
          Nothing to export yet
        </h2>
        <p className="mx-auto mt-3 max-w-md text-sm leading-relaxed text-ink-600">
          Upload a resume or paste its text on the dashboard, then export your PDF,
          LaTeX source or an Overleaf-ready file.
        </p>
      </div>
    );
  }

  const templateOptions = templates ?? FALLBACK_TEMPLATES;

  const retry = () => {
    if (attempt === "overleaf") {
      void handleOverleaf();
    } else {
      void handleRender();
    }
  };

  return (
    <div className="space-y-10">
      <section>
        <span className="eyebrow">Step 5 · Export</span>
        <h1 className="mt-2 font-display text-3xl font-semibold tracking-tight text-ink-900 sm:text-4xl">
          Export your resume
        </h1>
        <p className="mt-3 max-w-2xl text-sm leading-relaxed text-ink-600">
          Rendered from the resume text with your accepted changes applied, using three
          original single-column LaTeX templates. Every character you see is real generated
          output — no mock previews.
        </p>
      </section>

      <section className="card p-6 sm:p-8" aria-label="Template selection">
        <span className="eyebrow">Template</span>
        <h2 className="mt-1.5 font-display text-xl font-semibold tracking-tight text-ink-900">
          Choose a layout
        </h2>
        <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-3">
          {templateOptions.map((option) => (
            <TemplateCard
              key={option.id}
              info={option}
              selected={templateId === option.id}
              onSelect={() => setTemplateId(option.id)}
            />
          ))}
        </div>

        <div className="mt-6 flex flex-col gap-3 sm:flex-row">
          <button
            type="button"
            className="btn-primary"
            onClick={handleRender}
            disabled={busy !== null}
          >
            {busy === "render" ? (
              <>
                <Spinner />
                Rendering…
              </>
            ) : (
              "Generate PDF"
            )}
          </button>
          <button
            type="button"
            className="btn-secondary"
            onClick={handleOverleaf}
            disabled={busy !== null}
          >
            {busy === "overleaf" ? "Preparing…" : "Prepare for Overleaf"}
          </button>
        </div>
      </section>

      {busy !== null ? (
        busy === "render" ? (
          <BusyPanel
            label="Compiling with LaTeX…"
            note="The first compile can take a few seconds while Tectonic fetches its package bundle."
          />
        ) : (
          <BusyPanel
            label="Preparing your Overleaf file…"
            note="Generating the bundled .tex source for a clean import into Overleaf."
          />
        )
      ) : null}

      {error ? (
        <section className="card border-red-200 p-6" role="alert">
          <h3 className="font-display text-lg font-semibold text-red-700">Export failed</h3>
          <p className="mt-1.5 text-sm leading-relaxed text-ink-600">{error}</p>
          <button type="button" className="btn-secondary mt-4" onClick={retry}>
            Try again
          </button>
        </section>
      ) : null}

      {render ? (() => {
        const pdf = render.status === "success" ? render.pdf : null;
        const failed = render.status !== "success";
        return (
          <section className="card overflow-hidden" aria-label="Render result">
            <div className="flex flex-col gap-4 border-b border-ink-200 p-6 sm:flex-row sm:items-start sm:justify-between sm:p-8">
              <div className="min-w-0">
                <span className="eyebrow">
                  {pdf ? "Generated" : "Compiler status"}
                </span>
                <h2 className="mt-1.5 font-display text-2xl font-semibold tracking-tight text-ink-900">
                  {pdf ? "Your PDF is ready" : STATUS_MESSAGES[render.status]}
                </h2>
                <p className="mt-1.5 text-sm leading-relaxed text-ink-500">
                  Template: {render.template_id}
                  {render.compiler ? ` · compiled with ${render.compiler}` : ""}
                  {render.page_count ? ` · ${render.page_count} page${render.page_count > 1 ? "s" : ""}` : ""}
                </p>
              </div>
              <div className="flex shrink-0 flex-wrap gap-2">
                {pdf ? (
                  <button
                    type="button"
                    className="btn-primary"
                    onClick={() => void handleDownload(pdf)}
                  >
                    Download PDF
                  </button>
                ) : null}
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={() => void handleDownload(render.tex)}
                >
                  Download .tex
                </button>
                <button type="button" className="btn-ghost" onClick={handleRender}>
                  Regenerate
                </button>
              </div>
            </div>

            {failed ? (
              <div className="p-6 sm:p-8">
                {render.message ? (
                  <p className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm leading-relaxed text-amber-900">
                    {render.message}
                  </p>
                ) : null}
                {render.status === "compiler_unavailable" ? (
                  <p className="mt-3 text-sm leading-relaxed text-ink-500">
                    Install a LaTeX engine such as Tectonic, XeLaTeX or pdfLaTeX, or set{" "}
                    <code className="rounded bg-ink-900/[0.05] px-1 py-0.5 font-mono text-xs">
                      RESUMEFIT_LATEX_COMPILER
                    </code>{" "}
                    to its path, then regenerate.
                  </p>
                ) : null}
              </div>
            ) : null}

            {render.log ? (
              <details className="border-t border-ink-200 bg-cream-50 p-6 sm:p-8">
                <summary className="cursor-pointer text-sm font-semibold text-ink-700">
                  Compiler log
                </summary>
                <pre className="mt-3 max-h-72 overflow-auto whitespace-pre-wrap break-words rounded-lg border border-line bg-base-input p-3 font-mono text-xs leading-relaxed text-ink-700">
                  {render.log}
                </pre>
              </details>
            ) : null}

            {pdf ? (
              <div className="border-t border-ink-200 bg-cream-50 p-6 sm:p-8">
                <iframe
                  className="h-[70vh] w-full rounded-xl border border-line bg-white shadow-panel"
                  src={absoluteArtifactUrl(pdf.download_url)}
                  title="Generated PDF preview"
                />
              </div>
            ) : null}
          </section>
        );
      })() : null}

      {overleaf ? (
        <section className="card p-6 sm:p-8" aria-label="Overleaf export">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
            <div className="min-w-0">
              <span className="eyebrow">Overleaf</span>
              <h2 className="mt-1.5 font-display text-2xl font-semibold tracking-tight text-ink-900">
                Import file ready
              </h2>
              <p className="mt-2 max-w-2xl text-sm leading-relaxed text-ink-500">
                {overleaf.note}
              </p>
            </div>
            <button
              type="button"
              className="btn-primary shrink-0"
              onClick={() => void handleDownload(overleaf.tex)}
            >
              Download main.tex
            </button>
          </div>
          <ol className="mt-6 space-y-3">
            {overleaf.instructions.map((instruction, index) => (
              <li key={instruction} className="flex items-start gap-3 text-sm leading-relaxed text-ink-700">
                <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-brand-gradient-soft font-display text-sm font-semibold text-brand-400">
                  {index + 1}
                </span>
                {instruction}
              </li>
            ))}
          </ol>
        </section>
      ) : null}
    </div>
  );
}