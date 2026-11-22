import type {
  AnalysisParameters,
  ApiFailureBody,
  ConversationTurn,
  DatasetProfile,
  DatasetSummary,
  ExecutionEnvelope,
  ProjectionEnvelope,
  Readiness,
  SemanticMapping,
  SessionAction,
  SessionProjection,
} from "./types";

const configuredBase = process.env.NEXT_PUBLIC_FINANCIAL_API_BASE_URL;
export const API_BASE_URL = (configuredBase || "http://127.0.0.1:8000/api/v1").replace(/\/$/, "");

export class ApiClientError extends Error {
  constructor(
    message: string,
    readonly httpStatus: number,
    readonly body: ApiFailureBody | null,
  ) {
    super(message);
    this.name = "ApiClientError";
  }

  get status(): string {
    return this.body?.status || (this.httpStatus === 0 ? "API_UNAVAILABLE" : "INVALID_REQUEST");
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      headers: init?.body instanceof FormData
        ? init.headers
        : { "Content-Type": "application/json", ...init?.headers },
      cache: "no-store",
    });
  } catch {
    throw new ApiClientError("Local Financial Manager API could not be reached.", 0, null);
  }

  const body = (await response.json().catch(() => null)) as T | ApiFailureBody | null;
  if (!response.ok) {
    const failure = body as ApiFailureBody | null;
    const message = failure?.errors?.[0]?.message || "The request could not be completed safely.";
    throw new ApiClientError(message, response.status, failure);
  }
  return body as T;
}

export const api = {
  health: () => request<ProjectionEnvelope<{ status: string; api_version: string; product_version: string }>>("/health"),
  capabilities: (datasetId?: string) => request<ProjectionEnvelope<Record<string, unknown>>>(
    `/capabilities${datasetId ? `?dataset_id=${encodeURIComponent(datasetId)}` : ""}`,
  ),
  datasets: () => request<ProjectionEnvelope<DatasetSummary[]>>("/datasets"),
  dataset: (id: string) => request<ProjectionEnvelope<DatasetSummary>>(`/datasets/${encodeURIComponent(id)}`),
  profile: (id: string) => request<ProjectionEnvelope<DatasetProfile>>(`/datasets/${encodeURIComponent(id)}/profile`),
  mappings: (id: string) => request<ProjectionEnvelope<SemanticMapping>>(`/datasets/${encodeURIComponent(id)}/mappings`),
  readiness: (id: string) => request<ProjectionEnvelope<Readiness>>(`/datasets/${encodeURIComponent(id)}/readiness`),
  upload: (file: File, sheet?: string, provenanceNote?: string) => {
    const body = new FormData();
    body.append("file", file);
    if (sheet) body.append("sheet", sheet);
    if (provenanceNote) body.append("provenance_note", provenanceNote);
    return request<ProjectionEnvelope<{ dataset: DatasetSummary; profile: DatasetProfile; mappings: SemanticMapping }>>(
      "/onboarding", { method: "POST", body },
    );
  },
  semanticDecision: (id: string, body: Record<string, unknown>) => request<ProjectionEnvelope<DatasetSummary>>(
    `/datasets/${encodeURIComponent(id)}/mappings/decisions`, { method: "POST", body: JSON.stringify(body) },
  ),
  confirmDomain: (id: string, domain: string, evidence: string) => request<ProjectionEnvelope<DatasetSummary>>(
    `/datasets/${encodeURIComponent(id)}/domain-confirmation`, { method: "POST", body: JSON.stringify({ domain, evidence }) },
  ),
  confirmQualifiers: (id: string, body: Record<string, string>) => request<ProjectionEnvelope<DatasetSummary>>(
    `/datasets/${encodeURIComponent(id)}/qualifiers`, { method: "POST", body: JSON.stringify(body) },
  ),
  analysis: (datasetId: string, operation: string, parameters: AnalysisParameters = {}) => request<ExecutionEnvelope>(
    "/analysis", { method: "POST", body: JSON.stringify({ dataset_id: datasetId, operation, parameters }) },
  ),
  anomaly: (datasetId: string, operation: string) => request<ExecutionEnvelope>(
    "/anomalies", { method: "POST", body: JSON.stringify({ dataset_id: datasetId, operation }) },
  ),
  createSession: () => request<ProjectionEnvelope<SessionProjection>>("/sessions", { method: "POST", body: "{}" }),
  session: (id: string) => request<ProjectionEnvelope<SessionProjection>>(`/sessions/${encodeURIComponent(id)}`),
  sessionTurn: (id: string, message: string) => request<ProjectionEnvelope<ConversationTurn>>(
    `/sessions/${encodeURIComponent(id)}/turns`, { method: "POST", body: JSON.stringify({ message }) },
  ),
  answer: (id: string, value: string) => request<ProjectionEnvelope<SessionAction>>(
    `/sessions/${encodeURIComponent(id)}/answers`, { method: "POST", body: JSON.stringify({ value }) },
  ),
  followUp: (id: string, reference: string, intent: "why_selected" | "record_detail") => request<ProjectionEnvelope<SessionAction>>(
    `/sessions/${encodeURIComponent(id)}/follow-ups`, { method: "POST", body: JSON.stringify({ reference, intent }) },
  ),
};
