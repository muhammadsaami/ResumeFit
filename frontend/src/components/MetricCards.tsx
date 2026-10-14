import type { ReactNode } from "react";
import type { AnalysisResponse, TailorResponse } from "../types";
import { AnalysisIcon, MatchIcon, SparkIcon, TemplatesIcon } from "./icons";

interface MetricCardsProps {
  analysis: AnalysisResponse | null;
  tailor: TailorResponse | null;
  proposedCount: number | null;
  loading: boolean;
}

interface MetricCardProps {
  label: string;
  value: string | number;
  caption: string;
  icon: ReactNode;
  tone: "brand" | "secondary" | "cyan" | "amber";
  meter?: number;
  ready: boolean;
  loading: boolean;
}

const TONE_CLASS: Record<MetricCardProps["tone"], string> = {
  brand: "from-brand-600/25 to-brand-600/5 text-brand-400",
  secondary: "from-secondary-500/25 to-secondary-500/5 text-secondary-400",
  cyan: "from-cyan-400/25 to-cyan-400/5 text-cyan-300",
  amber: "from-amber-400/25 to-amber-400/5 text-amber-400",
};

function meterColor(value: number): string {
  if (value >= 80) return "bg-emerald-500";
  if (value >= 60) return "bg-amber-500";
  return "bg-red-500";
}

function MetricCard({
  label,
  value,
  caption,
  icon,
  tone,
  meter,
  ready,
  loading,
}: MetricCardProps) {
  return (
    <div className="card p-5">
      <div className="flex items-start justify-between gap-3">
        <span className="text-xs font-semibold uppercase tracking-wide text-ink-500">
          {label}
        </span>
        <span
          className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br ${TONE_CLASS[tone]}`}
        >
          {icon}
        </span>
      </div>

      {loading ? (
        <div className="mt-3 h-9 w-20 animate-pulse rounded-lg bg-ink-100" aria-hidden="true" />
      ) : (
        <p
          className={`mt-2 font-display text-3xl font-bold leading-none tabular-nums ${
            ready ? "text-ink-900" : "text-ink-300"
          }`}
        >
          {value}
        </p>
      )}

      {typeof meter === "number" ? (
        <span className="mt-3 block h-1.5 overflow-hidden rounded-full bg-ink-100" role="presentation">
          <span
            className={`block h-full rounded-full ${meterColor(meter)}`}
            style={{ width: `${Math.max(0, Math.min(meter, 100))}%` }}
          />
        </span>
      ) : null}

      <p className="mt-3 text-xs leading-relaxed text-ink-400">{caption}</p>
    </div>
  );
}

export function MetricCards({ analysis, tailor, proposedCount, loading }: MetricCardsProps) {
  const score = analysis?.ats_score.score ?? null;
  const max = analysis?.ats_score.max_score ?? 100;
  const matchPct = tailor?.match_percentage ?? null;
  const skillCount = analysis?.structured_resume.skills.all_skills.length ?? null;

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <MetricCard
        label="ATS Readiness Score"
        value={score !== null ? `${score}/${max}` : "—"}
        caption={
          analysis
            ? "Estimated ATS-readiness based on rule-based checks."
            : "Run an analysis to calculate your ATS readiness."
        }
        icon={<AnalysisIcon className="h-5 w-5" />}
        tone="brand"
        meter={score !== null ? (score / Math.max(max, 1)) * 100 : undefined}
        ready={score !== null}
        loading={loading}
      />
      <MetricCard
        label="Job Match Score"
        value={matchPct !== null ? `${matchPct.toFixed(matchPct % 1 === 0 ? 0 : 1)}%` : "—"}
        caption={
          tailor
            ? "How well your resume covers the target job description."
            : "Add a job description to measure keyword match."
        }
        icon={<MatchIcon className="h-5 w-5" />}
        tone="secondary"
        meter={matchPct ?? undefined}
        ready={matchPct !== null}
        loading={loading}
      />
      <MetricCard
        label="Skills Detected"
        value={skillCount ?? "—"}
        caption={
        skillCount !== null
            ? "Distinct skills extracted from your resume."
            : "Skills appear here once your resume is parsed."
        }
        icon={<TemplatesIcon className="h-5 w-5" />}
        tone="cyan"
        ready={skillCount !== null}
        loading={loading}
      />
      <MetricCard
        label="Actionable Suggestions"
        value={proposedCount ?? "—"}
        caption={
          proposedCount !== null
            ? "Reviewable changes proposed by ResumeFit."
            : "Suggestions appear after analysis is complete."
        }
        icon={<SparkIcon className="h-5 w-5" />}
        tone="amber"
        ready={proposedCount !== null}
        loading={loading}
      />
    </div>
  );
}
