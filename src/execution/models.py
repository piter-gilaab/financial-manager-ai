"""Closed, data-only contracts for onboarded dataset execution."""

from dataclasses import dataclass
from enum import Enum
from typing import Any

from src.financial.models import envelope


class AdapterOutcome(str, Enum):
    READY_FOR_EXECUTION = "READY_FOR_EXECUTION"
    UNSUPPORTED_OPERATION = "UNSUPPORTED_OPERATION"
    MISSING_SEMANTIC_FIELD = "MISSING_SEMANTIC_FIELD"
    UNRESOLVED_SEMANTICS = "UNRESOLVED_SEMANTICS"
    INVALID_REGISTRY = "INVALID_REGISTRY"
    SCHEMA_MISMATCH = "SCHEMA_MISMATCH"
    QUALITY_BLOCKER = "QUALITY_BLOCKER"
    STALE_MAPPING = "STALE_MAPPING"
    DATASET_BLOCKED = "DATASET_BLOCKED"


class SalesRecordOperation(str, Enum):
    SALES_RECORD_COUNT = "SALES_RECORD_COUNT"
    SALES_SUMMARY = "SALES_SUMMARY"
    SALES_BY_COUNTRY = "SALES_BY_COUNTRY"
    SALES_BY_PERIOD = "SALES_BY_PERIOD"
    SALES_BY_SEGMENT = "SALES_BY_SEGMENT"
    SALES_BY_PRODUCT = "SALES_BY_PRODUCT"
    PROFIT_SUMMARY = "PROFIT_SUMMARY"
    DISCOUNT_ANALYSIS = "DISCOUNT_ANALYSIS"
    UNITS_SOLD_SUMMARY = "UNITS_SOLD_SUMMARY"


class MissingDimensionPolicy(str, Enum):
    BUCKET = "BUCKET"
    EXCLUDE = "EXCLUDE"


class PeriodGranularity(str, Enum):
    MONTH = "MONTH"
    YEAR = "YEAR"


@dataclass(frozen=True, slots=True)
class AdapterExecutionRequest:
    dataset_id: str
    operation: SalesRecordOperation | str
    missing_dimension: MissingDimensionPolicy | str = MissingDimensionPolicy.BUCKET
    granularity: PeriodGranularity | str = PeriodGranularity.MONTH


@dataclass(frozen=True, slots=True)
class AdapterValidation:
    outcome: AdapterOutcome
    message: str

    @property
    def ready(self) -> bool:
        return self.outcome is AdapterOutcome.READY_FOR_EXECUTION

    def to_dict(self) -> dict[str, Any]:
        return {"outcome": self.outcome.value, "message": self.message}


_MESSAGES = {
    AdapterOutcome.READY_FOR_EXECUTION: "The registered dataset is ready for this adapter operation.",
    AdapterOutcome.UNSUPPORTED_OPERATION: "The requested adapter operation is not supported.",
    AdapterOutcome.MISSING_SEMANTIC_FIELD: "A semantic field required by this operation is missing.",
    AdapterOutcome.UNRESOLVED_SEMANTICS: "Required dataset semantics are not approved.",
    AdapterOutcome.INVALID_REGISTRY: "The registered dataset artifacts are invalid.",
    AdapterOutcome.SCHEMA_MISMATCH: "The source schema does not match the approved mapping.",
    AdapterOutcome.QUALITY_BLOCKER: "The requested result cannot be calculated safely.",
    AdapterOutcome.STALE_MAPPING: "The registered semantic mapping is stale.",
    AdapterOutcome.DATASET_BLOCKED: "The dataset is not eligible for execution.",
}


def validation(outcome: AdapterOutcome) -> AdapterValidation:
    return AdapterValidation(outcome, _MESSAGES[outcome])


def evidence_envelope(request: object) -> dict[str, Any]:
    if isinstance(request, AdapterExecutionRequest):
        operation = request.operation.value if isinstance(request.operation, SalesRecordOperation) else (
            request.operation if type(request.operation) is str else None
        )
        dataset_id = request.dataset_id if type(request.dataset_id) is str else None
    else:
        operation = dataset_id = None
    return envelope({"query_name": operation, "dataset": dataset_id})


def failure_evidence(request: object, result: AdapterValidation) -> dict[str, Any]:
    response = evidence_envelope(request)
    response["status"] = (
        "UNSUPPORTED" if result.outcome is AdapterOutcome.UNSUPPORTED_OPERATION
        else "DATA_QUALITY_BLOCKER"
    )
    response["errors"] = [{
        "code": result.outcome.value,
        "field": None,
        "message": result.message,
    }]
    response["metadata"] = {"adapter_validation": result.to_dict()}
    return response
