import type { ConnectionStatus } from "../App";
import { NAV_ITEMS, type AnalysisTabKey, type ViewKey } from "../navigation";
import { MenuIcon, SearchIcon, UserIcon } from "./icons";

interface TopBarProps {
  view: ViewKey;
  tab: AnalysisTabKey;
  connection: ConnectionStatus;
  hasResume: boolean;
  search: string;
  onSearch: (value: string) => void;
  onOpenMenu: () => void;
}

const CONNECTION_STYLES: Record<ConnectionStatus, { dot: string; label: string }> = {
  checking: { dot: "bg-amber-400", label: "Checking engine" },
  online: { dot: "bg-emerald-400", label: "Engine online" },
  offline: { dot: "bg-red-400", label: "Engine offline" },
};

function pageTitle(view: ViewKey): string {
  if (view === "dashboard") return "Dashboard";
  if (view === "export") return "Export & Download";
  return "Resume Analysis";
}

function sectionLabel(view: ViewKey, tab: AnalysisTabKey): string {
  if (view === "dashboard") return "Workspace";
  if (view === "export") return "Export";
  const match = NAV_ITEMS.find((item) => item.view === "analysis" && (item.tab ?? "overview") === tab);
  return match?.label ?? "Resume Analysis";
}

export function TopBar({
  view,
  tab,
  connection,
  hasResume,
  search,
  onSearch,
  onOpenMenu,
}: TopBarProps) {
  const status = CONNECTION_STYLES[connection];

  return (
    <header className="sticky top-0 z-20 border-b border-line bg-base/85 backdrop-blur supports-[backdrop-filter]:bg-base/70">
      <div className="flex items-center gap-3 px-4 py-3 sm:px-6">
        <button
          type="button"
          onClick={onOpenMenu}
          className="rounded-lg border border-line bg-base-elevated p-2 text-ink-500 hover:text-ink-900 lg:hidden"
          aria-label="Open navigation"
        >
          <MenuIcon className="h-5 w-5" />
        </button>

        <div className="hidden min-w-0 md:block">
          <p className="truncate font-display text-sm font-semibold text-ink-900">{pageTitle(view)}</p>
          <p className="truncate text-[0.7rem] text-ink-400">{sectionLabel(view, tab)}</p>
        </div>

        <label className="relative ml-auto flex min-w-0 max-w-md flex-1 items-center">
          <SearchIcon className="pointer-events-none absolute left-3 h-4 w-4 text-ink-400" />
          <input
            type="search"
            value={search}
            onChange={(event) => onSearch(event.target.value)}
            disabled={!hasResume}
            placeholder={hasResume ? "Search your resume text…" : "Import a resume to search"}
            aria-label="Search resume text"
            className="input py-2 pl-9 pr-3 text-sm disabled:cursor-not-allowed disabled:opacity-60"
          />
        </label>

        <div
          className="hidden items-center gap-2 rounded-full border border-line bg-base-elevated px-3 py-1.5 text-xs font-medium text-ink-500 sm:flex"
          role="status"
          aria-live="polite"
        >
          <span className={`h-2 w-2 rounded-full ${status.dot}`} aria-hidden="true" />
          {status.label}
        </div>

        <div className="flex items-center gap-2 rounded-full border border-line bg-base-elevated py-1 pl-1 pr-3">
          <span className="flex h-7 w-7 items-center justify-center rounded-full bg-brand-gradient-soft text-brand-400">
            <UserIcon className="h-4 w-4" />
          </span>
          <span className="hidden text-xs font-medium text-ink-500 sm:inline">Local session</span>
        </div>
      </div>
    </header>
  );
}
