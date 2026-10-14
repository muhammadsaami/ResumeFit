import type {
  AnalysisResponse,
  ApiErrorEnvelope,
  ArtifactInfo,
  ChangeDecisionResponse,
  ChangeListResponse,
  HealthResponse,
  OverleafResponse,
  RenderResponse,
  ResumeResponse,
  TailorResponse,
  TemplateListResponse,
} from "../types";

const baseUrl = (import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000").replace(/\/+$/, "");
const API = `${baseUrl}/api/v1`;

export class ApiError extends Error {
  readonly code: string;
  readonly status: number;

  constructor(message: string, code: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.code = code;
    this.status = status;
  }
}

async function toApiError(response: Response): Promise<ApiError> {
  let message = "Something went wrong. Please try again.";
  let code = "unknown_error";
  try {
    const body = (await response.json()) as ApiErrorEnvelope;
    if (body?.error?.message) message = body.error.message;
    if (body?.error?.code) code = body.error.code;
  } catch {
    // Non-JSON error body; keep the generic message.
  }
  return new ApiError(message, code, response.status);
}

async function request(url: string, init?: RequestInit): Promise<Response> {
  try {
    return await fetch(url, init);
  } catch {
    throw new ApiError(
      "Cannot reach the ResumeFit server. Is the backend running on " + baseUrl + "?",
      "network_error",
      0,
    );
  }
}

export async function getHealth(): Promise<HealthResponse> {
  const response = await request(`${API}/health`);
  if (!response.ok) throw await toApiError(response);
  return (await response.json()) as HealthResponse;
}

export async function createResumeFromFile(file: File): Promise<ResumeResponse> {
  const form = new FormData();
  form.append("file", file, file.name);
  const response = await request(`${API}/resumes`, { method: "POST", body: form });
  if (!response.ok) throw await toApiError(response);
  return (await response.json()) as ResumeResponse;
}

export async function createResumeFromText(text: string): Promise<ResumeResponse> {
  const response = await request(`${API}/resumes`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });
  if (!response.ok) throw await toApiError(response);
  return (await response.json()) as ResumeResponse;
}

export async function deleteResume(resumeId: string): Promise<void> {
  const response = await request(`${API}/resumes/${encodeURIComponent(resumeId)}`, {
    method: "DELETE",
  });
  if (response.status === 204) return;
  if (!response.ok) throw await toApiError(response);
}

export async function analyzeResume(resumeId: string): Promise<AnalysisResponse> {
  const response = await request(
    `${API}/resumes/${encodeURIComponent(resumeId)}/analyze`,
    { method: "POST" },
  );
  if (!response.ok) throw await toApiError(response);
  return (await response.json()) as AnalysisResponse;
}

export async function getChanges(resumeId: string): Promise<ChangeListResponse> {
  const response = await request(`${API}/resumes/${encodeURIComponent(resumeId)}/changes`);
  if (!response.ok) throw await toApiError(response);
  return (await response.json()) as ChangeListResponse;
}

export async function tailorResume(
  resumeId: string,
  jobDescription: string,
): Promise<TailorResponse> {
  const response = await request(
    `${API}/resumes/${encodeURIComponent(resumeId)}/tailor`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ job_description: jobDescription }),
    },
  );
  if (!response.ok) throw await toApiError(response);
  return (await response.json()) as TailorResponse;
}

export async function acceptChange(
  resumeId: string,
  changeId: string,
): Promise<ChangeDecisionResponse> {
  const response = await request(
    `${API}/resumes/${encodeURIComponent(resumeId)}/changes/${encodeURIComponent(changeId)}/accept`,
    { method: "POST" },
  );
  if (!response.ok) throw await toApiError(response);
  return (await response.json()) as ChangeDecisionResponse;
}

export async function rejectChange(
  resumeId: string,
  changeId: string,
): Promise<ChangeDecisionResponse> {
  const response = await request(
    `${API}/resumes/${encodeURIComponent(resumeId)}/changes/${encodeURIComponent(changeId)}/reject`,
    { method: "POST" },
  );
  if (!response.ok) throw await toApiError(response);
  return (await response.json()) as ChangeDecisionResponse;
}

export async function editChange(
  resumeId: string,
  changeId: string,
  proposedText: string,
): Promise<ChangeDecisionResponse> {
  const response = await request(
    `${API}/resumes/${encodeURIComponent(resumeId)}/changes/${encodeURIComponent(changeId)}/edit`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ proposed_text: proposedText }),
    },
  );
  if (!response.ok) throw await toApiError(response);
  return (await response.json()) as ChangeDecisionResponse;
}

export async function fetchTemplates(resumeId: string): Promise<TemplateListResponse> {
  const response = await request(
    `${API}/resumes/${encodeURIComponent(resumeId)}/render/templates`,
  );
  if (!response.ok) throw await toApiError(response);
  return (await response.json()) as TemplateListResponse;
}

export async function renderResume(
  resumeId: string,
  templateId: string,
): Promise<RenderResponse> {
  const response = await request(
    `${API}/resumes/${encodeURIComponent(resumeId)}/render`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ template_id: templateId }),
    },
  );
  if (!response.ok) throw await toApiError(response);
  return (await response.json()) as RenderResponse;
}

export async function prepareOverleaf(
  resumeId: string,
  templateId: string,
): Promise<OverleafResponse> {
  const response = await request(
    `${API}/resumes/${encodeURIComponent(resumeId)}/overleaf`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ template_id: templateId }),
    },
  );
  if (!response.ok) throw await toApiError(response);
  return (await response.json()) as OverleafResponse;
}

export function absoluteArtifactUrl(path: string): string {
  if (/^https?:\/\//.test(path)) return path;
  return baseUrl + path;
}

export async function downloadArtifact(
  artifact: ArtifactInfo,
): Promise<{ blob: Blob; filename: string }> {
  const response = await request(absoluteArtifactUrl(artifact.download_url));
  if (!response.ok) throw await toApiError(response);
  return { blob: await response.blob(), filename: artifact.filename };
}
