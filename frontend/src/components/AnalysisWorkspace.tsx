import { useEffect, useMemo, useState } from "react";
import { ApiError, analyzeResume, getChanges } from "../api/client";
import { formatBytes, formatDateTime } from "../lib/format";
import { ANALYSIS_TABS, type AnalysisTabKey } from "../navigation";
import type {
  AnalysisResponse,
  ChangeListResponse,
  DetectedIssue,
  ExperienceEntry,
  ProjectEntry,
  ResumeResponse,
  RuleResult,
  RuleStatus,
  TailorResponse,
} from "../types";
import { ChangeReview } from "./ChangeReview";
import { InsightsPanel } from "./InsightsPanel";
import { MetricCards } from "./MetricCards";
import { ResumePreview } from "./ResumePreview";
import { TailorPanel } from "./TailorPanel";

interface AnalysisWorkspaceProps {
  resume: ResumeResponse | null;
  jobDescription: string;
  deleting: boolean;
  tab: AnalysisTabKey;
  onTabChange: (tab: AnalysisTabKey) => void;
  searchQuery: string;
  onDelete: () => void;
  onGoToDashboard: () => void;
}

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="stat-card">
      <dt className="text-[0.7rem] font-semibold uppercase tracking-wide text-ink-500">{label}</dt>
      <dd className="mt-1 font-display text-base font-semibold text-ink-800">{value}</dd>
    </div>
  );
}

const STATUS_STYLES: Record<RuleStatus, string> = {
  passed: "bg-emerald-50 text-emerald-700",
  warning: "bg-amber-50 text-amber-700",
  failed: "bg-red-50 text-red-700",
};

const STATUS_ICONS: Record<RuleStatus, string> = {
  passed: "✓",
  warning: "!",
  failed: "✕",
};

function StatusBadge({ status }: { status: RuleStatus }) {
  return (
    <span className={`badge capitalize ${STATUS_STYLES[status]}`}>
      <span aria-hidden="true" className="text-xs font-bold">
        {STATUS_ICONS[status]}
      </span>
      {status}
    </span>
  );
}

function scorePalette(score: number): string {
  if (score >= 80) return "text-emerald-700";
  if (score >= 60) return "text-amber-700";
  return "text-red-700";
}

function ScoreGauge({ analysis }: { analysis: AnalysisResponse }) {
  const { score, max_score: max } = analysis.ats_score;
  const color = scorePalette(score);
  const pct = Math.max(0, Math.min(score / Math.max(max, 1), 1));
  const radius = 50;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference * (1 - pct);

  return (
    <div
      className={`relative h-44 w-44 shrink-0 ${color}`}
      role="img"
      aria-label={`ATS score ${score} out of ${max}`}
    >
      <svg viewBox="0 0 120 120" className="h-full w-full -rotate-90">
        <circle cx="60" cy="60" r={radius} fill="none" stroke="#1C2740" strokeWidth="9" />
        <circle
          cx="60"
          cy="60"
          r={radius}
          fill="none"
          stroke="currentColor"
          strokeWidth="9"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="font-display text-5xl font-bold leading-none tabular-nums">{score}</span>
        <span className="mt-1.5 text-xs font-medium text-ink-400">of {max} points</span>
      </div>
    </div>
  );
}

function ScoreCard({ analysis }: { analysis: AnalysisResponse }) {
  const { ats_score: score } = analysis;
  return (
    <section className="card p-6 sm:p-8" aria-label="ATS-readiness score">
      <div className="flex flex-col items-start gap-8 lg:flex-row lg:items-center lg:justify-between">
        <div className="max-w-xl">
          <span className="eyebrow">ATS readiness</span>
          <h2 className="mt-2 font-display text-2xl font-semibold tracking-tight text-ink-900">
            {score.label}
          </h2>
          <p className="mt-2 text-sm leading-relaxed text-ink-500">{score.disclaimer}</p>
          <dl className="mt-6 grid grid-cols-3 gap-3">
            <Stat label="Passed" value={score.summary.passed} />
            <Stat label="Warnings" value={score.summary.warnings} />
            <Stat label="Failed" value={score.summary.failed} />
          </dl>
        </div>
        <ScoreGauge analysis={analysis} />
      </div>
    </section>
  );
}

function ContactRow({ label, value }: { label: string; value: string | null }) {
  return (
    <div className="flex items-center justify-between gap-3 py-2.5">
      <span className="text-xs font-medium uppercase tracking-wide text-ink-500">{label}</span>
      <span className={`text-sm ${value ? "text-ink-800" : "text-ink-400"}`}>
        {value ?? "Not detected"}
      </span>
    </div>
  );
}

function ProfileCard({ analysis }: { analysis: AnalysisResponse }) {
  const { structured_resume: parsed, ats_score: score } = analysis;
  const { basics, skills, confidence } = parsed;
  return (
    <section className="card p-6" aria-label="What we extracted">
      <div className="flex items-start justify-between gap-3">
        <h2 className="font-display text-base font-semibold text-ink-900">Profile</h2>
        <span className="badge border border-line bg-base-elevated text-ink-500">
          Confidence {Math.round(confidence.overall * 100)}%
        </span>
      </div>

      <div className="mt-4 divide-y divide-line">
        <ContactRow label="Name" value={basics.name} />
        <ContactRow label="Email" value={basics.email} />
        <ContactRow label="Phone" value={basics.phone} />
        <ContactRow label="Location" value={basics.city} />
        <ContactRow label="LinkedIn" value={basics.linkedin} />
        <ContactRow label="GitHub" value={basics.github} />
      </div>

      <div className="mt-4 flex flex-wrap gap-1.5">
        {parsed.sections_detected.length > 0 ? (
          parsed.sections_detected.map((section) => (
            <span key={section} className="badge bg-brand-gradient-soft capitalize text-brand-400">
              {section}
            </span>
          ))
        ) : (
          <span className="text-sm text-ink-400">No standard sections detected.</span>
        )}
      </div>

      <dl className="mt-5 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Stat label="Education" value={parsed.education.length} />
        <Stat label="Experience" value={parsed.experience.length} />
        <Stat label="Projects" value={parsed.projects.length} />
        <Stat label="Skills" value={skills.all_skills.length} />
      </dl>

      <p className="mt-4 text-xs text-ink-400">
        Overall ATS readiness: {score.score}/{score.max_score}
      </p>
    </section>
  );
}

function IssuesList({
  issues,
  onNavigate,
}: {
  issues: DetectedIssue[];
  onNavigate: (line: number) => void;
}) {
  return (
    <section className="card p-6" aria-label="Detected issues">
      <h2 className="font-display text-base font-semibold text-ink-900">Detected issues</h2>
      {issues.length === 0 ? (
        <p className="mt-3 text-sm text-ink-500">No issues detected by the current checks.</p>
      ) : (
        <ul className="mt-4 space-y-4">
          {issues.map((issue) => (
            <li key={issue.rule_id} className="flex gap-3">
              <span
                className={`flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-[0.65rem] font-bold text-white ${
                  issue.severity === "error" ? "bg-red-500" : "bg-amber-500"
                }`}
                aria-hidden="true"
              >
                {issue.severity === "error" ? "✕" : "!"}
              </span>
              <div>
                <p className="text-sm font-medium text-ink-800">{issue.message}</p>
                {issue.suggestion ? (
                  <p className="mt-1 text-xs leading-relaxed text-ink-500">{issue.suggestion}</p>
                ) : null}
                {issue.source_lines.length > 0 ? (
                  <button
                    type="button"
                    className="mt-1 text-xs text-brand-400 underline-offset-2 hover:underline"
                    onClick={() => onNavigate(issue.source_lines[0].line)}
                  >
                    Jump to line {issue.source_lines[0].line}
                  </button>
                ) : null}
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function RuleRow({ rule }: { rule: RuleResult }) {
  const ratio =
    rule.points_max > 0 ? Math.max(0, Math.min(rule.points_earned / rule.points_max, 1)) : 0;
  const barColor =
    rule.status === "passed"
      ? "bg-emerald-500"
      : rule.status === "warning"
        ? "bg-amber-500"
        : "bg-red-500";
  return (
    <li className="py-3.5">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-sm font-medium text-ink-900">{rule.name}</span>
            <StatusBadge status={rule.status} />
            <span className="badge border border-line bg-base-elevated text-ink-500">
              {rule.category.replace(/_/g, " ")}
            </span>
          </div>
          <p className="mt-1.5 text-xs leading-relaxed text-ink-500">{rule.explanation}</p>
          {rule.suggestion && rule.status !== "passed" ? (
            <p className="mt-1 text-xs leading-relaxed text-ink-600">{rule.suggestion}</p>
          ) : null}
          {rule.source_lines.length > 0 ? (
            <p className="mt-1 text-xs text-ink-400">
              Source line {rule.source_lines.map((line) => line.line).join(", ")}
            </p>
          ) : null}
        </div>
        <div className="flex shrink-0 flex-col items-end gap-1.5">
          <span className="text-sm tabular-nums text-ink-500">
            {rule.points_earned}/{rule.points_max}
          </span>
          <span className="h-1.5 w-20 overflow-hidden rounded-full bg-ink-100" role="presentation">
            <span className={`block h-full rounded-full ${barColor}`} style={{ width: `${ratio * 100}%` }} />
          </span>
        </div>
      </div>
    </li>
  );
}

function RuleBreakdown({ rules }: { rules: RuleResult[] }) {
  return (
    <section className="card p-6 sm:p-8" aria-label="Scoring breakdown">
      <h2 className="font-display text-xl font-semibold tracking-tight text-ink-900">
        Scoring breakdown
      </h2>
      <p className="mt-1.5 text-sm leading-relaxed text-ink-500">
        Every point is tied to a check so you can see exactly what affected the score.
      </p>
      <ul className="mt-2 divide-y divide-line">
        {rules.map((rule) => (
          <RuleRow key={rule.rule_id} rule={rule} />
        ))}
      </ul>
    </section>
  );
}

function SectionDetail({ analysis }: { analysis: AnalysisResponse }) {
  const { structured_resume: parsed, skills } = {
    structured_resume: analysis.structured_resume,
    skills: analysis.structured_resume.skills,
  };
  return (
    <section className="card p-6" aria-label="Extracted sections">
      <h2 className="font-display text-base font-semibold text-ink-900">Extracted sections</h2>
      <p className="mt-1 text-xs leading-relaxed text-ink-500">
        Every entry detected in your resume, preserved exactly as parsed.
      </p>

      {skills.all_skills.length > 0 ? (
        <div className="mt-5">
          <h3 className="text-xs font-semibold uppercase tracking-wide text-ink-500">Skills</h3>
          <div className="mt-2 flex flex-wrap gap-1.5">
            {skills.all_skills.map((skill) => (
              <span key={skill} className="badge border border-line bg-base-elevated text-ink-700">
                {skill}
              </span>
            ))}
          </div>
          {skills.duplicates.length > 0 ? (
            <p className="mt-2 text-xs text-amber-700">
              Duplicate skills: {skills.duplicates.join(", ")}
            </p>
          ) : null}
        </div>
      ) : null}

      {parsed.experience.length > 0 ? (
        <div className="mt-5 space-y-3">
          <h3 className="text-xs font-semibold uppercase tracking-wide text-ink-500">Experience</h3>
          {parsed.experience.map((entry: ExperienceEntry, index: number) => (
            <div key={`${entry.company ?? "exp"}-${index}`} className="text-sm text-ink-600">
              <p className="font-medium text-ink-900">
                {entry.role ?? "Role not detected"}
                {entry.company ? ` · ${entry.company}` : ""}
              </p>
              <p className="text-xs text-ink-500">
                {[entry.start_date, entry.end_date].filter(Boolean).join(" – ") || "Dates not detected"}
              </p>
            </div>
          ))}
        </div>
      ) : null}

      {parsed.projects.length > 0 ? (
        <div className="mt-5 space-y-3">
          <h3 className="text-xs font-semibold uppercase tracking-wide text-ink-500">Projects</h3>
          {parsed.projects.map((project: ProjectEntry, index: number) => (
            <div key={`${project.name ?? "project"}-${index}`} className="text-sm text-ink-600">
              <p className="font-medium text-ink-900">{project.name ?? "Untitled project"}</p>
              {project.technologies.length > 0 ? (
                <p className="text-xs text-ink-500">{project.technologies.join(", ")}</p>
              ) : null}
            </div>
          ))}
        </div>
      ) : null}

      {parsed.certifications.length > 0 ? (
        <div className="mt-5">
          <h3 className="text-xs font-semibold uppercase tracking-wide text-ink-500">
            Certifications
          </h3>
          <ul className="mt-2 space-y-1 text-sm text-ink-600">
            {parsed.certifications.map((certification, index) => (
              <li key={`${certification}-${index}`} className="flex gap-2">
                <span className="text-brand-400" aria-hidden="true">
                  •
                </span>
                <span>{certification}</span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </section>
  );
}

function SectionCoverage({ rules }: { rules: RuleResult[] }) {
  const sectionRules = rules.filter(
    (rule) => rule.rule_id.startsWith("section_") || rule.category === "sections",
  );
  return (
    <section className="card p-6" aria-label="Section coverage">
      <h2 className="font-display text-base font-semibold text-ink-900">Section coverage</h2>
      <p className="mt-1 text-xs leading-relaxed text-ink-500">
        ResumeFit checks standard resume sections. A section can be present but still need work —
        each result explains why.
      </p>
      {sectionRules.length === 0 ? (
        <p className="mt-3 text-sm text-ink-500">No section checks available.</p>
      ) : (
        <ul className="mt-4 space-y-3">
          {sectionRules.map((rule) => (
            <li key={rule.rule_id} className="flex items-start gap-3">
              <StatusBadge status={rule.status} />
              <div className="min-w-0">
                <p className="text-sm font-medium text-ink-800">{rule.name}</p>
                <p className="mt-0.5 text-xs leading-relaxed text-ink-500">{rule.explanation}</p>
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function TabsBar({
  tab,
  onTabChange,
  counts,
}: {
  tab: AnalysisTabKey;
  onTabChange: (tab: AnalysisTabKey) => void;
  counts: Partial<Record<AnalysisTabKey, number>>;
}) {
  return (
    <div
      role="tablist"
      aria-label="Analysis views"
      className="flex gap-1 overflow-x-auto rounded-xl border border-line bg-base-card p-1"
    >
      {ANALYSIS_TABS.map((item) => {
        const active = tab === item.key;
        const count = counts[item.key];
        return (
          <button
            key={item.key}
            role="tab"
            type="button"
            aria-selected={active}
            onClick={() => onTabChange(item.key)}
            className={`flex shrink-0 items-center gap-2 whitespace-nowrap rounded-lg px-3.5 py-2 text-sm font-medium transition-colors ${
              active
                ? "bg-brand-gradient text-white shadow-[0_6px_18px_rgba(115,87,255,0.35)]"
                : "text-ink-500 hover:bg-ink-900/[0.05] hover:text-ink-900"
            }`}
          >
            {item.label}
            {typeof count === "number" && count > 0 ? (
              <span
                className={`rounded-full px-1.5 text-[0.65rem] font-semibold tabular-nums ${
                  active ? "bg-white/20 text-white" : "bg-ink-100 text-ink-500"
                }`}
              >
                {count}
              </span>
            ) : null}
          </button>
        );
      })}
    </div>
  );
}

function LoadingPanel() {
  return (
    <div
      className="card flex items-center justify-center gap-3 p-8 text-sm text-ink-500"
      role="status"
      aria-busy="true"
    >
      <span
        className="h-5 w-5 animate-spin rounded-full border-2 border-brand-600/30 border-t-brand-400"
        aria-hidden="true"
      />
      Analyzing your resume…
    </div>
  );
}

function ErrorPanel({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div className="card border-red-200 p-8" role="alert">
      <h3 className="font-display text-lg font-semibold text-red-700">Analysis failed</h3>
      <p className="mt-1.5 text-sm leading-relaxed text-ink-500">{message}</p>
      <button type="button" className="btn-secondary mt-5" onClick={onRetry}>
        Try again
      </button>
    </div>
  );
}

export function AnalysisWorkspace({
  resume,
  jobDescription,
  deleting,
  tab,
  onTabChange,
  searchQuery,
  onDelete,
  onGoToDashboard,
}: AnalysisWorkspaceProps) {
  const [analysis, setAnalysis] = useState<AnalysisResponse | null>(null);
  const [changes, setChanges] = useState<ChangeListResponse | null>(null);
  const [tailor, setTailor] = useState<TailorResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [reloadToken, setReloadToken] = useState(0);
  const [activeLine, setActiveLine] = useState<number | null>(null);

  const navigateToLine = (line: number) => {
    onTabChange("preview");
    setActiveLine(null);
    window.setTimeout(() => setActiveLine(line), 0);
  };

  const preview = useMemo(() => {
    if (!analysis) {
      return { green: [] as string[], amber: [] as string[], issueLines: [] as number[] };
    }
    const green = new Set<string>();
    const amber = new Set<string>();

    for (const skill of analysis.structured_resume.skills.all_skills) {
      green.add(skill);
    }
    if (tailor) {
      const demonstrated = new Set(tailor.evidence_backed_skills.map((m) => m.canonical));
      for (const match of [...tailor.matched_skills, ...tailor.matched_keywords]) {
        green.add(match.term);
      }
      for (const match of tailor.matched_skills) {
        if (!demonstrated.has(match.canonical)) amber.add(match.term);
      }
    }

    const issueLines = new Set<number>();
    for (const issue of analysis.detected_issues) {
      for (const line of issue.source_lines) issueLines.add(line.line);
    }
    for (const rule of analysis.ats_score.breakdown) {
      if (rule.status === "passed") continue;
      for (const line of rule.source_lines) issueLines.add(line.line);
    }

    return {
      green: [...green],
      amber: [...amber],
      issueLines: [...issueLines].sort((a, b) => a - b),
    };
  }, [analysis, tailor]);

  useEffect(() => {
    if (!resume) {
      setAnalysis(null);
      setChanges(null);
      setTailor(null);
      setError(null);
      return;
    }
    let active = true;
    setLoading(true);
    setError(null);
    Promise.all([analyzeResume(resume.resume_id), getChanges(resume.resume_id)])
      .then(([analysisResult, changeResult]) => {
        if (!active) return;
        setAnalysis(analysisResult);
        setChanges(changeResult);
      })
      .catch((err: unknown) => {
        if (!active) return;
        setAnalysis(null);
        setChanges(null);
        setError(err instanceof ApiError ? err.message : "Analysis failed. Please try again.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [resume, reloadToken]);

  useEffect(() => {
    if (searchQuery.trim() && resume) onTabChange("preview");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchQuery]);

  const applyEffective = (list: ChangeListResponse) => {
    setChanges(list);
    setAnalysis(list.effective_analysis);
  };

  const handleTailored = (result: TailorResponse) => {
    setTailor(result);
    setChanges(result.changes);
    setAnalysis(result.changes.effective_analysis);
  };

  if (!resume) {
    return (
      <div className="card mx-auto max-w-2xl p-12 text-center">
        <span className="eyebrow">Analysis</span>
        <h2 className="mt-2 font-display text-2xl font-semibold tracking-tight text-ink-900">
          Nothing to analyze yet
        </h2>
        <p className="mx-auto mt-3 max-w-md text-sm leading-relaxed text-ink-500">
          Upload a resume or paste its text on the dashboard to get started.
        </p>
        <button type="button" className="btn-primary mt-7" onClick={onGoToDashboard}>
          Go to dashboard
        </button>
      </div>
    );
  }

  const { metadata } = resume;
  const proposedCount = changes?.summary.proposed ?? null;
  const counts: Partial<Record<AnalysisTabKey, number>> = {
    keywords: tailor ? tailor.matched_skills.length + tailor.missing_skills.length : undefined,
    suggestions: changes?.summary.total,
  };

  const analysisLoading = loading;
  const needAnalysis = tab === "overview" || tab === "sections" || tab === "preview";

  return (
    <div className="space-y-6">
      <section className="card p-6 sm:p-8">
        <div className="flex flex-col gap-5 sm:flex-row sm:items-start sm:justify-between">
          <div className="min-w-0">
            <span className="eyebrow">Resume received</span>
            <h2 className="mt-2 truncate font-display text-2xl font-semibold tracking-tight text-ink-900">
              {metadata.filename ?? "Pasted resume text"}
            </h2>
            <p className="mt-1.5 text-sm leading-relaxed text-ink-500">
              {metadata.source_type === "upload" ? "Uploaded file" : "Pasted text"} · parsed with{" "}
              <span className="font-medium text-ink-700">{metadata.parser}</span>
            </p>
          </div>
          <button
            type="button"
            className="btn-secondary shrink-0 border-red-200 text-red-700 hover:bg-red-50"
            onClick={onDelete}
            disabled={deleting}
          >
            {deleting ? "Deleting…" : "Delete resume data"}
          </button>
        </div>

        <dl className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
          <Stat label="Words" value={metadata.word_count} />
          <Stat label="Characters" value={metadata.character_count} />
          <Stat label="Lines" value={metadata.line_count} />
          <Stat label="Pages" value={metadata.page_count ?? "n/a"} />
          {metadata.source_type === "upload" ? (
            <Stat label="File size" value={formatBytes(metadata.size_bytes)} />
          ) : null}
          <Stat label="Created" value={formatDateTime(resume.created_at)} />
          <Stat label="Expires" value={formatDateTime(resume.expires_at)} />
        </dl>

        {metadata.warnings.length > 0 ? (
          <ul className="mt-5 space-y-1 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm leading-relaxed text-amber-900">
            {metadata.warnings.map((warning) => (
              <li key={warning}>{warning}</li>
            ))}
          </ul>
        ) : null}

        <details className="mt-6 rounded-xl border border-line bg-base-elevated/60 p-4">
          <summary className="cursor-pointer text-sm font-semibold text-ink-700">
            View extracted text
          </summary>
          <pre className="mt-3 max-h-80 overflow-auto whitespace-pre-wrap break-words rounded-lg border border-line bg-base-input p-3 font-mono text-xs leading-relaxed text-ink-700">
            {resume.extracted_text}
          </pre>
        </details>
      </section>

      {jobDescription ? (
        <section className="card p-6">
          <h3 className="font-display text-base font-semibold text-ink-900">
            Target job description
          </h3>
          <p className="mt-1 text-sm text-ink-500">
            Pre-filled from the dashboard. Adjust it in keyword match and run the match against
            your resume.
          </p>
          <pre className="mt-3 max-h-48 overflow-auto whitespace-pre-wrap break-words rounded-lg border border-line bg-base-input p-3 text-xs leading-relaxed text-ink-700">
            {jobDescription}
          </pre>
        </section>
      ) : null}

      <MetricCards
        analysis={analysis}
        tailor={tailor}
        proposedCount={proposedCount}
        loading={loading}
      />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="space-y-6 lg:col-span-2">
          <TabsBar tab={tab} onTabChange={onTabChange} counts={counts} />

          {needAnalysis && analysisLoading ? <LoadingPanel /> : null}
          {needAnalysis && !analysisLoading && error ? (
            <ErrorPanel message={error} onRetry={() => setReloadToken((value) => value + 1)} />
          ) : null}

          {tab === "overview" && analysis && !analysisLoading ? (
            <>
              <ScoreCard analysis={analysis} />
              {analysis.parsing_warnings.length > 0 ? (
                <ul className="space-y-1 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm leading-relaxed text-amber-900">
                  {analysis.parsing_warnings.map((warning) => (
                    <li key={warning}>{warning}</li>
                  ))}
                </ul>
              ) : null}
              <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
                <IssuesList issues={analysis.detected_issues} onNavigate={navigateToLine} />
                <ProfileCard analysis={analysis} />
              </div>
              <RuleBreakdown rules={analysis.ats_score.breakdown} />
            </>
          ) : null}

          {tab === "sections" && analysis && !analysisLoading ? (
            <>
              <ProfileCard analysis={analysis} />
              <SectionDetail analysis={analysis} />
              <SectionCoverage rules={analysis.ats_score.breakdown} />
            </>
          ) : null}

          {tab === "keywords" ? (
            <TailorPanel
              key={resume.resume_id}
              resumeId={resume.resume_id}
              initialJobDescription={jobDescription}
              tailor={tailor}
              onTailored={handleTailored}
              onNavigate={navigateToLine}
            />
          ) : null}

          {tab === "suggestions" ? (
            <ChangeReview resumeId={resume.resume_id} changes={changes} onRefresh={applyEffective} />
          ) : null}

          {tab === "preview" ? (
            <ResumePreview
              text={resume.extracted_text}
              greenTerms={preview.green}
              amberTerms={preview.amber}
              issueLines={preview.issueLines}
              activeLine={activeLine}
              searchQuery={searchQuery}
            />
          ) : null}
        </div>

        <div className="lg:col-span-1">
          <InsightsPanel
            analysis={analysis}
            tailor={tailor}
            onViewAll={() => onTabChange("keywords")}
          />
        </div>
      </div>
    </div>
  );
}
