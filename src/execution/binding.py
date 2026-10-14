"""Deterministic binding from registered datasets to closed adapter requests."""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable

from src.financial.models import envelope
from src.onboarding.models import OnboardingError
from src.onboarding.registry import DatasetRegistry, re_dataset_id
from src.dynamic_financial import DYNAMIC_GROUPED_OPERATIONS

from .models import (
    AdapterExecutionRequest,
    MissingDimensionPolicy,
    PeriodGranularity,
    SalesRecordOperation,
)
from .registry import adapter_for


BINDING_VERSION = "1.0"
_ADAPTER_VERSION = "1.0"
_CANONICAL_MODEL_VERSION = "1.0"


class BindingOutcome(str, Enum):
    BOUND = "BOUND"
    INVALID_REQUEST = "INVALID_REQUEST"
    DATASET_NOT_FOUND = "DATASET_NOT_FOUND"
    UNSUPPORTED_DOMAIN = "UNSUPPORTED_DOMAIN"
    UNSUPPORTED_OPERATION = "UNSUPPORTED_OPERATION"
    MISSING_REQUIRED_SEMANTICS = "MISSING_REQUIRED_SEMANTICS"
    INVALID_PARAMETER = "INVALID_PARAMETER"
    ADAPTER_UNAVAILABLE = "ADAPTER_UNAVAILABLE"
    STALE_MAPPING = "STALE_MAPPING"
    BINDING_BLOCKED = "BINDING_BLOCKED"


@dataclass(frozen=True, slots=True)
class DynamicQueryParameters:
    missing_dimension: MissingDimensionPolicy | str | None = None
    granularity: PeriodGranularity | str | None = None


@dataclass(frozen=True, slots=True)
class DynamicQueryRequest:
    dataset_id: str
    operation: SalesRecordOperation | str
    parameters: DynamicQueryParameters = field(default_factory=DynamicQueryParameters)


@dataclass(frozen=True, slots=True)
class BoundExecutionRequest:
    binding_version: str
    dataset_id: str
    canonical_domain: str
    adapter_request: AdapterExecutionRequest
    registry_version: int
    mapping_version: int
    mapping_digest: str
    adapter_version: str
    canonical_model_version: str


@dataclass(frozen=True, slots=True)
class DynamicOperationBinding:
    canonical_domain: str
    operation: SalesRecordOperation
    required_roles: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class BindingResult:
    outcome: BindingOutcome
    message: str
    request: BoundExecutionRequest | None = None

    @property
    def bound(self) -> bool:
        return self.outcome is BindingOutcome.BOUND and self.request is not None

    def to_dict(self) -> dict[str, Any]:
        return {
            "outcome": self.outcome.value,
            "message": self.message,
            "bound": self.bound,
        }


_MESSAGES = {
    BindingOutcome.BOUND: "The structured request is bound to an approved adapter operation.",
    BindingOutcome.INVALID_REQUEST: "The dynamic query request is invalid.",
    BindingOutcome.DATASET_NOT_FOUND: "The requested dataset is not registered.",
    BindingOutcome.UNSUPPORTED_DOMAIN: "The registered canonical domain is not supported for dynamic execution.",
    BindingOutcome.UNSUPPORTED_OPERATION: "The requested dynamic operation is not supported for this domain.",
    BindingOutcome.MISSING_REQUIRED_SEMANTICS: "Required semantics for this dynamic operation are not approved.",
    BindingOutcome.INVALID_PARAMETER: "A dynamic query parameter is not supported for this operation.",
    BindingOutcome.ADAPTER_UNAVAILABLE: "No compatible execution adapter is registered for this binding.",
    BindingOutcome.STALE_MAPPING: "The registered semantic mapping is stale.",
    BindingOutcome.BINDING_BLOCKED: "The registered dataset is not eligible for query binding.",
}


def _result(outcome: BindingOutcome, request: BoundExecutionRequest | None = None) -> BindingResult:
    return BindingResult(outcome, _MESSAGES[outcome], request)


_OPERATION_KEYS = {item.value: item for item in SalesRecordOperation}
_MISSING_DIMENSION_KEYS = {item.value: item for item in MissingDimensionPolicy}
_GRANULARITY_KEYS = {item.value: item for item in PeriodGranularity}
_DYNAMIC_OPERATION_BINDINGS = (
    DynamicOperationBinding(
        "SALES_RECORD", SalesRecordOperation.SALES_RECORD_COUNT, (),
    ),
    DynamicOperationBinding(
        "SALES_RECORD", SalesRecordOperation.SALES_SUMMARY, ("SALES",),
    ),
    DynamicOperationBinding(
        "SALES_RECORD", SalesRecordOperation.SALES_BY_COUNTRY, ("SALES", "COUNTRY"),
    ),
    DynamicOperationBinding(
        "SALES_RECORD", SalesRecordOperation.SALES_BY_PERIOD,
        ("SALES", "TRANSACTION_DATE"),
    ),
    DynamicOperationBinding(
        "SALES_RECORD", SalesRecordOperation.SALES_BY_SEGMENT, ("SALES", "SEGMENT"),
    ),
    DynamicOperationBinding(
        "SALES_RECORD", SalesRecordOperation.SALES_BY_PRODUCT, ("SALES", "PRODUCT"),
    ),
    DynamicOperationBinding(
        "SALES_RECORD", SalesRecordOperation.PROFIT_SUMMARY, ("PROFIT",),
    ),
    DynamicOperationBinding(
        "SALES_RECORD", SalesRecordOperation.DISCOUNT_ANALYSIS, ("DISCOUNT",),
    ),
    DynamicOperationBinding(
        "SALES_RECORD", SalesRecordOperation.UNITS_SOLD_SUMMARY, ("UNITS_SOLD",),
    ),
)
_BINDINGS = {
    (item.canonical_domain, item.operation): item.required_roles
    for item in _DYNAMIC_OPERATION_BINDINGS
}


def dynamic_operation_bindings(domain: str) -> tuple[DynamicOperationBinding, ...]:
    """Return the closed, code-owned operation catalog for one canonical domain."""
    if type(domain) is not str:
        return ()
    return tuple(item for item in _DYNAMIC_OPERATION_BINDINGS
                 if item.canonical_domain == domain)


class DynamicQueryBinder:
    """Bind explicit dataset IDs and operation keys; never interpret free text."""

    def __init__(
        self,
        onboarding_root: Path | str,
        *,
        adapter_resolver: Callable = adapter_for,
        readiness_probe: bool = False,
    ):
        if type(readiness_probe) is not bool:
            raise TypeError("readiness_probe must be a bool")
        self.root = Path(onboarding_root)
        self._registry = DatasetRegistry(self.root)
        self._adapter_resolver = adapter_resolver
        self._readiness_probe = readiness_probe

    def bind(self, request: object) -> BindingResult:
        if (not isinstance(request, DynamicQueryRequest)
                or type(request.dataset_id) is not str
                or not isinstance(request.parameters, DynamicQueryParameters)):
            return _result(BindingOutcome.INVALID_REQUEST)
        if not re_dataset_id(request.dataset_id):
            return _result(BindingOutcome.INVALID_REQUEST)
        try:
            workflow = self._registry.workflow(request.dataset_id)
            entry = self._registry.get(request.dataset_id)
            profile = self._registry.load_profile(request.dataset_id, entry.profile_digest)
            mapping = self._registry.load_mapping(
                request.dataset_id,
                entry.semantic_mapping_version,
                entry.semantic_mapping_digest,
            )
        except OnboardingError as error:
            if error.code == "dataset_not_found":
                return _result(BindingOutcome.DATASET_NOT_FOUND)
            if error.code == "artifact_mismatch":
                return _result(BindingOutcome.STALE_MAPPING)
            return _result(BindingOutcome.BINDING_BLOCKED)
        if (
            workflow.get("mapping_version") != entry.semantic_mapping_version
            or workflow.get("mapping_digest") != entry.semantic_mapping_digest
            or workflow.get("profile_version") != entry.profile_version
            or workflow.get("profile_digest") != entry.profile_digest
            or workflow.get("source_fingerprint") != entry.source_fingerprint
            or workflow.get("ingestion_run_id") != entry.ingestion_run_id
            or workflow.get("source_type") != entry.source_type
            or workflow.get("source_sheet") != entry.source_sheet
            or workflow.get("row_count") != entry.row_count
            or workflow.get("registry_version") != entry.registry_version
            or workflow.get("approved_domain") != entry.canonical_domain
            or profile.profile_version != entry.profile_version
            or profile.source_sha256 != entry.source_fingerprint
            or profile.row_count != entry.row_count
            or mapping.profile_digest != profile.profile_digest
        ):
            return _result(BindingOutcome.STALE_MAPPING)
        if not self._eligible(entry, readiness_probe=self._readiness_probe) or mapping.status != "SEMANTICALLY_APPROVED":
            return _result(BindingOutcome.BINDING_BLOCKED)
        if entry.canonical_domain != mapping.approved_domain:
            return _result(BindingOutcome.STALE_MAPPING)
        if entry.canonical_domain != "SALES_RECORD":
            return _result(BindingOutcome.UNSUPPORTED_DOMAIN)
        operation = (
            request.operation if isinstance(request.operation, SalesRecordOperation)
            else _OPERATION_KEYS.get(request.operation) if type(request.operation) is str
            else None
        )
        if operation is None:
            return _result(BindingOutcome.UNSUPPORTED_OPERATION)
        required_roles = _BINDINGS.get((entry.canonical_domain, operation))
        if required_roles is None:
            return _result(BindingOutcome.UNSUPPORTED_OPERATION)
        raw_policy = request.parameters.missing_dimension
        if operation.value in DYNAMIC_GROUPED_OPERATIONS:
            raw_policy = MissingDimensionPolicy.BUCKET if raw_policy is None else raw_policy
            policy = (
                raw_policy if isinstance(raw_policy, MissingDimensionPolicy)
                else _MISSING_DIMENSION_KEYS.get(raw_policy) if type(raw_policy) is str
                else None
            )
            if policy is None:
                return _result(BindingOutcome.INVALID_PARAMETER)
        else:
            if raw_policy is not None:
                return _result(BindingOutcome.INVALID_PARAMETER)
            policy = MissingDimensionPolicy.BUCKET
        raw_granularity = request.parameters.granularity
        if operation is SalesRecordOperation.SALES_BY_PERIOD:
            raw_granularity = PeriodGranularity.MONTH if raw_granularity is None else raw_granularity
            granularity = (
                raw_granularity if isinstance(raw_granularity, PeriodGranularity)
                else _GRANULARITY_KEYS.get(raw_granularity) if type(raw_granularity) is str
                else None
            )
            if granularity is None:
                return _result(BindingOutcome.INVALID_PARAMETER)
        else:
            if raw_granularity is not None:
                return _result(BindingOutcome.INVALID_PARAMETER)
            granularity = PeriodGranularity.MONTH
        for role in required_roles:
            matches = [item for item in mapping.proposals if item.proposed_role == role]
            if len(matches) != 1 or matches[0].status != "CONFIRMED":
                return _result(BindingOutcome.MISSING_REQUIRED_SEMANTICS)
            try:
                profile_column = profile.column(matches[0].source_column)
            except KeyError:
                return _result(BindingOutcome.BINDING_BLOCKED)
            if profile_column.column_id != matches[0].column_id:
                return _result(BindingOutcome.BINDING_BLOCKED)
        adapter = self._adapter_resolver(entry.canonical_domain, self.root)
        if not self._compatible_adapter(
            adapter,
            domain=entry.canonical_domain,
            operation=operation,
            adapter_version=_ADAPTER_VERSION,
            canonical_model_version=_CANONICAL_MODEL_VERSION,
        ):
            return _result(BindingOutcome.ADAPTER_UNAVAILABLE)
        adapter_request = AdapterExecutionRequest(
            dataset_id=request.dataset_id,
            operation=operation,
            missing_dimension=policy,
            granularity=granularity,
        )
        return _result(BindingOutcome.BOUND, BoundExecutionRequest(
            binding_version=BINDING_VERSION,
            dataset_id=request.dataset_id,
            canonical_domain=entry.canonical_domain,
            adapter_request=adapter_request,
            registry_version=entry.registry_version,
            mapping_version=entry.semantic_mapping_version,
            mapping_digest=entry.semantic_mapping_digest,
            adapter_version=adapter.adapter_version,
            canonical_model_version=adapter.canonical_model_version,
        ))

    def execute(self, request: object) -> dict[str, Any]:
        bound = self.bind(request)
        if not bound.bound:
            return self._failure_evidence(request, bound)
        adapter = self._adapter_resolver(bound.request.canonical_domain, self.root)
        if not self._compatible_adapter(
            adapter,
            domain=bound.request.canonical_domain,
            operation=bound.request.adapter_request.operation,
            adapter_version=bound.request.adapter_version,
            canonical_model_version=bound.request.canonical_model_version,
        ):
            return self._failure_evidence(
                request, _result(BindingOutcome.ADAPTER_UNAVAILABLE),
            )
        return adapter.execute(bound.request.adapter_request)

    @staticmethod
    def _failure_evidence(request: object, result: BindingResult) -> dict[str, Any]:
        dataset_id = request.dataset_id if (
            isinstance(request, DynamicQueryRequest) and type(request.dataset_id) is str
        ) else None
        operation = request.operation if isinstance(request, DynamicQueryRequest) else None
        if isinstance(operation, SalesRecordOperation):
            operation = operation.value
        elif type(operation) is not str:
            operation = None
        response = envelope({"query_name": operation, "dataset": dataset_id})
        if result.outcome in {
            BindingOutcome.INVALID_REQUEST,
            BindingOutcome.DATASET_NOT_FOUND,
            BindingOutcome.INVALID_PARAMETER,
        }:
            response["status"] = "INVALID_REQUEST"
        elif result.outcome in {
            BindingOutcome.UNSUPPORTED_DOMAIN,
            BindingOutcome.UNSUPPORTED_OPERATION,
        }:
            response["status"] = "UNSUPPORTED"
        else:
            response["status"] = "DATA_QUALITY_BLOCKER"
        response["errors"] = [{
            "code": result.outcome.value,
            "field": None,
            "message": result.message,
        }]
        response["metadata"] = {"query_binding": result.to_dict()}
        return response

    @staticmethod
    def _compatible_adapter(
        adapter,
        *,
        domain: str,
        operation: SalesRecordOperation,
        adapter_version: str,
        canonical_model_version: str,
    ) -> bool:
        return bool(
            adapter is not None
            and adapter.domain == domain
            and adapter.adapter_version == adapter_version
            and adapter.canonical_model_version == canonical_model_version
            and operation in adapter.supported_operations()
        )

    @staticmethod
    def _eligible(entry, *, readiness_probe: bool = False) -> bool:
        if entry.lifecycle_state in {"REGISTERED", "READY"}:
            return True
        if entry.lifecycle_state != "BLOCKED":
            return False
        analysis = next((
            item for item in entry.capability_readiness.get("capabilities", [])
            if type(item) is dict and item.get("identifier") == "FINANCIAL_ANALYSIS"
        ), None)
        if not analysis or analysis.get("semantic_readiness") != "READY":
            return False
        if (readiness_probe and analysis.get("state") == "BLOCKED"
                and analysis.get("policy_readiness") == "READY"):
            return True
        return bool(
            analysis
            and analysis.get("state") == "BLOCKED_NOT_IMPLEMENTED"
            and analysis.get("semantic_readiness") == "READY"
            and analysis.get("policy_readiness") == "READY"
        )
