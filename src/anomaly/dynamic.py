"""Deterministic global anomaly screening for approved dynamic SALES_RECORD data."""

from collections import Counter
from dataclasses import dataclass
from decimal import DecimalException
from pathlib import Path
from typing import Any

from src.execution.models import AdapterOutcome
from src.execution.sales_record import SalesRecordExecutionAdapter
from src.financial.arithmetic import canonical_decimal, exact_context
from src.financial.models import ContractError, arithmetic_metadata, envelope
from src.dynamic_anomaly import DynamicAnomalyOperation

from .baseline import MINIMUM_SIZE, assessment, reference
from .models import DynamicAnomalyAssessment, DynamicAnomalyScreeningResult


@dataclass(frozen=True, slots=True)
class DynamicAnomalyRequest:
    dataset_id: str
    operation: DynamicAnomalyOperation | str


@dataclass(frozen=True, slots=True)
class DynamicAnomalyRegistration:
    operation: DynamicAnomalyOperation
    measure: str
    required_roles: tuple[str, ...]


_OPERATION_KEYS = {item.value: item for item in DynamicAnomalyOperation}
_REGISTRATION_CATALOG = (
    DynamicAnomalyRegistration(
        DynamicAnomalyOperation.SALES_ANOMALY_SCREEN, "SALES", ("SALES",),
    ),
    DynamicAnomalyRegistration(
        DynamicAnomalyOperation.PROFIT_ANOMALY_SCREEN, "PROFIT", ("PROFIT",),
    ),
)
_REGISTRATIONS = {item.operation: item for item in _REGISTRATION_CATALOG}
_POLICY = {"name": "tukey_iqr", "version": "1.0"}
_CANDIDATE_REFERENCE_LIMIT = 20


def dynamic_anomaly_operations() -> tuple[DynamicAnomalyOperation, ...]:
    return tuple(item.operation for item in _REGISTRATION_CATALOG)


def dynamic_anomaly_registrations() -> tuple[DynamicAnomalyRegistration, ...]:
    """Return the closed code-owned operation/measure/semantic catalog."""
    return _REGISTRATION_CATALOG


class DynamicAnomalyAdapter:
    """Closed adapter from authenticated SALES_RECORD artifacts to Tukey screening."""

    domain = "SALES_RECORD"
    adapter_version = "1.0"
    policy_name = "tukey_iqr"
    policy_version = "1.0"

    def __init__(self, onboarding_root: Path | str):
        self.root = Path(onboarding_root)
        self._sales_records = SalesRecordExecutionAdapter(self.root)

    @staticmethod
    def supported_operations() -> tuple[DynamicAnomalyOperation, ...]:
        return dynamic_anomaly_operations()

    def validate(self, request: object, *, readiness_probe: bool = False) -> dict[str, Any]:
        operation = self._operation(request)
        if operation is None:
            return {"state": "UNSUPPORTED", "reason": "unsupported_operation"}
        measure = _REGISTRATIONS[operation].measure
        checked, prepared = self._sales_records.prepare_anomaly_records(
            request.dataset_id, measure, readiness_probe=readiness_probe,
        )
        if not checked.ready:
            return {"state": "BLOCKED", "reason": self._preparation_reason(checked.outcome, measure)}
        if prepared.currency["status"] == "CONFIRMED_MULTIPLE":
            return {"state": "BLOCKED", "reason": "incompatible_currency"}
        try:
            probe = self._screen(prepared.records, measure, classify=False)
        except ContractError as error:
            return {"state": "BLOCKED", "reason": error.error["code"]}
        if probe["reference"]["eligibility"] != "ELIGIBLE":
            return {"state": "BLOCKED", "reason": probe["reference"]["reason"]}
        return {"state": "SUPPORTED", "reason": None}

    def execute(self, request: object) -> dict[str, Any]:
        operation = self._operation(request)
        if operation is None:
            return self._failure(request, "UNSUPPORTED", "unsupported_operation")
        measure = _REGISTRATIONS[operation].measure
        checked, prepared = self._sales_records.prepare_anomaly_records(
            request.dataset_id, measure,
        )
        if not checked.ready:
            return self._failure(
                request, "DATA_QUALITY_BLOCKER",
                self._preparation_reason(checked.outcome, measure),
            )
        if prepared.currency["status"] == "CONFIRMED_MULTIPLE":
            return self._failure(
                request, "DATA_QUALITY_BLOCKER", "incompatible_currency",
                currency=prepared.currency,
            )
        try:
            screened = self._screen(prepared.records, measure, classify=True)
        except ContractError as error:
            return self._failure(
                request, "DATA_QUALITY_BLOCKER", error.error["code"],
                currency=prepared.currency,
            )
        ref = screened["reference"]
        if ref["eligibility"] != "ELIGIBLE":
            return self._failure(
                request, "DATA_QUALITY_BLOCKER", ref["reason"],
                currency=prepared.currency,
            )

        untyped_items = screened["assessments"]
        counts = Counter(item["status"] for item in untyped_items)
        population = len(untyped_items)
        assessed = counts["CANDIDATE"] + counts["NOT_SELECTED"]
        count_evidence = {
            "population": population,
            "usable": screened["usable"],
            "assessed": assessed,
            "excluded": counts["NOT_ASSESSED"],
            "candidate": counts["CANDIDATE"],
            "not_selected": counts["NOT_SELECTED"],
            "not_assessed": counts["NOT_ASSESSED"],
        }
        reasons = Counter(
            item["reason"] for item in untyped_items if item["status"] == "NOT_ASSESSED"
        )
        currency = prepared.currency
        quality = self._quality(prepared, measure, reasons, currency)
        shared_warning_indices = tuple(
            index for index, warning in enumerate(quality["warnings"])
            if warning["scope"] == "dataset"
        )
        reason_warning_indices = {
            f"measure:{measure.casefold()}:{warning['code']}": index
            for index, warning in enumerate(quality["warnings"])
            if warning["scope"] == "record"
        }
        typed_items = tuple(
            DynamicAnomalyAssessment(
                dataset_id=request.dataset_id,
                quality_warning_indices=shared_warning_indices + (
                    (reason_warning_indices[item["reason"]],)
                    if item["reason"] in reason_warning_indices else ()
                ),
                **item,
            )
            for item in untyped_items
        )
        items = [item.to_dict() for item in typed_items]
        reference_evidence = {
            "reference_id": ref["reference_id"],
            "numeric_size": ref["numeric_size"],
            "eligibility": ref["eligibility"],
            "reason": ref["reason"],
            "q1": ref["q1"],
            "q3": ref["q3"],
            "iqr": ref["iqr"],
            "lower_fence": ref["lower_fence"],
            "upper_fence": ref["upper_fence"],
        }
        lineage = self._lineage(prepared, operation, items)
        response = envelope({"query_name": operation.value, "dataset": request.dataset_id})
        response.update(
            status="PARTIAL" if counts["NOT_ASSESSED"] else "SUCCESS",
            currency=currency,
            records={
                "population": population,
                "candidates": population,
                "used": assessed,
                "excluded": counts["NOT_ASSESSED"],
                "exclusion_reasons": dict(sorted(reasons.items())),
            },
            result=DynamicAnomalyScreeningResult(
                status="PARTIAL" if counts["NOT_ASSESSED"] else "SUCCESS",
                dataset_id=request.dataset_id,
                domain=self.domain,
                operation=operation.value,
                measure=measure,
                scope="GLOBAL",
                policy=dict(_POLICY),
                reference=reference_evidence,
                q1=ref["q1"],
                q3=ref["q3"],
                iqr=ref["iqr"],
                lower_fence=ref["lower_fence"],
                upper_fence=ref["upper_fence"],
                counts=count_evidence,
                not_assessed_reasons=dict(sorted(reasons.items())),
                conversion_applied=False,
                currency=currency,
                quality=quality,
                lineage=lineage,
                assessments=typed_items,
                candidate_references=tuple(
                    {
                        "dataset_id": request.dataset_id,
                        "canonical_record_id": item["canonical_record_id"],
                        "source_sheet": item["source_sheet"],
                        "source_row_number": item["source_row_number"],
                    }
                    for item in items if item["status"] == "CANDIDATE"
                )[:_CANDIDATE_REFERENCE_LIMIT],
                limitations=(
                    "Statistical candidates do not establish error, fraud, suspicion, misconduct, illegality or business risk.",
                    "This descriptive in-sample screen does not establish independent observations, detection accuracy, probability or business validity.",
                    "Only GLOBAL screening under tukey_iqr v1.0 is supported.",
                ),
            ).to_dict(),
            quality=quality,
            metadata=self._metadata(lineage),
        )
        return response

    @staticmethod
    def _operation(request: object) -> DynamicAnomalyOperation | None:
        if (not isinstance(request, DynamicAnomalyRequest)
                or type(request.dataset_id) is not str):
            return None
        if isinstance(request.operation, DynamicAnomalyOperation):
            return request.operation
        if type(request.operation) is str:
            return _OPERATION_KEYS.get(request.operation)
        return None

    @staticmethod
    def _preparation_reason(outcome: AdapterOutcome, measure: str) -> str:
        if outcome is AdapterOutcome.MISSING_SEMANTIC_FIELD:
            return f"missing_confirmed_{measure.casefold()}"
        if outcome is AdapterOutcome.UNRESOLVED_SEMANTICS:
            return f"missing_confirmed_{measure.casefold()}"
        if outcome is AdapterOutcome.QUALITY_BLOCKER:
            return "incompatible_currency"
        return outcome.value.casefold()

    @staticmethod
    def _screen(records, measure: str, *, classify: bool) -> dict[str, Any]:
        prepared = []
        values = []
        try:
            for record in sorted(
                records,
                key=lambda item: (item.source_row_number, item.canonical_record_id),
            ):
                token, status, raw = DynamicAnomalyAdapter._record_fields(record, measure)
                if token is None:
                    prepared.append((record, None, raw, status,
                                     f"measure:{measure.casefold()}:{status}"))
                    continue
                number = canonical_decimal(token)
                with exact_context():
                    number = +number
                values.append(number)
                prepared.append((record, number, raw, status, None))
            ref = reference(values, "global", (), {}, both_tails=True)
        except DecimalException:
            raise ContractError(
                "DATA_QUALITY_BLOCKER", "exact_arithmetic_limit",
                "Exact statistical arithmetic exceeded precision 60; no assessments returned.",
            ) from None
        if not classify or ref["eligibility"] != "ELIGIBLE":
            return {"reference": ref, "usable": len(values), "assessments": []}
        items = []
        for record, number, raw, status, reason in prepared:
            outcome = assessment(number, ref, reason)
            items.append({
                "canonical_record_id": record.canonical_record_id,
                "source_sheet": record.source_sheet,
                "source_row_number": record.source_row_number,
                "observed_value": None if number is None else format(number, "f"),
                "observed_raw": raw,
                "observed_status": status,
                "status": outcome["status"],
                "reason": outcome["reason"],
                "tail": outcome["tail"],
                "reference_id": outcome["reference_id"],
                "numeric_reference_size": outcome["numeric_peer_size"],
            })
        return {"reference": ref, "usable": len(values), "assessments": items}

    @staticmethod
    def _record_fields(record, measure: str) -> tuple[str | None, str, str | None]:
        if measure == "SALES":
            return record.sales, record.sales_status, record.sales_raw
        if measure == "PROFIT":
            return record.profit, record.profit_status, record.profit_raw
        raise ValueError("Unrecognized internal dynamic anomaly measure")

    @staticmethod
    def _quality(prepared, measure: str, reasons: Counter, currency: dict) -> dict:
        warnings = []
        if currency["status"] == "UNKNOWN":
            warnings.append({
                "code": "currency_unknown", "field": "currency", "scope": "dataset",
                "affected_records": None,
                "message": "Screening uses the unverified source denomination; no currency was inferred.",
                "flag_row_numbers": [],
            })
        for reason, count in sorted(reasons.items()):
            warnings.append({
                "code": reason.rsplit(":", 1)[-1],
                "field": measure.casefold(),
                "scope": "record",
                "affected_records": count,
                "message": "Unavailable measure values were not assessed and were not replaced with zero.",
                "flag_row_numbers": [],
            })
        if prepared.duplicate_row_candidates:
            warnings.append({
                "code": "duplicate_row_candidates", "field": None, "scope": "dataset",
                "affected_records": prepared.duplicate_row_candidates,
                "message": "Possible duplicate source rows are retained in this screening.",
                "flag_row_numbers": [],
            })
        return {"warnings": warnings, "flags": [], "detail": "summary"}

    def _lineage(self, prepared, operation, items) -> dict[str, Any]:
        return prepared.lineage | {
            "operation": operation.value,
            "policy": dict(_POLICY),
            "reference_id": "global",
            "records": [{
                "canonical_record_id": item["canonical_record_id"],
                "source_row_number": item["source_row_number"],
                "assessment": item["status"],
                "reason": item["reason"],
            } for item in items],
        }

    def _metadata(self, lineage) -> dict[str, Any]:
        return {
            "adapter": {"domain": self.domain, "version": self.adapter_version},
            "method": {
                "name": self.policy_name,
                "version": self.policy_version,
                "quantiles": "linear_(n-1)*p",
                "multiplier": "1.5",
                "minimum_numeric_records": MINIMUM_SIZE,
                "tails": "both",
                "comparison": "strict",
                "reference_population": "global_usable_values_including_assessed_record",
            },
            "arithmetic": arithmetic_metadata(),
            "lineage": lineage,
        }

    @staticmethod
    def _failure(request: object, status: str, code: str, *, currency=None) -> dict[str, Any]:
        operation = request.operation if isinstance(request, DynamicAnomalyRequest) else None
        if isinstance(operation, DynamicAnomalyOperation):
            operation = operation.value
        dataset_id = request.dataset_id if (
            isinstance(request, DynamicAnomalyRequest) and type(request.dataset_id) is str
        ) else None
        response = envelope({"query_name": operation, "dataset": dataset_id})
        response["status"] = status
        response["currency"] = currency
        response["errors"] = [{
            "code": code,
            "field": None,
            "message": "Dynamic anomaly screening could not be completed under the approved policy.",
        }]
        return response
