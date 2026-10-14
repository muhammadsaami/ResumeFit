import type { ResumeResponse } from "./types";
import { deleteResume, getHealth } from "./api/client";
import { AnalysisWorkspace } from "./components/AnalysisWorkspace";
import { Dashboard } from "./components/Dashboard";
import { ExportWorkspace } from "./components/ExportWorkspace";
import { Sidebar } from "./components/Sidebar";
import { TopBar } from "./components/TopBar";
import type { AnalysisTabKey, ViewKey } from "./navigation";
import { useCallback, useEffect, useState } from "react";

export type ConnectionStatus = "checking" | "online" | "offline";

export default function App() {
  const [view, setView] = useState<ViewKey>("dashboard");
  const [tab, setTab] = useState<AnalysisTabKey>("overview");
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [search, setSearch] = useState("");
  const [resume, setResume] = useState<ResumeResponse | null>(null);
  const [jobDescription, setJobDescription] = useState("");
  const [connection, setConnection] = useState<ConnectionStatus>("checking");
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    let active = true;
    const check = async () => {
      try {
        await getHealth();
        if (active) setConnection("online");
      } catch {
        if (active) setConnection("offline");
      }
    };
    void check();
    const timer = window.setInterval(check, 30_000);
    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, []);

  const navigate = useCallback((next: ViewKey, nextTab?: AnalysisTabKey) => {
    setView(next);
    setTab(nextTab ?? "overview");
    setSidebarOpen(false);
  }, []);

  const handleCreated = (created: ResumeResponse, description: string) => {
    setResume(created);
    setJobDescription(description);
    setTab("overview");
    setView("analysis");
    setSearch("");
  };

  const handleDelete = async () => {
    if (!resume) return;
    setDeleting(true);
    try {
      await deleteResume(resume.resume_id);
      setResume(null);
      setJobDescription("");
      setSearch("");
      setView("dashboard");
      setTab("overview");
    } finally {
      setDeleting(false);
    }
  };

  const handleReset = () => {
    setResume(null);
    setJobDescription("");
    setSearch("");
    setView("dashboard");
    setTab("overview");
  };

  return (
    <div className="min-h-screen bg-base bg-shell text-ink-900">
      <Sidebar
        view={view}
        tab={tab}
        hasResume={resume !== null}
        open={sidebarOpen}
        onNavigate={navigate}
        onClose={() => setSidebarOpen(false)}
      />

      <div className="lg:pl-72">
        <TopBar
          view={view}
          tab={tab}
          connection={connection}
          hasResume={resume !== null}
          search={search}
          onSearch={setSearch}
          onOpenMenu={() => setSidebarOpen(true)}
        />

        <main className="mx-auto w-full max-w-7xl px-4 pb-24 pt-6 sm:px-6 lg:px-8">
          {view === "dashboard" && (
            <Dashboard onCreated={handleCreated} connection={connection} />
          )}
          {view === "analysis" && (
            <AnalysisWorkspace
              resume={resume}
              jobDescription={jobDescription}
              deleting={deleting}
              tab={tab}
              onTabChange={setTab}
              searchQuery={search}
              onDelete={handleDelete}
              onGoToDashboard={handleReset}
            />
          )}
          {view === "export" && <ExportWorkspace resume={resume} />}
        </main>

        <footer className="border-t border-line">
          <div className="mx-auto max-w-7xl px-4 py-8 text-sm leading-relaxed text-ink-400 sm:px-6 lg:px-8">
            ResumeFit — local, rule-based ATS analysis with reviewable edits and real LaTeX
            export. Temporary resume data is held in memory and deleted automatically after one
            hour.
          </div>
        </footer>
      </div>
    </div>
  );
}
