"""Static adapters for the frozen PAYABLE, RECEIVABLE and CASH catalogs."""

from dataclasses import dataclass
from pathlib import Path

from src.dynamic_financial import MissingDimensionPolicy, PeriodGranularity
from src.financial.currency import CurrencyMetadata, CurrencyStatus, UNKNOWN_DISCLOSURE
from src.financial.models import ContractError, arithmetic_metadata
from src.financial.multidomain import (
    CanonicalFinancialRecord,
    cash_by_dimension,
    cash_by_period,
    cash_magnitude,
    cash_summary,
    obligation_aging,
    obligation_by_dimension,
    obligation_summary,
    overdue_obligation_summary,
    record_count,
)
from src.multidomain_financial import (
    AS_OF_OPERATIONS,
    COUNT_OPERATIONS,
    DOMAIN_OPERATIONS,
    GROUPED_OPERATIONS,
    MONETARY_OPERATIONS,
    PERIOD_OPERATIONS,
    MultiDomainOperation,
)
from src.onboarding.canonical import CANONICAL_MAPPING_VERSION, CanonicalMapper, CanonicalMappingSpec
from src.onboarding.ingestion import SafeFileIngestor
from src.onboarding.models import OnboardingError
from src.onboarding.profiling import DatasetProfile
from src.onboarding.registry import DatasetRegistry, REGISTRY_SCHEMA_VERSION, RegistryEntry
from src.onboarding.semantics import SemanticMapping

from .models import (
    AdapterExecutionRequest,
    AdapterOutcome,
    AdapterValidation,
    evidence_envelope,
    failure_evidence,
    validation,
)


ADAPTER_VERSION = "1.0"

_REQUIRED_ROLES = {
    MultiDomainOperation.PAYABLE_COUNT: (),
    MultiDomainOperation.PAYABLE_SUMMARY: ("AMOUNT",),
    MultiDomainOperation.PAYABLE_BY_SUPPLIER: ("AMOUNT", "SUPPLIER"),
    MultiDomainOperation.PAYABLE_BY_DUE_PERIOD: ("AMOUNT", "DUE_DATE"),
    MultiDomainOperation.PAYABLE_AGING: ("AMOUNT", "DUE_DATE", "STATUS"),
    MultiDomainOperation.OVERDUE_PAYABLE_SUMMARY: ("AMOUNT", "DUE_DATE", "STATUS"),
    MultiDomainOperation.RECEIVABLE_COUNT: (),
    MultiDomainOperation.RECEIVABLE_SUMMARY: ("AMOUNT",),
    MultiDomainOperation.RECEIVABLE_BY_CUSTOMER: ("AMOUNT", "CUSTOMER"),
    MultiDomainOperation.RECEIVABLE_BY_DUE_PERIOD: ("AMOUNT", "DUE_DATE"),
    MultiDomainOperation.RECEIVABLE_AGING: ("AMOUNT", "DUE_DATE", "STATUS"),
    MultiDomainOperation.OVERDUE_RECEIVABLE_SUMMARY: ("AMOUNT", "DUE_DATE", "STATUS"),
    MultiDomainOperation.CASH_TRANSACTION_COUNT: (),
    MultiDomainOperation.CASH_INFLOW_SUMMARY: ("AMOUNT", "CASH_DIRECTION"),
    MultiDomainOperation.CASH_OUTFLOW_SUMMARY: ("AMOUNT", "CASH_DIRECTION"),
    MultiDomainOperation.NET_CASH_BY_PERIOD: ("AMOUNT", "CASH_DIRECTION", "TRANSACTION_DATE"),
    MultiDomainOperation.CASH_BY_CATEGORY: ("AMOUNT", "CASH_DIRECTION", "CATEGORY"),
    MultiDomainOperation.CASH_BY_ACCOUNT: ("AMOUNT", "CASH_DIRECTION", "ACCOUNT"),
}


@dataclass(frozen=True, slots=True)
class _Prepared:
    entry: RegistryEntry
    profile: DatasetProfile
    mapping: SemanticMapping
    canonical_spec: CanonicalMappingSpec
    records: tuple[CanonicalFinancialRecord, ...]


class MultiDomainExecutionAdapter:
    domain = ""
    adapter_version = ADAPTER_VERSION
    canonical_model_version = CANONICAL_MAPPING_VERSION

    def __init__(self, onboarding_root: Path | str):
        self.root = Path(onboarding_root)
        self._registry = DatasetRegistry(self.root)
        self._ingestor = SafeFileIngestor(self.root)
        self._canonical = CanonicalMapper()

    @classmethod
    def supported_operations(cls):
        return DOMAIN_OPERATIONS[cls.domain]

    def validate(self, request: AdapterExecutionRequest, *, readiness_probe: bool = False) -> AdapterValidation:
        if type(readiness_probe) is not bool:
            return validation(AdapterOutcome.INVALID_REGISTRY)
        checked, prepared = self._prepare(request, readiness_probe=readiness_probe)
        if not checked.ready or not readiness_probe:
            return checked
        if not self._minimum_data(request.operation, prepared):
            return validation(AdapterOutcome.QUALITY_BLOCKER)
        return checked

    def execute(self, request: AdapterExecutionRequest) -> dict:
        checked, prepared = self._prepare(request)
        if not checked.ready:
            return failure_evidence(request, checked)
        if not self._minimum_data(request.operation, prepared):
            return failure_evidence(request, validation(AdapterOutcome.QUALITY_BLOCKER))
        try:
            calculated = self._calculate(request, prepared)
        except (ContractError, ValueError):
            return failure_evidence(request, validation(AdapterOutcome.QUALITY_BLOCKER))
        response = evidence_envelope(request)
        response.update(
            domain=self.domain,
            operation=request.operation.value,
            status=calculated["status"],
            result=calculated["result"],
            records=calculated["records"],
            quality=self._quality(prepared, calculated, request.operation),
            metadata=self._metadata(prepared, calculated, request.operation),
            limitations=[
                "Only the frozen operation and parameters were executed.",
                "No FX, inferred currency or cross-currency aggregation was applied.",
            ],
        )
        if request.operation in MONETARY_OPERATIONS:
            response["currency"] = self._currency(prepared.mapping)
        if calculated.get("no_data_reason") is not None:
            response["metadata"]["no_data_reason"] = calculated["no_data_reason"]
        return response

    def _prepare(self, request: object, *, readiness_probe: bool = False):
        if (not isinstance(request, AdapterExecutionRequest)
                or not isinstance(request.operation, MultiDomainOperation)
                or request.operation not in self.supported_operations()
                or not isinstance(request.missing_dimension, MissingDimensionPolicy)
                or not isinstance(request.granularity, PeriodGranularity)):
            return validation(AdapterOutcome.UNSUPPORTED_OPERATION), None
        if (request.operation not in GROUPED_OPERATIONS
                and request.missing_dimension is not MissingDimensionPolicy.BUCKET):
            return validation(AdapterOutcome.UNSUPPORTED_OPERATION), None
        if (request.operation not in PERIOD_OPERATIONS
                and request.granularity is not PeriodGranularity.MONTH):
            return validation(AdapterOutcome.UNSUPPORTED_OPERATION), None
        if type(request.dataset_id) is not str:
            return validation(AdapterOutcome.INVALID_REGISTRY), None
        try:
            workflow = self._registry.workflow(request.dataset_id)
            entry = self._registry.get(request.dataset_id)
            profile = self._registry.load_profile(request.dataset_id, entry.profile_digest)
            mapping = self._registry.load_mapping(
                request.dataset_id, entry.semantic_mapping_version,
                entry.semantic_mapping_digest,
            )
        except OnboardingError as error:
            outcome = AdapterOutcome.STALE_MAPPING if error.code == "artifact_mismatch" else (
                AdapterOutcome.DATASET_BLOCKED if error.code == "dataset_not_found"
                else AdapterOutcome.INVALID_REGISTRY
            )
            return validation(outcome), None
        if any((
            workflow.get("mapping_digest") != entry.semantic_mapping_digest,
            workflow.get("mapping_version") != entry.semantic_mapping_version,
            workflow.get("profile_digest") != entry.profile_digest,
            workflow.get("profile_version") != entry.profile_version,
            workflow.get("source_fingerprint") != entry.source_fingerprint,
            workflow.get("ingestion_run_id") != entry.ingestion_run_id,
            workflow.get("source_type") != entry.source_type,
            workflow.get("source_sheet") != entry.source_sheet,
        )):
            return validation(AdapterOutcome.STALE_MAPPING), None
        if (entry.registry_schema_version != REGISTRY_SCHEMA_VERSION
                or entry.canonical_domain != self.domain
                or mapping.approved_domain != self.domain):
            return validation(AdapterOutcome.DATASET_BLOCKED), None
        if mapping.status != "SEMANTICALLY_APPROVED":
            return validation(AdapterOutcome.UNRESOLVED_SEMANTICS), None
        if entry.lifecycle_state not in {"REGISTERED", "READY", "BLOCKED"}:
            return validation(AdapterOutcome.DATASET_BLOCKED), None
        roles = _REQUIRED_ROLES[request.operation]
        for role in roles:
            matches = [item for item in mapping.proposals
                       if item.proposed_role == role and item.status == "CONFIRMED"]
            if len(matches) != 1:
                return validation(AdapterOutcome.MISSING_SEMANTIC_FIELD), None
            try:
                if profile.column(matches[0].source_column).column_id != matches[0].column_id:
                    return validation(AdapterOutcome.SCHEMA_MISMATCH), None
            except KeyError:
                return validation(AdapterOutcome.SCHEMA_MISMATCH), None
        if request.operation in AS_OF_OPERATIONS:
            if (mapping.qualifiers.get("amount_basis") != "OUTSTANDING_BALANCE"
                    or mapping.qualifiers.get("dataset_reference_date") is None):
                return validation(AdapterOutcome.UNRESOLVED_SEMANTICS), None
            if request.as_of_date != mapping.qualifiers["dataset_reference_date"]:
                return validation(AdapterOutcome.REFERENCE_DATE_MISMATCH), None
            if self._value_mapping(mapping, "STATUS") is None:
                return validation(AdapterOutcome.UNRESOLVED_SEMANTICS), None
        elif request.as_of_date is not None:
            return validation(AdapterOutcome.UNSUPPORTED_OPERATION), None
        if self.domain == "CASH_TRANSACTION" and request.operation not in COUNT_OPERATIONS:
            if mapping.qualifiers.get("cash_amount_convention") not in {
                "MAGNITUDE_WITH_DIRECTION", "SIGNED_WITH_DIRECTION",
            } or self._value_mapping(mapping, "CASH_DIRECTION") is None:
                return validation(AdapterOutcome.UNRESOLVED_SEMANTICS), None
        if request.operation in MONETARY_OPERATIONS:
            if mapping.currency_state == "CONFIRMED_MULTIPLE":
                return validation(AdapterOutcome.QUALITY_BLOCKER), None
            if mapping.currency_state not in {"UNKNOWN", "CONFIRMED"}:
                return validation(AdapterOutcome.INVALID_REGISTRY), None
        try:
            dataset = self._ingestor.load(request.dataset_id, entry.ingestion_run_id)
        except OnboardingError:
            return validation(AdapterOutcome.INVALID_REGISTRY), None
        if (dataset.source_sha256 != entry.source_fingerprint
                or dataset.source_sha256 != profile.source_sha256
                or dataset.source_sheet != entry.source_sheet
                or dataset.detected_format != entry.source_type
                or dataset.row_count != entry.row_count
                or dataset.columns != tuple(column.name for column in profile.columns)):
            return validation(AdapterOutcome.SCHEMA_MISMATCH), None
        try:
            spec = self._canonical.build_spec(profile, mapping, roles=frozenset(roles))
            canonical = self._canonical.map_records_with_status(dataset, spec)
        except OnboardingError:
            return validation(AdapterOutcome.SCHEMA_MISMATCH), None
        status_map = self._value_mapping(mapping, "STATUS") or {}
        direction_map = self._value_mapping(mapping, "CASH_DIRECTION") or {}
        records = tuple(self._record(item, status_map, direction_map) for item in canonical)
        if (request.operation in AS_OF_OPERATIONS
                and any(item.settlement_status not in {"OPEN", "SETTLED", "CANCELLED"}
                        for item in records)):
            return validation(AdapterOutcome.QUALITY_BLOCKER), None
        return validation(AdapterOutcome.READY_FOR_EXECUTION), _Prepared(
            entry, profile, mapping, spec, records,
        )

    @staticmethod
    def _value_mapping(mapping: SemanticMapping, role: str):
        columns = [item.source_column for item in mapping.proposals
                   if item.proposed_role == role and item.status == "CONFIRMED"]
        if len(columns) != 1:
            return None
        for decision in reversed(mapping.decisions):
            if (decision.get("source_column") == columns[0]
                    and decision.get("approved_role") == role
                    and type(decision.get("value_mapping")) is dict):
                return decision["value_mapping"]
        return None

    @staticmethod
    def _value(item: dict, role: str):
        field = item["canonical_fields"].get(role)
        return None if field is None else field["normalized_value"]

    @staticmethod
    def _state(item: dict, role: str):
        field = item["canonical_fields"].get(role)
        return "source_missing" if field is None else field["status"]

    @staticmethod
    def _raw(item: dict, role: str):
        field = item["canonical_fields"].get(role)
        return None if field is None else field["source_value"]

    @classmethod
    def _record(cls, item, status_map, direction_map):
        status_raw = cls._raw(item, "STATUS")
        direction_raw = cls._raw(item, "CASH_DIRECTION")
        status = status_map.get(status_raw) if status_raw is not None else None
        direction = direction_map.get(direction_raw) if direction_raw is not None else None
        return CanonicalFinancialRecord(
            canonical_record_id=item["canonical_record_id"],
            source_row_number=item["lineage"]["source_row_number"],
            source_sheet=item["lineage"]["source_sheet"],
            amount=cls._value(item, "AMOUNT"), amount_status=cls._state(item, "AMOUNT"),
            amount_raw=cls._raw(item, "AMOUNT"),
            due_date=cls._value(item, "DUE_DATE"), due_date_status=cls._state(item, "DUE_DATE"),
            supplier=cls._value(item, "SUPPLIER"), supplier_status=cls._state(item, "SUPPLIER"),
            customer=cls._value(item, "CUSTOMER"), customer_status=cls._state(item, "CUSTOMER"),
            settlement_status=status,
            settlement_status_status=(cls._state(item, "STATUS") if status is not None
                                      else "invalid_semantic_mapping" if status_raw is not None
                                      else cls._state(item, "STATUS")),
            settlement_status_raw=status_raw,
            transaction_date=cls._value(item, "TRANSACTION_DATE"),
            transaction_date_status=cls._state(item, "TRANSACTION_DATE"),
            cash_direction=direction,
            cash_direction_status=(cls._state(item, "CASH_DIRECTION") if direction is not None
                                   else "invalid_semantic_mapping" if direction_raw is not None
                                   else cls._state(item, "CASH_DIRECTION")),
            cash_direction_raw=direction_raw,
            category=cls._value(item, "CATEGORY"), category_status=cls._state(item, "CATEGORY"),
            account=cls._value(item, "ACCOUNT"), account_status=cls._state(item, "ACCOUNT"),
        )

    @staticmethod
    def _minimum_data(operation, prepared):
        records = prepared.records
        if operation in COUNT_OPERATIONS:
            return bool(records)
        if operation in AS_OF_OPERATIONS:
            return any(item.settlement_status in {"OPEN", "SETTLED", "CANCELLED"} for item in records)
        if operation in {
            MultiDomainOperation.CASH_INFLOW_SUMMARY,
            MultiDomainOperation.CASH_OUTFLOW_SUMMARY,
            MultiDomainOperation.NET_CASH_BY_PERIOD,
            MultiDomainOperation.CASH_BY_CATEGORY,
            MultiDomainOperation.CASH_BY_ACCOUNT,
        }:
            convention = prepared.mapping.qualifiers["cash_amount_convention"]
            return any(cash_magnitude(item, convention)[0] is not None for item in records)
        return any(item.amount is not None for item in records)

    @staticmethod
    def _calculate(request, prepared):
        operation, records = request.operation, prepared.records
        if operation in COUNT_OPERATIONS:
            return record_count(records)
        if operation in {MultiDomainOperation.PAYABLE_SUMMARY, MultiDomainOperation.RECEIVABLE_SUMMARY}:
            return obligation_summary(records)
        if operation is MultiDomainOperation.PAYABLE_BY_SUPPLIER:
            return obligation_by_dimension(records, dimension="supplier",
                                           exclude_missing=request.missing_dimension is MissingDimensionPolicy.EXCLUDE)
        if operation is MultiDomainOperation.RECEIVABLE_BY_CUSTOMER:
            return obligation_by_dimension(records, dimension="customer",
                                           exclude_missing=request.missing_dimension is MissingDimensionPolicy.EXCLUDE)
        if operation in {MultiDomainOperation.PAYABLE_BY_DUE_PERIOD,
                         MultiDomainOperation.RECEIVABLE_BY_DUE_PERIOD}:
            return obligation_by_dimension(
                records, dimension="due_date",
                exclude_missing=request.missing_dimension is MissingDimensionPolicy.EXCLUDE,
                granularity=request.granularity.value,
            )
        if operation in {MultiDomainOperation.PAYABLE_AGING, MultiDomainOperation.RECEIVABLE_AGING}:
            return obligation_aging(records, as_of_date=request.as_of_date)
        if operation in {MultiDomainOperation.OVERDUE_PAYABLE_SUMMARY,
                         MultiDomainOperation.OVERDUE_RECEIVABLE_SUMMARY}:
            return overdue_obligation_summary(records, as_of_date=request.as_of_date)
        convention = prepared.mapping.qualifiers["cash_amount_convention"]
        if operation is MultiDomainOperation.CASH_INFLOW_SUMMARY:
            return cash_summary(records, direction="INFLOW", amount_convention=convention)
        if operation is MultiDomainOperation.CASH_OUTFLOW_SUMMARY:
            return cash_summary(records, direction="OUTFLOW", amount_convention=convention)
        if operation is MultiDomainOperation.NET_CASH_BY_PERIOD:
            return cash_by_period(
                records, granularity=request.granularity.value,
                exclude_missing=request.missing_dimension is MissingDimensionPolicy.EXCLUDE,
                amount_convention=convention,
            )
        if operation is MultiDomainOperation.CASH_BY_CATEGORY:
            return cash_by_dimension(records, dimension="category",
                                     exclude_missing=request.missing_dimension is MissingDimensionPolicy.EXCLUDE,
                                     amount_convention=convention)
        if operation is MultiDomainOperation.CASH_BY_ACCOUNT:
            return cash_by_dimension(records, dimension="account",
                                     exclude_missing=request.missing_dimension is MissingDimensionPolicy.EXCLUDE,
                                     amount_convention=convention)
        raise ValueError("Unsupported operation")

    @staticmethod
    def _currency(mapping):
        if mapping.currency_state == "UNKNOWN":
            return CurrencyMetadata().to_dict() | {
                "basis": "unverified_source_denomination", "conversion_applied": False,
            }
        return CurrencyMetadata(
            CurrencyStatus.CONFIRMED, mapping.confirmed_currency,
            f"approved_semantic_mapping:{mapping.mapping_version}",
        ).to_dict() | {"basis": "source_denomination", "conversion_applied": False}

    @staticmethod
    def _quality(prepared, calculated, operation):
        warnings = []
        if operation in MONETARY_OPERATIONS and prepared.mapping.currency_state == "UNKNOWN":
            warnings.append({
                "code": "currency_unknown", "field": "currency", "scope": "dataset",
                "affected_records": None, "message": UNKNOWN_DISCLOSURE,
                "flag_row_numbers": [],
            })
        for field, states in calculated.get("unavailable_by_field", {}).items():
            for code, count in states.items():
                if count:
                    warnings.append({
                        "code": code, "field": field, "scope": "record",
                        "affected_records": count,
                        "message": "Unavailable source values were excluded or bucketed under the closed policy.",
                        "flag_row_numbers": [],
                    })
        return {"warnings": warnings, "flags": [], "detail": "summary"}

    def _metadata(self, prepared, calculated, operation):
        participation = calculated["participation"]
        return {
            "adapter": {"domain": self.domain, "version": self.adapter_version},
            "catalog_version": "2.0",
            "value_basis": "approved_onboarded_source_records",
            "semantic_qualifiers": dict(prepared.mapping.qualifiers),
            "arithmetic": arithmetic_metadata(),
            "lineage": {
                "dataset_id": prepared.entry.dataset_id,
                "registry_version": prepared.entry.registry_version,
                "registry_digest": prepared.entry.entry_digest,
                "profile_version": prepared.entry.profile_version,
                "profile_digest": prepared.entry.profile_digest,
                "semantic_mapping_version": prepared.entry.semantic_mapping_version,
                "semantic_mapping_digest": prepared.entry.semantic_mapping_digest,
                "canonical_model_version": prepared.canonical_spec.version,
                "canonical_spec_digest": prepared.canonical_spec.spec_digest,
                "source_fingerprint": prepared.entry.source_fingerprint,
                "source_sheet": prepared.entry.source_sheet,
                "operation": operation.value,
                "records": [{
                    "canonical_record_id": item.canonical_record_id,
                    "source_row_number": item.source_row_number,
                    "source_amount": item.amount_raw,
                    "normalized_amount": item.amount,
                    "source_status": item.settlement_status_raw,
                    "mapped_status": item.settlement_status,
                    "source_cash_direction": item.cash_direction_raw,
                    "mapped_cash_direction": item.cash_direction,
                    "participation": participation[item.canonical_record_id][0],
                    "exclusion_reason": participation[item.canonical_record_id][1],
                } for item in prepared.records],
            },
        }


class PayableExecutionAdapter(MultiDomainExecutionAdapter):
    domain = "PAYABLE"


class ReceivableExecutionAdapter(MultiDomainExecutionAdapter):
    domain = "RECEIVABLE"


class CashTransactionExecutionAdapter(MultiDomainExecutionAdapter):
    domain = "CASH_TRANSACTION"
