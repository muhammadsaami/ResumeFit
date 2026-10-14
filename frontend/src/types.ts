export type SourceType = "upload" | "paste";

export type ExtractionStatus = "processed";

export interface ParsingMetadata {
  source_type: SourceType;
  filename: string | null;
  content_type: string | null;
  size_bytes: number;
  parser: string;
  character_count: number;
  word_count: number;
  line_count: number;
  page_count: number | null;
  warnings: string[];
}

export interface ResumeResponse {
  resume_id: string;
  status: ExtractionStatus;
  extracted_text: string;
  metadata: ParsingMetadata;
  created_at: string;
  expires_at: string;
}

export interface HealthResponse {
  status: string;
  service: string;
  version: string;
  uptime_seconds: number;
  stored_resumes: number;
  timestamp: string;
}

export interface ApiErrorDetail {
  location?: (string | number)[];
  message?: string;
}

export interface ApiErrorEnvelope {
  error: {
    code: string;
    message: string;
    details?: ApiErrorDetail[];
  };
}

export type RuleStatus = "passed" | "warning" | "failed";

export interface SourceLineRef {
  line: number;
  text: string;
}

export interface RuleResult {
  rule_id: string;
  name: string;
  category: string;
  status: RuleStatus;
  points_earned: number;
  points_max: number;
  explanation: string;
  suggestion: string | null;
  source_lines: SourceLineRef[];
}

export interface ScoreSummary {
  passed: number;
  warnings: number;
  failed: number;
}

export interface AtsScore {
  score: number;
  max_score: number;
  label: string;
  disclaimer: string;
  summary: ScoreSummary;
  breakdown: RuleResult[];
}

export interface DetectedIssue {
  rule_id: string;
  severity: "error" | "warning";
  message: string;
  suggestion: string | null;
  source_lines: SourceLineRef[];
}

export interface BulletItem {
  text: string;
  source_line: number | null;
}

export interface Basics {
  name: string | null;
  email: string | null;
  phone: string | null;
  city: string | null;
  linkedin: string | null;
  github: string | null;
}

export interface EducationEntry {
  institution: string | null;
  degree: string | null;
  start_date: string | null;
  end_date: string | null;
  score: string | null;
  source_lines: SourceLineRef[];
  confidence: number;
}

export interface ExperienceEntry {
  company: string | null;
  role: string | null;
  start_date: string | null;
  end_date: string | null;
  bullets: BulletItem[];
  source_lines: SourceLineRef[];
  confidence: number;
}

export interface ProjectEntry {
  name: string | null;
  technologies: string[];
  bullets: BulletItem[];
  source_lines: SourceLineRef[];
  confidence: number;
}

export interface Skills {
  languages: string[];
  frameworks: string[];
  tools: string[];
  other: string[];
  all_skills: string[];
  duplicates: string[];
  source_lines: SourceLineRef[];
  confidence: number;
}

export interface ParsingConfidence {
  overall: number;
  sections_found: number;
  sections_expected: number;
  contact_fields_found: number;
}

export interface StructuredResume {
  basics: Basics;
  education: EducationEntry[];
  experience: ExperienceEntry[];
  projects: ProjectEntry[];
  certifications: string[];
  skills: Skills;
  sections_detected: string[];
  nonstandard_headings: string[];
  warnings: string[];
  confidence: ParsingConfidence;
}

export interface AnalysisResponse {
  resume_id: string;
  status: string;
  structured_resume: StructuredResume;
  ats_score: AtsScore;
  detected_issues: DetectedIssue[];
  parsing_warnings: string[];
  analyzed_at: string;
}

export type ChangeCategory =
  | "heading_normalization"
  | "date_normalization"
  | "bullet_normalization"
  | "duplicate_skills"
  | "skill_grouping"
  | "skill_ordering"
  | "first_person"
  | "weak_opener"
  | "tense_normalization"
  | "bullet_shortening"
  | "bullet_rewrite"
  | "missing_contact"
  | "missing_section"
  | "personal_detail";

export type ChangeAction = "replace" | "flag";

export type ChangeStatus = "proposed" | "accepted" | "rejected";

export type GuardStatus = "safe" | "needs_review" | "unsafe";

export type ChangeOrigin = "autofix" | "tailor";

export interface ResumeChange {
  id: string;
  category: ChangeCategory;
  action: ChangeAction;
  origin: ChangeOrigin;
  title: string;
  original_text: string;
  proposed_text: string | null;
  reason: string;
  source_line: number | null;
  source_end_line: number | null;
  evidence: SourceLineRef[];
  guard_status: GuardStatus;
  guard_reasons: string[];
  status: ChangeStatus;
  applicable: boolean;
  user_edited: boolean;
}

export interface ChangeSummary {
  total: number;
  proposed: number;
  accepted: number;
  rejected: number;
  safe: number;
  needs_review: number;
  unsafe: number;
}

export interface ChangeListResponse {
  resume_id: string;
  summary: ChangeSummary;
  changes: ResumeChange[];
  effective_analysis: AnalysisResponse;
}

export interface ChangeDecisionResponse {
  resume_id: string;
  change: ResumeChange;
  applied: boolean;
  effective_analysis: AnalysisResponse;
}

export interface KeywordMatch {
  term: string;
  canonical: string;
  occurrences_in_job: number;
  in_resume: boolean;
  evidence: SourceLineRef[];
}

export interface JobDescriptionStats {
  character_count: number;
  word_count: number;
  unique_terms: number;
}

export interface TailorResponse {
  resume_id: string;
  job_description_stats: JobDescriptionStats;
  matched_skills: KeywordMatch[];
  missing_skills: KeywordMatch[];
  matched_keywords: KeywordMatch[];
  missing_keywords: KeywordMatch[];
  evidence_backed_skills: KeywordMatch[];
  suggested_skill_order: string[];
  bullet_suggestions: ResumeChange[];
  explanations: string[];
  match_percentage: number;
  match_note: string;
  changes: ChangeListResponse;
}

export type RenderStatus =
  | "success"
  | "compiler_unavailable"
  | "compilation_failed"
  | "timeout"
  | "too_large";

export type ArtifactKind = "pdf" | "tex";

export interface TemplateInfo {
  id: string;
  name: string;
  description: string;
}

export interface TemplateListResponse {
  templates: TemplateInfo[];
  default_template: string;
}

export interface ArtifactInfo {
  artifact_id: string;
  kind: ArtifactKind;
  filename: string;
  media_type: string;
  size_bytes: number;
  download_url: string;
}

export interface RenderResponse {
  resume_id: string;
  template_id: string;
  status: RenderStatus;
  compiler: string | null;
  page_count: number | null;
  pdf: ArtifactInfo | null;
  tex: ArtifactInfo;
  log: string | null;
  message: string | null;
  rendered_at: string;
}

export interface OverleafResponse {
  resume_id: string;
  template_id: string;
  method: string;
  tex: ArtifactInfo;
  note: string;
  instructions: string[];
}
