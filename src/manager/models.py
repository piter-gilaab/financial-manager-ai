"""Typed application envelopes; delegated evidence keeps its original schema."""

from copy import deepcopy
from dataclasses import dataclass
from enum import Enum
import json
from typing import Literal, NotRequired, TypedDict


class Capability(str, Enum):
    FINANCIAL_ANALYSIS = "FINANCIAL_ANALYSIS"
    ANOMALY_DETECTION = "ANOMALY_DETECTION"
    CASH_FLOW_FORECASTING = "CASH_FLOW_FORECASTING"
    DOCUMENT_RETRIEVAL = "DOCUMENT_RETRIEVAL"


class Availability(str, Enum):
    AVAILABLE = "AVAILABLE"
    BLOCKED = "BLOCKED"
    DEFERRED = "DEFERRED"


@dataclass(frozen=True, slots=True)
class CapabilityInfo:
    identifier: Capability
    name: str
    status: Availability
    reason: str | None
    documentation: tuple[str, ...]
    limitations: tuple[str, ...]

    def to_dict(self):
        return {"identifier": self.identifier.value, "name": self.name, "status": self.status.value,
                "reason": self.reason, "documentation": list(self.documentation),
                "limitations": list(self.limitations)}


class FinancialAnalysisRequest(TypedDict):
    question: str
    dataset: NotRequired[str | None]
    parameters: NotRequired[dict | None]


class AnomalyRequest(TypedDict):
    analysis_version: str
    dataset: str
    measure: str
    filters: NotRequired[dict]
    period: NotRequired[dict | None]
    quality_detail: NotRequired[str]


ExecutionStatus = Literal[
    "SUCCESS", "PARTIAL", "NO_DATA", "INVALID_REQUEST", "UNSUPPORTED",
    "DATA_QUALITY_BLOCKER", "CLARIFICATION_REQUIRED", "PROVIDER_UNAVAILABLE",
    "PROVIDER_ERROR", "CAPABILITY_UNAVAILABLE",
]


class ManagerResponse(TypedDict):
    manager_version: str
    capability: str | None
    capability_status: str | None
    execution_status: ExecutionStatus
    delegated_status: str | None
    delegated_result: dict | None
    summary: str
    warnings: list[dict]
    limitations: list[str]
    errors: list[dict]
    clarification: dict | None


def response(info, status, *, selected=None, result=None, delegated_status=None,
             summary="", warnings=(), errors=(), clarification=None) -> ManagerResponse:
    # Copies also isolate convenience fields from the authoritative nested result.
    return {"manager_version": "1.0", "capability": info.identifier.value if info else selected,
            "capability_status": info.status.value if info else None, "execution_status": status,
            "delegated_status": delegated_status, "delegated_result": deepcopy(result),
            "summary": summary, "warnings": deepcopy(list(warnings)),
            "limitations": list(info.limitations) if info else [],
            "errors": deepcopy(list(errors)), "clarification": deepcopy(clarification)}


@dataclass(frozen=True, slots=True)
class PlanStep:
    capability: CapabilityInfo
    clause: str
    request_json: str
    reason_code: str
    notes: tuple[str, ...] = ()

    def to_dict(self, step_id):
        return {"step_id": step_id, "capability": self.capability.to_dict(),
                "original_clause": self.clause, "normalized_request": json.loads(self.request_json),
                "reason_code": self.reason_code, "notes": list(self.notes)}


@dataclass(frozen=True, slots=True)
class RoutingPlan:
    original_request: str | None
    status: str
    reason_code: str
    message: str
    steps: tuple[PlanStep, ...] = ()
    clarification_field: str | None = None
    choices: tuple[str, ...] = ()

    def to_dict(self):
        return {"routing_version": "1.0", "original_request": self.original_request,
                "status": self.status, "reason_code": self.reason_code, "message": self.message,
                "steps": [step.to_dict(i) for i, step in enumerate(self.steps, 1)],
                "clarification": {"field": self.clarification_field, "question": self.message,
                                  "choices": list(self.choices)} if self.status == "CLARIFICATION_REQUIRED" else None,
                "blockers": [step.capability.to_dict() for step in self.steps
                             if step.capability.status != Availability.AVAILABLE]}
