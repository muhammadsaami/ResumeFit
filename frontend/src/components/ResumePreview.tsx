import { useEffect, useMemo, useRef } from "react";
import { highlightLine } from "../lib/highlight";

interface ResumePreviewProps {
  text: string;
  greenTerms: string[];
  amberTerms: string[];
  issueLines: number[];
  activeLine: number | null;
  searchQuery?: string;
}

const TONE_CLASS: Record<"green" | "amber", string> = {
  green: "rounded bg-emerald-100 px-0.5 font-semibold text-emerald-900",
  amber: "rounded bg-amber-100 px-0.5 font-semibold text-amber-900",
};

export function ResumePreview({
  text,
  greenTerms,
  amberTerms,
  issueLines,
  activeLine,
  searchQuery = "",
}: ResumePreviewProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const issueSet = useMemo(() => new Set(issueLines), [issueLines]);
  const lines = useMemo(() => text.split("\n"), [text]);
  const query = searchQuery.trim().toLowerCase();

  const matchLines = useMemo(() => {
    if (!query) return new Set<number>();
    const set = new Set<number>();
    lines.forEach((line, index) => {
      if (line.toLowerCase().includes(query)) set.add(index + 1);
    });
    return set;
  }, [lines, query]);

  useEffect(() => {
    if (activeLine === null) return;
    const node = containerRef.current?.querySelector(`#preview-line-${activeLine}`);
    node?.scrollIntoView({ behavior: "smooth", block: "center" });
  }, [activeLine]);

  useEffect(() => {
    if (!query) return;
    const first = containerRef.current?.querySelector("[data-search-match='true']");
    first?.scrollIntoView({ behavior: "smooth", block: "center" });
  }, [query]);

  return (
    <section className="card p-6" aria-label="Resume preview">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="font-display text-base font-semibold text-ink-900">Resume preview</h2>
          <p className="mt-1 text-xs leading-relaxed text-ink-500">
            Highlighted in place: matched job terms, and lines with detected issues.
          </p>
        </div>
        <div className="flex flex-wrap gap-2 text-[0.7rem]">
          <span className="badge bg-emerald-50 text-emerald-700">Matched / present</span>
          <span className="badge bg-amber-50 text-amber-700">Reinforce in a bullet</span>
          <span className="badge bg-red-50 text-red-700">Detected issue</span>
          {query ? (
            <span className="badge bg-cyan-400/15 text-cyan-300">
              {matchLines.size} match{matchLines.size === 1 ? "" : "es"}
            </span>
          ) : null}
        </div>
      </div>

      <div
        ref={containerRef}
        className="mt-4 max-h-[32rem] overflow-auto rounded-xl border border-line bg-base-input p-3"
      >
        <ol className="space-y-0.5">
          {lines.map((line, index) => {
            const number = index + 1;
            const hasIssue = issueSet.has(number);
            const isActive = activeLine === number;
            const isMatch = matchLines.has(number);
            const segments = highlightLine(line, greenTerms, amberTerms);
            return (
              <li
                key={number}
                id={`preview-line-${number}`}
                data-search-match={isMatch ? "true" : undefined}
                className={[
                  "flex gap-3 rounded-md border-l-4 px-2 py-0.5 font-mono text-xs leading-relaxed",
                  hasIssue ? "border-l-red-500 bg-red-50/50" : "border-l-transparent",
                  isMatch ? "ring-1 ring-cyan-400/60" : "",
                  isActive ? "ring-2 ring-brand-500/70" : "",
                ].join(" ")}
              >
                <span className="w-7 shrink-0 select-none text-right text-ink-400 tabular-nums">
                  {number}
                </span>
                <span className="min-w-0 whitespace-pre-wrap break-words text-ink-700">
                  {segments.map((segment, segmentIndex) =>
                    segment.tone ? (
                      <mark key={segmentIndex} className={TONE_CLASS[segment.tone]}>
                        {segment.text}
                      </mark>
                    ) : (
                      <span key={segmentIndex}>{segment.text}</span>
                    ),
                  )}
                </span>
              </li>
            );
          })}
        </ol>
      </div>
    </section>
  );
}
