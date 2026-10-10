"""Validated translation from Phase 13 SALES_RECORD artifacts to Financial Core."""

from dataclasses import dataclass
from pathlib import Path

from src.financial.currency import CurrencyMetadata, CurrencyStatus, UNKNOWN_DISCLOSURE
from src.financial.models import ContractError, arithmetic_metadata
from src.financial.sales_records import (
    CanonicalSalesRecord,
    discount_analysis,
    profit_summary,
    sales_by_country,
    sales_by_period,
    sales_by_product,
    sales_by_segment,
    sales_record_count,
    sales_summary,
    units_sold_summary,
)
from src.onboarding.canonical import (
    CANONICAL_MAPPING_VERSION,
    CanonicalMapper,
    CanonicalMappingSpec,
)
from src.onboarding.ingestion import SafeFileIngestor
from src.onboarding.models import OnboardingError
from src.onboarding.profiling import DatasetProfile
from src.onboarding.registry import DatasetRegistry, REGISTRY_SCHEMA_VERSION, RegistryEntry
from src.onboarding.semantics import SEMANTIC_ROLE_VALUE_KINDS, SemanticMapping

from .models import (
    AdapterExecutionRequest,
    AdapterOutcome,
    AdapterValidation,
    MissingDimensionPolicy,
    PeriodGranularity,
    SalesRecordOperation,
    evidence_envelope,
    failure_evidence,
    validation,
)


ADAPTER_VERSION = "1.0"
_REQUIRED_ROLES = {
    SalesRecordOperation.SALES_RECORD_COUNT: frozenset(),
    SalesRecordOperation.SALES_SUMMARY: frozenset({"SALES"}),
    SalesRecordOperation.SALES_BY_COUNTRY: frozenset({"SALES", "COUNTRY"}),
    SalesRecordOperation.SALES_BY_PERIOD: frozenset({"SALES", "TRANSACTION_DATE"}),
    SalesRecordOperation.SALES_BY_SEGMENT: frozenset({"SALES", "SEGMENT"}),
    SalesRecordOperation.SALES_BY_PRODUCT: frozenset({"SALES", "PRODUCT"}),
    SalesRecordOperation.PROFIT_SUMMARY: frozenset({"PROFIT"}),
    SalesRecordOperation.DISCOUNT_ANALYSIS: frozenset({"DISCOUNT"}),
    SalesRecordOperation.UNITS_SOLD_SUMMARY: frozenset({"UNITS_SOLD"}),
}
_MONETARY_OPERATIONS = frozenset({
    SalesRecordOperation.SALES_SUMMARY,
    SalesRecordOperation.SALES_BY_COUNTRY,
    SalesRecordOperation.SALES_BY_PERIOD,
    SalesRecordOperation.SALES_BY_SEGMENT,
    SalesRecordOperation.SALES_BY_PRODUCT,
    SalesRecordOperation.PROFIT_SUMMARY,
    SalesRecordOperation.DISCOUNT_ANALYSIS,
})
_STATUS_PRESERVING_OPERATIONS = frozenset({
    SalesRecordOperation.SALES_BY_PERIOD,
    SalesRecordOperation.SALES_BY_SEGMENT,
    SalesRecordOperation.SALES_BY_PRODUCT,
    SalesRecordOperation.PROFIT_SUMMARY,
    SalesRecordOperation.DISCOUNT_ANALYSIS,
    SalesRecordOperation.UNITS_SOLD_SUMMARY,
})


@dataclass(frozen=True, slots=True)
class _PreparedSalesRecords:
    entry: RegistryEntry
    profile: DatasetProfile
    mapping: SemanticMapping
    canonical_spec: CanonicalMappingSpec
    records: tuple[CanonicalSalesRecord, ...]


class SalesRecordExecutionAdapter:
    domain = "SALES_RECORD"
    adapter_version = ADAPTER_VERSION
    canonical_model_version = CANONICAL_MAPPING_VERSION

    def __init__(self, onboarding_root: Path | str):
        self.root = Path(onboarding_root)
        self._registry = DatasetRegistry(self.root)
        self._ingestor = SafeFileIngestor(self.root)
        self._canonical = CanonicalMapper()

    @staticmethod
    def supported_operations() -> tuple[SalesRecordOperation, ...]:
        return tuple(SalesRecordOperation)

    def validate(
        self,
        request: AdapterExecutionRequest,
        *,
        readiness_probe: bool = False,
    ) -> AdapterValidation:
        if type(readiness_probe) is not bool:
            return validation(AdapterOutcome.INVALID_REGISTRY)
        result, prepared = self._prepare(request, readiness_probe=readiness_probe)
        if readiness_probe and result.ready:
            if not self._has_executable_measure(request.operation, prepared.records):
                return validation(AdapterOutcome.QUALITY_BLOCKER)
            try:
                calculated = self._calculate(request, prepared.records)
            except ContractError:
                return validation(AdapterOutcome.QUALITY_BLOCKER)
            if calculated is None:
                return validation(AdapterOutcome.UNSUPPORTED_OPERATION)
        return result

    @staticmethod
    def _has_executable_measure(
        operation: SalesRecordOperation,
        records: tuple[CanonicalSalesRecord, ...],
    ) -> bool:
        if operation is SalesRecordOperation.SALES_RECORD_COUNT:
            return True
        if operation in {
            SalesRecordOperation.SALES_SUMMARY,
            SalesRecordOperation.SALES_BY_COUNTRY,
            SalesRecordOperation.SALES_BY_PERIOD,
            SalesRecordOperation.SALES_BY_SEGMENT,
            SalesRecordOperation.SALES_BY_PRODUCT,
        }:
            return any(record.sales is not None for record in records)
        if operation is SalesRecordOperation.PROFIT_SUMMARY:
            return any(record.profit is not None for record in records)
        if operation is SalesRecordOperation.DISCOUNT_ANALYSIS:
            return any(record.discount is not None for record in records)
        if operation is SalesRecordOperation.UNITS_SOLD_SUMMARY:
            return any(record.units_sold is not None for record in records)
        return False

    def execute(self, request: AdapterExecutionRequest) -> dict:
        checked, prepared = self._prepare(request)
        if not checked.ready:
            return failure_evidence(request, checked)
        try:
            calculated = self._calculate(request, prepared.records)
            if calculated is None:
                return failure_evidence(request, validation(AdapterOutcome.UNSUPPORTED_OPERATION))
        except ContractError:
            return failure_evidence(request, validation(AdapterOutcome.QUALITY_BLOCKER))
        response = evidence_envelope(request)
        response.update(
            status=calculated["status"],
            result=calculated["result"],
            records=calculated["records"],
            metadata=self._metadata(prepared, calculated),
        )
        if request.operation in _MONETARY_OPERATIONS:
            response["currency"] = self._currency(prepared)
            response["quality"] = self._quality(prepared, calculated, response["currency"])
        else:
            response["quality"] = self._quality(prepared, calculated, None)
        if calculated["no_data_reason"] is not None:
            response["metadata"]["no_data_reason"] = calculated["no_data_reason"]
        return response

    @staticmethod
    def _calculate(
        request: AdapterExecutionRequest,
        records: tuple[CanonicalSalesRecord, ...],
    ) -> dict | None:
        """Delegate one closed operation to Financial Core calculations."""
        if request.operation is SalesRecordOperation.SALES_RECORD_COUNT:
            return sales_record_count(records)
        if request.operation is SalesRecordOperation.SALES_SUMMARY:
            return sales_summary(records)
        if request.operation is SalesRecordOperation.SALES_BY_COUNTRY:
            return sales_by_country(
                records,
                exclude_missing=request.missing_dimension is MissingDimensionPolicy.EXCLUDE,
            )
        if request.operation is SalesRecordOperation.SALES_BY_PERIOD:
            return sales_by_period(
                records,
                exclude_missing=request.missing_dimension is MissingDimensionPolicy.EXCLUDE,
                granularity=request.granularity,
            )
        if request.operation is SalesRecordOperation.SALES_BY_SEGMENT:
            return sales_by_segment(
                records,
                exclude_missing=request.missing_dimension is MissingDimensionPolicy.EXCLUDE,
            )
        if request.operation is SalesRecordOperation.SALES_BY_PRODUCT:
            return sales_by_product(
                records,
                exclude_missing=request.missing_dimension is MissingDimensionPolicy.EXCLUDE,
            )
        if request.operation is SalesRecordOperation.PROFIT_SUMMARY:
            return profit_summary(records)
        if request.operation is SalesRecordOperation.DISCOUNT_ANALYSIS:
            return discount_analysis(records)
        if request.operation is SalesRecordOperation.UNITS_SOLD_SUMMARY:
            return units_sold_summary(records)
        return None

    def _prepare(
        self, request: object, *, readiness_probe: bool = False,
    ) -> tuple[AdapterValidation, _PreparedSalesRecords | None]:
        if (not isinstance(request, AdapterExecutionRequest)
                or not isinstance(request.operation, SalesRecordOperation)
                or not isinstance(request.missing_dimension, MissingDimensionPolicy)
                or not isinstance(request.granularity, PeriodGranularity)
                or request.operation not in {
                    SalesRecordOperation.SALES_BY_COUNTRY,
                    SalesRecordOperation.SALES_BY_PERIOD,
                    SalesRecordOperation.SALES_BY_SEGMENT,
                    SalesRecordOperation.SALES_BY_PRODUCT,
                }
                and request.missing_dimension is not MissingDimensionPolicy.BUCKET):
            return validation(AdapterOutcome.UNSUPPORTED_OPERATION), None
        if (request.operation is not SalesRecordOperation.SALES_BY_PERIOD
                and request.granularity is not PeriodGranularity.MONTH):
            return validation(AdapterOutcome.UNSUPPORTED_OPERATION), None
        if type(request.dataset_id) is not str:
            return validation(AdapterOutcome.INVALID_REGISTRY), None
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
            outcome = (
                AdapterOutcome.STALE_MAPPING if error.code == "artifact_mismatch"
                else AdapterOutcome.DATASET_BLOCKED if error.code == "dataset_not_found"
                else AdapterOutcome.INVALID_REGISTRY
            )
            return validation(outcome), None
        if (workflow.get("mapping_digest") != entry.semantic_mapping_digest
                or workflow.get("mapping_version") != entry.semantic_mapping_version
                or workflow.get("profile_digest") != entry.profile_digest
                or workflow.get("profile_version") != entry.profile_version
                or workflow.get("source_fingerprint") != entry.source_fingerprint
                or workflow.get("ingestion_run_id") != entry.ingestion_run_id
                or workflow.get("source_type") != entry.source_type
                or workflow.get("source_sheet") != entry.source_sheet):
            return validation(AdapterOutcome.STALE_MAPPING), None
        if entry.registry_schema_version != REGISTRY_SCHEMA_VERSION:
            return validation(AdapterOutcome.INVALID_REGISTRY), None
        if entry.canonical_domain != self.domain or mapping.approved_domain != self.domain:
            return validation(AdapterOutcome.DATASET_BLOCKED), None
        if mapping.status != "SEMANTICALLY_APPROVED":
            return validation(AdapterOutcome.UNRESOLVED_SEMANTICS), None
        if entry.lifecycle_state not in {"REGISTERED", "BLOCKED", "READY"}:
            return validation(AdapterOutcome.DATASET_BLOCKED), None
        if entry.lifecycle_state == "BLOCKED":
            analysis = next((
                item for item in entry.capability_readiness.get("capabilities", [])
                if type(item) is dict and item.get("identifier") == "FINANCIAL_ANALYSIS"
            ), None)
            pre_activation = bool(
                analysis
                and analysis.get("state") == "BLOCKED_NOT_IMPLEMENTED"
                and analysis.get("semantic_readiness") == "READY"
                and analysis.get("policy_readiness") == "READY"
            )
            revocation_probe = bool(
                readiness_probe
                and analysis
                and analysis.get("state") == "BLOCKED"
                and analysis.get("semantic_readiness") == "READY"
                and analysis.get("policy_readiness") == "READY"
            )
            if not pre_activation and not revocation_probe:
                return validation(AdapterOutcome.DATASET_BLOCKED), None
        required_roles = _REQUIRED_ROLES[request.operation]
        if (request.operation is SalesRecordOperation.DISCOUNT_ANALYSIS
                and SEMANTIC_ROLE_VALUE_KINDS.get("DISCOUNT") != "MONETARY_AMOUNT"):
            return validation(AdapterOutcome.INVALID_REGISTRY), None
        for role in required_roles:
            matches = [item for item in mapping.proposals if item.proposed_role == role]
            if not matches:
                return validation(AdapterOutcome.MISSING_SEMANTIC_FIELD), None
            if len(matches) != 1 or matches[0].status != "CONFIRMED":
                return validation(AdapterOutcome.UNRESOLVED_SEMANTICS), None
        try:
            dataset = self._ingestor.load(request.dataset_id, entry.ingestion_run_id)
        except OnboardingError:
            return validation(AdapterOutcome.INVALID_REGISTRY), None
        if (dataset.source_sha256 != entry.source_fingerprint
                or dataset.source_sha256 != profile.source_sha256
                or dataset.source_sheet != entry.source_sheet
                or dataset.detected_format != entry.source_type
                or dataset.row_count != entry.row_count
                or dataset.row_count != profile.row_count
                or dataset.columns != tuple(column.name for column in profile.columns)):
            return validation(AdapterOutcome.SCHEMA_MISMATCH), None
        columns = {column.name: column.column_id for column in profile.columns}
        if any(
            columns.get(item.source_column) != item.column_id
            for item in mapping.proposals if item.proposed_role in required_roles
        ):
            return validation(AdapterOutcome.SCHEMA_MISMATCH), None
        if request.operation in _MONETARY_OPERATIONS:
            if mapping.currency_state == "CONFIRMED_MULTIPLE":
                return validation(AdapterOutcome.QUALITY_BLOCKER), None
            if mapping.currency_state not in {"UNKNOWN", "CONFIRMED"}:
                return validation(AdapterOutcome.INVALID_REGISTRY), None
            if mapping.currency_state == "CONFIRMED":
                try:
                    CurrencyMetadata(
                        CurrencyStatus.CONFIRMED,
                        mapping.confirmed_currency,
                        f"approved_semantic_mapping:{mapping.mapping_version}",
                    )
                except ValueError:
                    return validation(AdapterOutcome.INVALID_REGISTRY), None
        try:
            spec = self._canonical.build_spec(profile, mapping, roles=required_roles)
            if request.operation in _STATUS_PRESERVING_OPERATIONS:
                canonical = self._canonical.map_records_with_status(dataset, spec)
            else:
                canonical = self._canonical.map_records(dataset, spec)
        except OnboardingError as error:
            outcome = (
                AdapterOutcome.QUALITY_BLOCKER
                if error.code == "canonical_parse_failure"
                else AdapterOutcome.SCHEMA_MISMATCH
            )
            return validation(outcome), None
        records = tuple(CanonicalSalesRecord(
            canonical_record_id=record["canonical_record_id"],
            source_row_number=record["lineage"]["source_row_number"],
            source_sheet=record["lineage"]["source_sheet"],
            sales=self._field(record, "SALES"),
            sales_status=self._field_status(record, "SALES"),
            country=self._field(record, "COUNTRY"),
            country_status=self._field_status(record, "COUNTRY"),
            transaction_date=self._field(record, "TRANSACTION_DATE"),
            transaction_date_status=self._field_status(record, "TRANSACTION_DATE"),
            segment=self._field(record, "SEGMENT"),
            segment_status=self._field_status(record, "SEGMENT"),
            product=self._field(record, "PRODUCT"),
            product_status=self._field_status(record, "PRODUCT"),
            profit=self._field(record, "PROFIT"),
            profit_status=self._field_status(record, "PROFIT"),
            discount=self._field(record, "DISCOUNT"),
            discount_status=self._field_status(record, "DISCOUNT"),
            units_sold=self._field(record, "UNITS_SOLD"),
            units_sold_status=self._field_status(record, "UNITS_SOLD"),
        ) for record in canonical)
        return validation(AdapterOutcome.READY_FOR_EXECUTION), _PreparedSalesRecords(
            entry, profile, mapping, spec, records,
        )

    @staticmethod
    def _field(record: dict, role: str):
        value = record["canonical_fields"].get(role)
        return None if value is None else value["normalized_value"]

    @staticmethod
    def _field_status(record: dict, role: str) -> str:
        value = record["canonical_fields"].get(role)
        if value is None:
            return "source_missing"
        if "status" in value:
            return value["status"]
        return "source_missing" if value["normalized_value"] is None else "parsed"

    @staticmethod
    def _currency(prepared: _PreparedSalesRecords) -> dict:
        mapping = prepared.mapping
        if mapping.currency_state == "UNKNOWN":
            return CurrencyMetadata().to_dict() | {
                "basis": "unverified_source_denomination",
                "conversion_applied": False,
            }
        if mapping.currency_state == "CONFIRMED":
            return CurrencyMetadata(
                status=CurrencyStatus.CONFIRMED,
                code=mapping.confirmed_currency,
                source=f"approved_semantic_mapping:{mapping.mapping_version}",
            ).to_dict() | {"basis": "source_denomination", "conversion_applied": False}
        raise ContractError(
            "DATA_QUALITY_BLOCKER", "unsupported_currency_partition",
            "Multiple denominations require an approved partition contract.",
        )

    @staticmethod
    def _quality(prepared: _PreparedSalesRecords, calculated: dict,
                 currency: dict | None) -> dict:
        warnings = []
        if currency is not None and currency["status"] == "UNKNOWN":
            warnings.append({
                "code": "currency_unknown", "field": "currency", "scope": "dataset",
                "affected_records": None, "message": UNKNOWN_DISCLOSURE,
                "flag_row_numbers": [],
            })
        if calculated.get("missing_sales"):
            warnings.append({
                "code": "source_missing", "field": "sales", "scope": "record",
                "affected_records": calculated["missing_sales"],
                "message": "Missing sales values were excluded and not replaced with zero.",
                "flag_row_numbers": [],
            })
        if calculated.get("missing_country"):
            warnings.append({
                "code": "source_missing", "field": "country", "scope": "record",
                "affected_records": calculated["missing_country"],
                "message": "Missing country labels follow the requested dimension policy.",
                "flag_row_numbers": [],
            })
        for field, statuses in calculated.get("unavailable_by_field", {}).items():
            for code, affected in sorted(statuses.items()):
                if code == "source_missing" and field in {
                    "sales", "country", "transaction_date", "segment", "product",
                }:
                    continue
                warnings.append({
                    "code": code, "field": field, "scope": "record",
                    "affected_records": affected,
                    "message": (
                        "Unavailable dimension values follow the requested dimension policy."
                        if field in {"country", "transaction_date", "segment", "product"}
                        else "Unavailable measure values were excluded and not replaced with zero."
                    ),
                    "flag_row_numbers": [],
                })
        for key, field in (
            ("missing_transaction_date", "transaction_date"),
            ("missing_segment", "segment"),
            ("missing_product", "product"),
        ):
            if calculated.get(key):
                warnings.append({
                    "code": "source_missing", "field": field, "scope": "record",
                    "affected_records": calculated[key],
                    "message": "Missing dimension values follow the requested dimension policy.",
                    "flag_row_numbers": [],
                })
        if prepared.profile.duplicate_row_candidates:
            warnings.append({
                "code": "duplicate_row_candidates", "field": None, "scope": "dataset",
                "affected_records": prepared.profile.duplicate_row_candidates,
                "message": "Possible duplicate source rows are retained in this result.",
                "flag_row_numbers": [],
            })
        return {"warnings": warnings, "flags": [], "detail": "summary"}

    def _metadata(self, prepared: _PreparedSalesRecords, calculated: dict) -> dict:
        participation = calculated["participation"]
        return {
            "adapter": {"domain": self.domain, "version": self.adapter_version},
            "value_basis": "approved_onboarded_source_records",
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
                "records": [{
                    "canonical_record_id": record.canonical_record_id,
                    "source_row_number": record.source_row_number,
                    "participation": participation[record.canonical_record_id][0],
                    "exclusion_reason": participation[record.canonical_record_id][1],
                } for record in prepared.records],
            },
        }
