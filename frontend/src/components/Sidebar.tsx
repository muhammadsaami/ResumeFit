import { NAV_ITEMS, isNavActive, type AnalysisTabKey, type ViewKey } from "../navigation";
import { CloseIcon } from "./icons";

interface SidebarProps {
  view: ViewKey;
  tab: AnalysisTabKey;
  hasResume: boolean;
  open: boolean;
  onNavigate: (view: ViewKey, tab?: AnalysisTabKey) => void;
  onClose: () => void;
}

export function Sidebar({
  view,
  tab,
  hasResume,
  open,
  onNavigate,
  onClose,
}: SidebarProps) {
  return (
    <>
      {open ? (
        <button
          type="button"
          aria-label="Close navigation"
          onClick={onClose}
          className="fixed inset-0 z-30 bg-black/60 backdrop-blur-sm lg:hidden"
        />
      ) : null}

      <aside
        className={`fixed inset-y-0 left-0 z-40 flex w-72 flex-col border-r border-line bg-base-sidebar transition-transform duration-200 lg:translate-x-0 ${
          open ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="flex items-center justify-between gap-3 px-5 pb-5 pt-6">
          <button
            type="button"
            onClick={() => onNavigate("dashboard")}
            className="flex items-center gap-3 rounded-xl text-left"
            aria-label="ResumeFit home"
          >
            <span className="relative flex h-10 w-10 items-center justify-center rounded-xl bg-brand-gradient font-display text-base font-bold text-white shadow-[0_8px_24px_rgba(115,87,255,0.4)]">
              RF
            </span>
            <span className="min-w-0">
              <span className="block font-display text-lg font-bold tracking-tight text-ink-900">
                ResumeFit
              </span>
              <span className="block text-[0.7rem] font-medium text-ink-400">
                AI Resume Intelligence
              </span>
            </span>
          </button>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-1.5 text-ink-400 hover:bg-ink-900/[0.06] hover:text-ink-900 lg:hidden"
            aria-label="Close navigation"
          >
            <CloseIcon className="h-5 w-5" />
          </button>
        </div>

        <nav aria-label="Primary" className="flex-1 space-y-1 overflow-y-auto px-3">
          {NAV_ITEMS.map((item) => {
            const active = isNavActive(item, view, tab);
            const Icon = item.icon;
            return (
              <button
                key={item.key}
                type="button"
                onClick={() => {
                  onNavigate(item.view, item.tab);
                  onClose();
                }}
                aria-current={active ? "page" : undefined}
                className={`nav-link ${active ? "nav-link-active" : ""}`}
              >
                {active ? (
                  <span
                    className="absolute inset-y-2 left-0 w-1 rounded-r-full bg-brand-gradient"
                    aria-hidden="true"
                  />
                ) : null}
                <Icon
                  className={`h-5 w-5 shrink-0 ${active ? "text-brand-400" : "text-ink-400"}`}
                />
                <span className="truncate">{item.label}</span>
                {item.view === "analysis" && hasResume ? (
                  <span
                    className="ml-auto h-1.5 w-1.5 shrink-0 rounded-full bg-brand-400"
                    aria-hidden="true"
                  />
                ) : null}
              </button>
            );
          })}
        </nav>

        <div className="px-5 pb-6 pt-4">
          <div className="rounded-xl border border-line bg-base-elevated/60 px-4 py-4">
            <p className="text-xs font-semibold text-ink-600">Private by design</p>
            <p className="mt-1 text-[0.7rem] leading-relaxed text-ink-400">
              Local, rule-based analysis. Resumes are deleted automatically after one hour and
              never leave your machine.
            </p>
          </div>
        </div>
      </aside>
    </>
  );
}
