import { useState } from "react";
import { ApiError, tailorResume } from "../api/client";
import type { KeywordMatch, TailorResponse } from "../types";

interface TailorPanelProps {
  resumeId: string;
  initialJobDescription: string;
  tailor: TailorResponse | null;
  onTailored: (result: TailorResponse) => void;
  onNavigate: (line: number) => void;
}

const MIN_JOB_DESCRIPTION_CHARS = 30;

function MatchChips({
  matches,
  tone,
  onNavigate,
}: {
  matches: KeywordMatch[];
  tone: "matched" | "missing" | "supported";
  onNavigate: (line: number) => void;
}) {
  if (matches.length === 0) {
    return <p className="text-sm text-ink-400">None.</p>;
  }
  const toneClass =
    tone === "matched"
      ? "bg-emerald-50 text-emerald-700"
      : tone === "missing"
        ? "bg-amber-50 text-amber-800"
        : "border border-emerald-300 bg-base-card text-emerald-700";
  return (
    <div className="flex flex-wrap gap-1.5">
      {matches.map((match) => {
        const evidence = match.evidence[0];
        const label = `${match.term}${match.occurrences_in_job > 1 ? ` ×${match.occurrences_in_job}` : ""}`;
        if (!evidence) {
          return (
            <span key={`${tone}-${match.canonical}-${match.term}`} className={`badge ${toneClass}`}>
              {label}
            </span>
          );
        }
        return (
          <button
            key={`${tone}-${match.canonical}-${match.term}`}
            type="button"
            className={`badge ${toneClass} underline-offset-2 hover:underline`}
            title={`Line ${evidence.line}: ${evidence.text}`}
            onClick={() => onNavigate(evidence.line)}
          >
            {label}
          </button>
        );
      })}
    </div>
  );
}

function MatchMeter({ tailor }: { tailor: TailorResponse }) {
  const pct = Math.max(0, Math.min(tailor.match_percentage, 100));
  const barColor =
    pct >= 70 ? "bg-emerald-500" : pct >= 40 ? "bg-amber-500" : "bg-red-500";
  return (
    <div className="rounded-xl border border-ink-200 bg-cream-50 p-4">
      <div className="flex items-baseline justify-between gap-3">
        <span className="text-xs font-semibold uppercase tracking-wide text-ink-500">
          Job-description match
        </span>
        <span className="font-display text-2xl font-semibold text-ink-900 tabular-nums">
          {pct.toFixed(pct % 1 === 0 ? 0 : 1)}%
        </span>
      </div>
      <span className="mt-2 block h-2 overflow-hidden rounded-full bg-ink-200/70" role="presentation">
        <span className={`block h-full rounded-full ${barColor}`} style={{ width: `${pct}%` }} />
      </span>
      {tailor.match_note ? (
        <p className="mt-2 text-xs leading-relaxed text-ink-500">{tailor.match_note}</p>
      ) : null}
    </div>
  );
}

export function TailorPanel({
  resumeId,
  initialJobDescription,
  tailor,
  onTailored,
  onNavigate,
}: TailorPanelProps) {
  const [text, setText] = useState(initialJobDescription);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const trimmedLength = text.trim().length;
  const tooShort = trimmedLength > 0 && trimmedLength < MIN_JOB_DESCRIPTION_CHARS;

  const submit = async () => {
    if (trimmedLength < MIN_JOB_DESCRIPTION_CHARS) return;
    setLoading(true);
    setError(null);
    try {
      onTailored(await tailorResume(resumeId, text));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Tailoring failed. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="card p-6 sm:p-8" aria-label="Job-description tailoring">
      <span className="eyebrow">Step 4 · Tailoring</span>
      <h2 className="mt-1.5 font-display text-2xl font-semibold tracking-tight text-ink-900">
        Job-description match
      </h2>
      <p className="mt-2 max-w-3xl text-sm leading-relaxed text-ink-500">
        Paste the target job description. Matching is local and rule-based; skills you do not
        have are reported for your review but are never added to your resume without your
        explicit decision.
      </p>

      <label className="label mt-5" htmlFor="job-description-input">
        Target job description
      </label>
      <textarea
        id="job-description-input"
        className="input min-h-32 resize-y font-mono text-xs leading-relaxed"
        value={text}
        onChange={(event) => setText(event.target.value)}
        placeholder="Paste the job description here..."
      />
      <div className="mt-2 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <span className={tooShort ? "text-xs text-red-600" : "text-xs text-ink-400"}>
          {tooShort
            ? `Add at least ${MIN_JOB_DESCRIPTION_CHARS - trimmedLength} more characters.`
            : `${trimmedLength} characters`}
        </span>
        <button
          type="button"
          className="btn-primary"
          onClick={() => void submit()}
          disabled={loading || trimmedLength < MIN_JOB_DESCRIPTION_CHARS}
        >
          {loading ? (
            <>
              <span
                className="h-4 w-4 animate-spin rounded-full border-2 border-white/40 border-t-white"
                aria-hidden="true"
              />
              Matching…
            </>
          ) : (
            "Match against resume"
          )}
        </button>
      </div>

      {error ? (
        <div
          className="mt-4 flex items-center justify-between gap-3 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
          role="alert"
        >
          <span>{error}</span>
          <button type="button" className="btn-secondary" onClick={() => void submit()}>
            Retry
          </button>
        </div>
      ) : null}

      {tailor ? (
        <div className="mt-6 space-y-6">
          <MatchMeter tailor={tailor} />

          <dl className="grid grid-cols-3 gap-3">
            <div className="stat-card">
              <dt className="text-[0.7rem] font-semibold uppercase tracking-wide text-ink-500">
                Words
              </dt>
              <dd className="mt-1 font-display text-base font-semibold text-ink-800">
                {tailor.job_description_stats.word_count}
              </dd>
            </div>
            <div className="stat-card">
              <dt className="text-[0.7rem] font-semibold uppercase tracking-wide text-ink-500">
                Unique terms
              </dt>
              <dd className="mt-1 font-display text-base font-semibold text-ink-800">
                {tailor.job_description_stats.unique_terms}
              </dd>
            </div>
            <div className="stat-card">
              <dt className="text-[0.7rem] font-semibold uppercase tracking-wide text-ink-500">
                Skills matched
              </dt>
              <dd className="mt-1 font-display text-base font-semibold text-ink-800">
                {tailor.matched_skills.length}
              </dd>
            </div>
          </dl>

          {tailor.explanations.length > 0 ? (
            <ul className="space-y-1.5 rounded-xl border border-ink-200 bg-cream-50 px-4 py-3 text-xs leading-relaxed text-ink-600">
              {tailor.explanations.map((explanation) => (
                <li key={explanation} className="flex gap-2">
                  <span aria-hidden="true" className="text-brand-400">→</span>
                  {explanation}
                </li>
              ))}
            </ul>
          ) : null}

          <div>
            <h3 className="text-xs font-semibold uppercase tracking-wide text-emerald-700">
              Matched skills
            </h3>
            <p className="mt-0.5 text-xs text-ink-500">
              Requested in the job and present in your resume.
            </p>
            <div className="mt-2">
              <MatchChips matches={tailor.matched_skills} tone="matched" onNavigate={onNavigate} />
            </div>
          </div>

          <div>
            <h3 className="text-xs font-semibold uppercase tracking-wide text-emerald-700">
              Supported in your bullets
            </h3>
            <p className="mt-0.5 text-xs text-ink-500">
              Matched skills you already demonstrate in experience or projects.
            </p>
            <div className="mt-2">
              <MatchChips
                matches={tailor.evidence_backed_skills}
                tone="supported"
                onNavigate={onNavigate}
              />
            </div>

            {tailor.evidence_backed_skills.some((match) => match.evidence[0]) ? (
              <ul className="mt-3 space-y-1.5">
                {tailor.evidence_backed_skills
                  .filter((match) => match.evidence[0])
                  .map((match) => (
                    <li key={`evidence-${match.canonical}`} className="text-xs leading-relaxed">
                      <button
                        type="button"
                        className="text-left text-ink-600 underline-offset-2 hover:underline"
                        onClick={() => onNavigate(match.evidence[0].line)}
                      >
                        <span className="font-semibold text-emerald-700">{match.term}</span>
                        <span className="text-ink-400"> · line {match.evidence[0].line} · </span>
                        <span className="italic">“{match.evidence[0].text}”</span>
                      </button>
                    </li>
                  ))}
              </ul>
            ) : null}
          </div>

          <div>
            <h3 className="text-xs font-semibold uppercase tracking-wide text-amber-700">
              Missing skills
            </h3>
            <p className="mt-0.5 text-xs text-ink-500">
              Requested by the job but absent from your resume. Listed for review only —
              never inserted automatically.
            </p>
            <div className="mt-2">
              <MatchChips matches={tailor.missing_skills} tone="missing" onNavigate={onNavigate} />
            </div>
          </div>

          <div className="grid grid-cols-1 gap-5 sm:grid-cols-2">
            <div>
              <h3 className="text-xs font-semibold uppercase tracking-wide text-ink-500">
                Matched keywords
              </h3>
              <div className="mt-2">
                <MatchChips matches={tailor.matched_keywords} tone="matched" onNavigate={onNavigate} />
              </div>
            </div>
            <div>
              <h3 className="text-xs font-semibold uppercase tracking-wide text-ink-500">
                Missing keywords
              </h3>
              <div className="mt-2">
                <MatchChips matches={tailor.missing_keywords} tone="missing" onNavigate={onNavigate} />
              </div>
            </div>
          </div>
        </div>
      ) : null}
    </section>
  );
}