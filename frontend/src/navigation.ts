import type { ComponentType, SVGProps } from "react";

import {
  AnalysisIcon,
  DashboardIcon,
  ExportIcon,
  MatchIcon,
  SparkIcon,
  TemplatesIcon,
} from "./components/icons";

export type ViewKey = "dashboard" | "analysis" | "export";

export type AnalysisTabKey =
  | "overview"
  | "keywords"
  | "sections"
  | "suggestions"
  | "preview";

export interface NavItem {
  key: string;
  label: string;
  icon: ComponentType<SVGProps<SVGSVGElement>>;
  view: ViewKey;
  tab?: AnalysisTabKey;
}

export const NAV_ITEMS: NavItem[] = [
  { key: "dashboard", label: "Dashboard", icon: DashboardIcon, view: "dashboard" },
  { key: "analysis", label: "Resume Analysis", icon: AnalysisIcon, view: "analysis", tab: "overview" },
  { key: "matching", label: "Job Matching", icon: MatchIcon, view: "analysis", tab: "keywords" },
  { key: "suggestions", label: "AI Suggestions", icon: SparkIcon, view: "analysis", tab: "suggestions" },
  { key: "export", label: "Export & Download", icon: ExportIcon, view: "export" },
  { key: "templates", label: "Resume Templates", icon: TemplatesIcon, view: "export", tab: undefined },
];

export function isNavActive(item: NavItem, view: ViewKey, tab: AnalysisTabKey): boolean {
  if (item.view !== view) return false;
  if (item.view !== "analysis") return true;
  const itemTab = item.tab ?? "overview";
  return itemTab === tab;
}

export const ANALYSIS_TABS: { key: AnalysisTabKey; label: string }[] = [
  { key: "overview", label: "Overview" },
  { key: "keywords", label: "Keyword Match" },
  { key: "sections", label: "Section Analysis" },
  { key: "suggestions", label: "AI Suggestions" },
  { key: "preview", label: "Resume Preview" },
];
