import { useState } from "react";
import { ApiError, acceptChange, editChange, getChanges, rejectChange } from "../api/client";
import { diffWords } from "../lib/diff";
import type {
  ChangeListResponse,
  ChangeStatus,
  GuardStatus,
  ResumeChange,
} from "../types";

interface ChangeReviewProps {
  resumeId: string;
  changes: ChangeListResponse | null;
  onRefresh: (list: ChangeListResponse) => void;
}

const STATUS_STYLES: Record<ChangeStatus, string> = {
  proposed: "bg-ink-900/[0.06] text-ink-700",
  accepted: "bg-emerald-50 text-emerald-700",
  rejected: "bg-red-50 text-red-700",
};

const GUARD_STYLES: Record<GuardStatus, string> = {
  safe: "bg-emerald-50 text-emerald-700",
  needs_review: "bg-amber-50 text-amber-700",
  unsafe: "bg-red-50 text-red-700",
};

const GUARD_ACCENTS: Record<GuardStatus, string> = {
  safe: "border-l-emerald-600",
  needs_review: "border-l-amber-600",
  unsafe: "border-l-red-600",
};

const GUARD_LABEL: Record<GuardStatus, string> = {
  safe: "Guard: safe",
  needs_review: "Guard: needs review",
  unsafe: "Guard: unsafe",
};

function categoryLabel(category: string): string {
  return category.replace(/_/g, " ");
}

function DiffPanel({
  title,
  side,
  tone,
}: {
  title: string;
  side: { text: string; type: "same" | "added" | "removed" }[];
  tone: "original" | "revised";
}) {
  const containerClass =
    tone === "original"
      ? "rounded-xl border border-ink-200 bg-cream-50 p-3"
      : "rounded-xl border border-emerald-200 bg-emerald-50/50 p-3";
  const titleClass =
    tone === "original" ? "text-ink-500" : "text-emerald-700";
  return (
    <div className={containerClass}>
      <p className={`text-xs font-semibold uppercase tracking-wide ${titleClass}`}>{title}</p>
      <p className="mt-1.5 whitespace-pre-wrap break-words text-xs leading-relaxed text-ink-800">
        {side.length === 0 ? (
          <span className="text-ink-400">—</span>
        ) : (
          side.map((token, index) => (
            <span key={index}>
              {token.type === "added" ? (
                <mark className="rounded bg-emerald-200/80 px-0.5 font-semibold text-emerald-900">
                  {token.text}
                </mark>
              ) : token.type === "removed" ? (
                <mark className="rounded bg-red-200/70 px-0.5 text-red-800 line-through">
                  {token.text}
                </mark>
              ) : (
                token.text
              )}
              {index < side.length - 1 ? " " : ""}
            </span>
          ))
        )}
      </p>
    </div>
  );
}

function ChangeCard({
  change,
  pending,
  onAccept,
  onReject,
  onEdit,
}: {
  change: ResumeChange;
  pending: boolean;
  onAccept: () => void;
  onReject: () => void;
  onEdit: (text: string) => Promise<void>;
}) {
  const canDecide = change.status === "proposed";
  const canAccept = canDecide && change.action === "replace" && change.applicable;
  const canEdit = change.action === "replace" && change.status !== "accepted";
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(change.proposed_text ?? "");
  const [saving, setSaving] = useState(false);
  const [editError, setEditError] = useState<string | null>(null);

  const showDiff = change.action === "replace" && change.proposed_text !== null;
  const diff = showDiff ? diffWords(change.original_text, change.proposed_text ?? "") : null;

  const saveEdit = async () => {
    if (!draft.trim()) {
      setEditError("The replacement text cannot be empty.");
      return;
    }
    setSaving(true);
    setEditError(null);
    try {
      await onEdit(draft);
      setEditing(false);
    } catch (err) {
      setEditError(err instanceof ApiError ? err.message : "Could not save your edit.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <li className={`rounded-xl border border-line border-l-4 bg-base-card p-5 shadow-card ${GUARD_ACCENTS[change.guard_status]}`}>
      <div className="flex flex-wrap items-center gap-2">
        <span className="badge bg-ink-900/[0.05] capitalize text-ink-600">
          {categoryLabel(change.category)}
        </span>
        <span className="badge bg-brand-gradient-soft text-brand-400">
          {change.origin === "tailor" ? "Tailoring" : "Auto-fix"}
        </span>
        <span className={`badge ${GUARD_STYLES[change.guard_status]}`}>
          {GUARD_LABEL[change.guard_status]}
        </span>
        {change.user_edited ? (
          <span className="badge bg-brand-gradient-soft text-brand-400">Edited by you</span>
        ) : null}
        <span className={`badge ${STATUS_STYLES[change.status]} capitalize`}>
          {change.status}
        </span>
      </div>

      <h3 className="mt-3 font-display text-base font-semibold text-ink-900">
        {change.title}
      </h3>
      <p className="mt-1 text-sm leading-relaxed text-ink-500">{change.reason}</p>

      {change.source_line ? (
        <p className="mt-1.5 text-xs leading-relaxed text-ink-400">
          {change.source_end_line && change.source_end_line > change.source_line
            ? `Source lines ${change.source_line}\u2013${change.source_end_line}`
            : `Source line ${change.source_line}`}
          {change.evidence[0] ? `: ${change.evidence[0].text}` : ""}
        </p>
      ) : null}

      <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2">
        <DiffPanel
          title="Original"
          tone="original"
          side={
            diff
              ? diff.left
              : [{ text: change.original_text || "—", type: "same" as const }]
          }
        />
        <DiffPanel
          title={change.action === "replace" ? "Revised text" : "Advisory (no rewrite)"}
          tone="revised"
          side={
            diff
              ? diff.right
              : [
                  {
                    text: change.proposed_text ?? "No automatic rewrite; review manually.",
                    type: "same" as const,
                  },
                ]
          }
        />
      </div>

      {showDiff ? (
        <p className="mt-2 text-[0.7rem] text-ink-400">
          Removed words are struck through; added words are highlighted.
        </p>
      ) : null}

      {editing ? (
        <div className="mt-4">
          <label className="label" htmlFor={`edit-${change.id}`}>
            Your replacement text
          </label>
          <textarea
            id={`edit-${change.id}`}
            className="input min-h-24 resize-y font-mono text-xs leading-relaxed"
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
          />
          {editError ? (
            <p className="mt-1.5 text-xs text-red-600" role="alert">
              {editError}
            </p>
          ) : null}
          <div className="mt-2 flex items-center gap-2.5">
            <button
              type="button"
              className="btn-primary"
              onClick={() => void saveEdit()}
              disabled={saving}
            >
              {saving ? "Saving…" : "Save edit"}
            </button>
            <button
              type="button"
              className="btn-secondary"
              onClick={() => {
                setEditing(false);
                setEditError(null);
                setDraft(change.proposed_text ?? "");
              }}
              disabled={saving}
            >
              Cancel
            </button>
          </div>
        </div>
      ) : null}

      {change.guard_reasons.length > 0 ? (
        <ul className="mt-3 space-y-1 text-xs leading-relaxed text-amber-800">
          {change.guard_reasons.map((reason) => (
            <li key={reason} className="flex gap-2">
              <span aria-hidden="true" className="font-bold">!</span>
              {reason}
            </li>
          ))}
        </ul>
      ) : null}

      {canDecide ? (
        <div className="mt-4 flex flex-wrap items-center gap-2.5">
          <button
            type="button"
            className="btn-primary"
            onClick={onAccept}
            disabled={pending || !canAccept}
            title={canAccept ? undefined : "Only safe text rewrites can be applied."}
          >
            {pending ? "Working…" : "Accept change"}
          </button>
          <button type="button" className="btn-secondary" onClick={onReject} disabled={pending}>
            Reject
          </button>
          {canEdit ? (
            <button
              type="button"
              className="btn-secondary"
              onClick={() => {
                setDraft(change.proposed_text ?? "");
                setEditing((value) => !value);
              }}
              disabled={pending || saving}
            >
              {editing ? "Close editor" : "Edit"}
            </button>
          ) : null}
          {!canAccept ? (
            <span className="text-xs text-ink-400">
              Only safe text rewrites can be applied.
            </span>
          ) : null}
        </div>
      ) : canEdit ? (
        <div className="mt-4">
          <button
            type="button"
            className="btn-secondary"
            onClick={() => {
              setDraft(change.proposed_text ?? "");
              setEditing((value) => !value);
            }}
            disabled={pending || saving}
          >
            {editing ? "Close editor" : "Edit"}
          </button>
        </div>
      ) : null}
    </li>
  );
}

export function ChangeReview({ resumeId, changes, onRefresh }: ChangeReviewProps) {
  const [pendingId, setPendingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const decide = async (changeId: string, accept: boolean) => {
    setPendingId(changeId);
    setError(null);
    try {
      if (accept) {
        await acceptChange(resumeId, changeId);
      } else {
        await rejectChange(resumeId, changeId);
      }
      onRefresh(await getChanges(resumeId));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not update the change.");
    } finally {
      setPendingId(null);
    }
  };

  const edit = async (changeId: string, proposedText: string) => {
    setError(null);
    try {
      await editChange(resumeId, changeId, proposedText);
      onRefresh(await getChanges(resumeId));
    } catch (err) {
      throw err instanceof ApiError ? err : new ApiError("Could not save your edit.", "edit_failed", 0);
    }
  };

  if (!changes) {
    return (
      <section className="card p-6" aria-label="Proposed changes">
        <span className="eyebrow">Step 3 · Review</span>
        <h2 className="mt-1.5 font-display text-2xl font-semibold tracking-tight text-ink-900">
          Proposed changes
        </h2>
        <p className="mt-3 text-sm text-ink-500">Loading proposed changes…</p>
      </section>
    );
  }

  const { summary } = changes;

  return (
    <section className="card p-6 sm:p-8" aria-label="Proposed changes">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <span className="eyebrow">Step 3 · Review</span>
          <h2 className="mt-1.5 font-display text-2xl font-semibold tracking-tight text-ink-900">
            Proposed changes
          </h2>
        </div>
        <div className="flex flex-wrap gap-2 text-xs">
          <span className="badge bg-ink-900/[0.06] text-ink-600">{summary.total} total</span>
          <span className="badge bg-emerald-50 text-emerald-700">
            {summary.accepted} accepted
          </span>
          <span className="badge bg-ink-900/[0.06] text-ink-600">{summary.proposed} proposed</span>
          <span className="badge bg-red-50 text-red-700">{summary.rejected} rejected</span>
        </div>
      </div>
      <p className="mt-2 max-w-3xl text-sm leading-relaxed text-ink-500">
        Accept a change to apply it to the effective resume; the score recalculates
        automatically. Flags are advisory and are never applied.
      </p>

      {error ? (
        <div
          className="mt-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
          role="alert"
        >
          {error}
        </div>
      ) : null}

      {changes.changes.length === 0 ? (
        <p className="mt-4 text-sm text-ink-500">No changes were proposed for this resume.</p>
      ) : (
        <ul className="mt-5 space-y-4">
          {changes.changes.map((change) => (
            <ChangeCard
              key={change.id}
              change={change}
              pending={pendingId === change.id}
              onAccept={() => void decide(change.id, true)}
              onReject={() => void decide(change.id, false)}
              onEdit={(text) => edit(change.id, text)}
            />
          ))}
        </ul>
      )}
    </section>
  );
}