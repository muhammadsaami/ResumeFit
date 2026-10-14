import { useMemo } from "react";
import type { AnalysisResponse, KeywordMatch, TailorResponse } from "../types";
import { CheckIcon } from "./icons";

interface InsightsPanelProps {
  analysis: AnalysisResponse | null;
  tailor: TailorResponse | null;
  onViewAll?: () => void;
}

const MAX_CHIPS = 8;

function KeyGroup({
  title,
  tone,
  matches,
  emptyLabel,
}: {
  title: string;
  tone: "matched" | "partial" | "missing";
  matches: KeywordMatch[];
  emptyLabel: string;
}) {
  const toneStyle =
    tone === "matched"
      ? "bg-emerald-50 text-emerald-700"
      : tone === "partial"
        ? "bg-amber-50 text-amber-700"
        : "bg-red-50 text-red-700";
  const shown = matches.slice(0, MAX_CHIPS);
  return (
    <div>
      <div className="flex items-center justify-between gap-2">
        <h4 className="text-xs font-semibold uppercase tracking-wide text-ink-500">{title}</h4>
        <span className={`badge ${toneStyle}`}>{matches.length}</span>
      </div>
      {matches.length === 0 ? (
        <p className="mt-1.5 text-xs text-ink-400">{emptyLabel}</p>
      ) : (
        <div className="mt-2 flex flex-wrap gap-1.5">
          {shown.map((match) => (
            <span key={`${tone}-${match.canonical}-${match.term}`} className={`badge ${toneStyle}`}>
              {match.term}
            </span>
          ))}
          {matches.length > MAX_CHIPS ? (
            <span className="badge border border-line bg-base-elevated text-ink-500">
              +{matches.length - MAX_CHIPS}
            </span>
          ) : null}
        </div>
      )}
    </div>
  );
}

export function InsightsPanel({ analysis, tailor, onViewAll }: InsightsPanelProps) {
  const partial = useMemo(() => {
    if (!tailor) return [] as KeywordMatch[];
    const demonstrated = new Set(tailor.evidence_backed_skills.map((match) => match.canonical));
    return tailor.matched_skills.filter((match) => !demonstrated.has(match.canonical));
  }, [tailor]);

  const summary = analysis?.ats_score.summary;
  const deductions = useMemo(
    () =>
      analysis
        ? analysis.ats_score.breakdown
            .filter((rule) => rule.status !== "passed")
            .sort(
              (a, b) =>
                b.points_max - b.points_earned - (a.points_max - a.points_earned),
            )
            .slice(0, 4)
        : [],
    [analysis],
  );

  return (
    <div className="card p-6">
      <div className="flex items-center justify-between gap-3">
        <h3 className="font-display text-base font-semibold text-ink-900">Insights</h3>
        <span className="badge bg-brand-gradient-soft text-brand-400">Live</span>
      </div>

      <div className="mt-5">
        <h4 className="text-xs font-semibold uppercase tracking-wide text-ink-500">
          ATS score breakdown
        </h4>
        {summary ? (
          <>
            <div className="mt-2 grid grid-cols-3 gap-2 text-center">
              <div className="rounded-lg border border-emerald-200 bg-emerald-50 py-2">
                <p className="font-display text-lg font-bold text-emerald-700">{summary.passed}</p>
                <p className="text-[0.65rem] uppercase tracking-wide text-emerald-700/80">Passed</p>
              </div>
              <div className="rounded-lg border border-amber-200 bg-amber-50 py-2">
                <p className="font-display text-lg font-bold text-amber-700">{summary.warnings}</p>
                <p className="text-[0.65rem] uppercase tracking-wide text-amber-700/80">Warnings</p>
              </div>
              <div className="rounded-lg border border-red-200 bg-red-50 py-2">
                <p className="font-display text-lg font-bold text-red-700">{summary.failed}</p>
                <p className="text-[0.65rem] uppercase tracking-wide text-red-700/80">Failed</p>
              </div>
            </div>
            {deductions.length > 0 ? (
              <ul className="mt-3 space-y-2">
                {deductions.map((rule) => (
                  <li key={rule.rule_id} className="flex items-start gap-2 text-xs">
                    <span
                      className={`mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full ${
                        rule.status === "failed" ? "bg-red-500" : "bg-amber-500"
                      }`}
                      aria-hidden="true"
                    />
                    <span className="min-w-0 flex-1 text-ink-500">{rule.name}</span>
                    <span className="shrink-0 tabular-nums text-ink-400">
                      −{rule.points_max - rule.points_earned}
                    </span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="mt-3 flex items-center gap-1.5 text-xs text-emerald-700">
                <CheckIcon className="h-3.5 w-3.5" /> All checks passed.
              </p>
            )}
          </>
        ) : (
          <p className="mt-1.5 text-xs text-ink-400">No analysis yet.</p>
        )}
      </div>

      <div className="mt-6 space-y-5 border-t border-line pt-5">
        <h4 className="text-xs font-semibold uppercase tracking-wide text-ink-500">
          Keyword match
        </h4>
        {tailor ? (
          <>
            <KeyGroup
              title="Matched"
              tone="matched"
              matches={tailor.evidence_backed_skills}
              emptyLabel="No demonstrated job skills yet."
            />
            <KeyGroup
              title="Partial"
              tone="partial"
              matches={partial}
              emptyLabel="No partial matches."
            />
            <KeyGroup
              title="Missing"
              tone="missing"
              matches={tailor.missing_skills}
              emptyLabel="No missing skills — great coverage."
            />
          </>
        ) : (
          <p className="text-xs leading-relaxed text-ink-400">
            Add a job description and run job matching to see matched, partial and missing
            keywords.
          </p>
        )}
      </div>

      {onViewAll ? (
        <button type="button" className="btn-secondary mt-6 w-full" onClick={onViewAll}>
          View all keywords
        </button>
      ) : null}
    </div>
  );
}
