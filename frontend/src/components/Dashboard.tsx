import { useRef, useState, type ChangeEvent, type DragEvent, type FormEvent } from "react";

import type { ConnectionStatus } from "../App";
import { ApiError, createResumeFromFile, createResumeFromText } from "../api/client";
import {
  ALLOWED_EXTENSIONS,
  MAX_UPLOAD_BYTES,
  fileExtension,
  formatBytes,
} from "../lib/format";
import type { ResumeResponse } from "../types";
import { InsightsPanel } from "./InsightsPanel";
import { MetricCards } from "./MetricCards";
import { UploadCloudIcon } from "./icons";

interface DashboardProps {
  onCreated: (resume: ResumeResponse, jobDescription: string) => void;
  connection: ConnectionStatus;
}

type Mode = "upload" | "paste";

function validateFile(file: File): string | null {
  const extension = fileExtension(file.name);
  if (!ALLOWED_EXTENSIONS.includes(extension as (typeof ALLOWED_EXTENSIONS)[number])) {
    return `Unsupported file type "${extension || file.name}". Upload a PDF, DOCX or TXT file.`;
  }
  if (file.size === 0) {
    return "That file is empty. Choose a resume that contains text.";
  }
  if (file.size > MAX_UPLOAD_BYTES) {
    return `That file is ${formatBytes(file.size)}. The maximum size is 5 MB.`;
  }
  return null;
}

export function Dashboard({ onCreated, connection }: DashboardProps) {
  const [mode, setMode] = useState<Mode>("upload");
  const [file, setFile] = useState<File | null>(null);
  const [pasteText, setPasteText] = useState("");
  const [jobDescription, setJobDescription] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [dragActive, setDragActive] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const selectFile = (candidate: File | null) => {
    if (!candidate) {
      setFile(null);
      return;
    }
    const message = validateFile(candidate);
    if (message) {
      setError(message);
      setFile(null);
      return;
    }
    setError(null);
    setFile(candidate);
  };

  const handleFileInput = (event: ChangeEvent<HTMLInputElement>) => {
    selectFile(event.target.files?.[0] ?? null);
  };

  const handleDrop = (event: DragEvent<HTMLLabelElement>) => {
    event.preventDefault();
    setDragActive(false);
    selectFile(event.dataTransfer.files?.[0] ?? null);
  };

  const removeFile = () => {
    setFile(null);
    setError(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);

    if (mode === "upload") {
      if (!file) {
        setError("Choose a PDF, DOCX or TXT resume to analyze.");
        return;
      }
    } else if (pasteText.trim().length < 20) {
      setError("Paste at least a few lines of resume text before analyzing.");
      return;
    }

    setSubmitting(true);
    try {
      const resume =
        mode === "upload"
          ? await createResumeFromFile(file as File)
          : await createResumeFromText(pasteText);
      onCreated(resume, jobDescription.trim());
    } catch (caught) {
      const message =
        caught instanceof ApiError
          ? caught.message
          : "Unexpected error while analyzing the resume. Please try again.";
      setError(message);
    } finally {
      setSubmitting(false);
    }
  };

  const offline = connection === "offline";

  return (
    <div className="space-y-6">
      <section className="max-w-3xl">
        <span className="eyebrow">Parsing · ATS score · Editing · Export</span>
        <h1 className="mt-3 font-display text-3xl font-bold tracking-tight text-ink-900 sm:text-4xl">
          Make your resume job-ready with AI
        </h1>
        <p className="mt-4 max-w-2xl text-base leading-relaxed text-ink-500">
          Upload or paste your resume, add a job description if you have one, and ResumeFit will
          extract its structure and produce a transparent, rule-based ATS-readiness score you can
          inspect check by check.
        </p>
      </section>

      {offline ? (
        <div
          role="alert"
          className="card border-amber-200 bg-amber-50 p-5 text-sm leading-relaxed text-amber-900"
        >
          The ResumeFit backend is not reachable. Start it with{" "}
          <code className="rounded bg-amber-100 px-1.5 py-0.5 font-mono text-xs">
            uvicorn app.main:app --reload --port 8000
          </code>{" "}
          from the <code className="font-mono text-xs">backend</code> folder, then try again.
        </div>
      ) : null}

      <MetricCards analysis={null} tailor={null} proposedCount={null} loading={false} />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <form
          onSubmit={handleSubmit}
          className="card p-6 sm:p-8 lg:col-span-2"
          noValidate
          aria-busy={submitting}
        >
          <fieldset>
            <legend className="label text-base text-ink-700">Add your resume</legend>
            <div className="mb-6 inline-flex rounded-xl border border-line bg-base-elevated p-1">
              {(["upload", "paste"] as Mode[]).map((option) => (
                <button
                  key={option}
                  type="button"
                  onClick={() => {
                    setMode(option);
                    setError(null);
                  }}
                  aria-pressed={mode === option}
                  className={`rounded-lg px-4 py-1.5 text-sm font-semibold transition-colors ${
                    mode === option
                      ? "bg-brand-gradient text-white shadow-[0_6px_18px_rgba(115,87,255,0.35)]"
                      : "text-ink-500 hover:text-ink-900"
                  }`}
                >
                  {option === "upload" ? "Upload file" : "Paste text"}
                </button>
              ))}
            </div>

            {mode === "upload" ? (
              <div>
                <label
                  htmlFor="resume-file"
                  onDragOver={(event) => {
                    event.preventDefault();
                    setDragActive(true);
                  }}
                  onDragLeave={() => setDragActive(false)}
                  onDrop={handleDrop}
                  className={`flex cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed px-6 py-12 text-center transition-colors ${
                    dragActive
                      ? "border-brand-500 bg-brand-50"
                      : "border-line-strong bg-base-elevated/50 hover:border-brand-400/70 hover:bg-brand-50/40"
                  }`}
                >
                  <span className="flex h-12 w-12 items-center justify-center rounded-xl bg-brand-gradient-soft text-brand-400">
                    <UploadCloudIcon className="h-6 w-6" />
                  </span>
                  <span className="mt-4 text-sm font-semibold text-ink-700">
                    Drag a resume here, or click to browse
                  </span>
                  <span className="mt-2 flex flex-wrap items-center justify-center gap-1.5 text-xs text-ink-400">
                    <span className="badge border border-line bg-base-elevated text-ink-600">PDF</span>
                    <span className="badge border border-line bg-base-elevated text-ink-600">DOCX</span>
                    <span className="badge border border-line bg-base-elevated text-ink-600">TXT</span>
                    <span className="ml-1">up to 5 MB</span>
                  </span>
                  <input
                    ref={fileInputRef}
                    id="resume-file"
                    name="resume-file"
                    type="file"
                    accept=".pdf,.docx,.txt"
                    className="sr-only"
                    onChange={handleFileInput}
                  />
                </label>

                {file ? (
                  <div className="mt-4 flex items-center justify-between gap-3 rounded-xl border border-line bg-base-elevated px-4 py-3">
                    <div className="min-w-0">
                      <p className="truncate text-sm font-medium text-ink-800">{file.name}</p>
                      <p className="text-xs text-ink-400">{formatBytes(file.size)} · ready to analyze</p>
                    </div>
                    <button
                      type="button"
                      onClick={removeFile}
                      className="btn-ghost shrink-0 px-3 py-1.5 text-sm text-red-700 hover:bg-red-50"
                      aria-label={`Remove ${file.name}`}
                    >
                      Remove
                    </button>
                  </div>
                ) : null}
              </div>
            ) : (
              <div>
                <label className="label" htmlFor="resume-text">
                  Paste resume text
                </label>
                <textarea
                  id="resume-text"
                  name="resume-text"
                  rows={10}
                  value={pasteText}
                  onChange={(event) => setPasteText(event.target.value)}
                  placeholder={"Paste your full resume here...\n\nInclude your name, contact, education, skills, projects and experience."}
                  className="input font-mono text-xs leading-relaxed"
                />
                <p className="mt-2 text-xs text-ink-400">
                  {pasteText.trim().length} characters entered
                </p>
              </div>
            )}
          </fieldset>

          <div className="mt-7">
            <div className="mb-1.5 flex items-center justify-between">
              <label className="label mb-0" htmlFor="job-description">
                Job description
              </label>
              <span className="text-xs text-ink-400">Optional</span>
            </div>
            <textarea
              id="job-description"
              name="job-description"
              rows={5}
              value={jobDescription}
              onChange={(event) => setJobDescription(event.target.value)}
              placeholder="Paste the job description to tailor your resume against it."
              className="input"
            />
            <p className="mt-2 text-xs leading-relaxed text-ink-400">
              Used for keyword matching and tailoring. Skills the job asks for but your resume
              does not show are reported for review — never added silently.
            </p>
          </div>

          {error ? (
            <p
              role="alert"
              className="mt-6 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm leading-relaxed text-red-700"
            >
              {error}
            </p>
          ) : null}

          <div className="mt-8 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <p className="text-xs leading-relaxed text-ink-400" role="status" aria-live="polite">
              {submitting
                ? "Parsing and analyzing your resume on the server…"
                : "Your resume is parsed on the server and deleted automatically after one hour."}
            </p>
            <button type="submit" className="btn-primary sm:w-auto" disabled={submitting}>
              {submitting ? (
                <>
                  <span
                    className="h-4 w-4 animate-spin rounded-full border-2 border-white/40 border-t-white"
                    aria-hidden="true"
                  />
                  Analyzing…
                </>
              ) : (
                "Analyze Resume"
              )}
            </button>
          </div>
        </form>

        <InsightsPanel analysis={null} tailor={null} />
      </div>
    </div>
  );
}
