"""Typed, data-only contracts for dynamic anomaly screening."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class DynamicAnomalyAssessment:
    dataset_id: str
    canonical_record_id: str
    source_sheet: str | None
    source_row_number: int
    observed_value: str | None
    observed_raw: str | None
    observed_status: str
    status: str
    reason: str | None
    tail: str | None
    reference_id: str | None
    numeric_reference_size: int | None
    quality_warning_indices: tuple[int, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "dataset_id": self.dataset_id,
            "canonical_record_id": self.canonical_record_id,
            "source_sheet": self.source_sheet,
            "source_row_number": self.source_row_number,
            "observed_value": self.observed_value,
            "observed_raw": self.observed_raw,
            "observed_status": self.observed_status,
            "status": self.status,
            "reason": self.reason,
            "tail": self.tail,
            "reference_id": self.reference_id,
            "numeric_reference_size": self.numeric_reference_size,
            "quality_warning_indices": list(self.quality_warning_indices),
        }


@dataclass(frozen=True, slots=True)
class DynamicAnomalyScreeningResult:
    status: str
    dataset_id: str
    domain: str
    operation: str
    measure: str
    scope: str
    policy: dict[str, str]
    reference: dict[str, Any]
    q1: str
    q3: str
    iqr: str
    lower_fence: str
    upper_fence: str
    counts: dict[str, int]
    not_assessed_reasons: dict[str, int]
    conversion_applied: bool
    currency: dict[str, Any]
    quality: dict[str, Any]
    lineage: dict[str, Any]
    assessments: tuple[DynamicAnomalyAssessment, ...]
    candidate_references: tuple[dict[str, Any], ...]
    limitations: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "dataset_id": self.dataset_id,
            "domain": self.domain,
            "operation": self.operation,
            "measure": self.measure,
            "scope": self.scope,
            "policy": dict(self.policy),
            "reference": dict(self.reference),
            "q1": self.q1,
            "q3": self.q3,
            "iqr": self.iqr,
            "lower_fence": self.lower_fence,
            "upper_fence": self.upper_fence,
            "counts": dict(self.counts),
            "not_assessed_reasons": dict(self.not_assessed_reasons),
            "conversion_applied": self.conversion_applied,
            "currency": dict(self.currency),
            "quality": self.quality,
            "lineage": self.lineage,
            "assessments": [item.to_dict() for item in self.assessments],
            "candidate_references": [dict(item) for item in self.candidate_references],
            "limitations": list(self.limitations),
        }
