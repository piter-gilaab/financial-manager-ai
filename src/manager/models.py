"""Typed application envelopes; delegated evidence keeps its original schema."""

from copy import deepcopy
from dataclasses import dataclass
from enum import Enum
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
