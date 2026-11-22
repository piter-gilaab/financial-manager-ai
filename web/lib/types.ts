import type { components } from "./api-schema";

export type DatasetSummary = components["schemas"]["DatasetSummaryResponse"];
export type DatasetProfile = components["schemas"]["DatasetProfileResponse"];
export type SemanticMapping = components["schemas"]["SemanticMappingResponse"];
export type Readiness = components["schemas"]["ReadinessResponse"];
export type SessionProjection = components["schemas"]["SessionProjectionResponse"];
export type ConversationTurn = components["schemas"]["ConversationTurnResponse"];
export type SessionAction = components["schemas"]["SessionActionResponse"];
export type ApiError = components["schemas"]["ApiError"];
export type AnalysisParameters = components["schemas"]["AnalysisParameters"];
export type JsonValue = components["schemas"]["ExecutionEnvelope"]["evidence"];

export interface ProjectionEnvelope<T> {
  api_version: string;
  status: string;
  data: T;
  limitations: string[];
  errors: ApiError[];
}

export interface ExecutionEnvelope {
  api_version: string;
  status: string;
  evidence: JsonValue;
  limitations: string[];
  errors: ApiError[];
}

export interface ApiFailureBody {
  api_version?: string;
  status?: string;
  data?: { field?: string; choices?: string[] } | null;
  limitations?: string[];
  errors?: ApiError[];
}

export type ApiHealth = "checking" | "healthy" | "unavailable";

export function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
