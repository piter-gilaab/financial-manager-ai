"""Transport-neutral commands and projections for the Phase 3 application seam."""

from dataclasses import dataclass
from enum import Enum
from pathlib import Path, PurePath, PureWindowsPath
from typing import Mapping

from src.dynamic_financial import MissingDimensionPolicy, PeriodGranularity


class ResourceNotFound(Exception):
    """A bounded application lookup failure, distinct from programming errors."""


class FinancialOperation(str, Enum):
    SALES_RECORD_COUNT = "SALES_RECORD_COUNT"
    SALES_SUMMARY = "SALES_SUMMARY"
    SALES_BY_COUNTRY = "SALES_BY_COUNTRY"
    SALES_BY_PERIOD = "SALES_BY_PERIOD"
    SALES_BY_SEGMENT = "SALES_BY_SEGMENT"
    SALES_BY_PRODUCT = "SALES_BY_PRODUCT"
    PROFIT_SUMMARY = "PROFIT_SUMMARY"
    DISCOUNT_ANALYSIS = "DISCOUNT_ANALYSIS"
    UNITS_SOLD_SUMMARY = "UNITS_SOLD_SUMMARY"
    PAYABLE_COUNT = "PAYABLE_COUNT"
    PAYABLE_SUMMARY = "PAYABLE_SUMMARY"
    PAYABLE_BY_SUPPLIER = "PAYABLE_BY_SUPPLIER"
    PAYABLE_BY_DUE_PERIOD = "PAYABLE_BY_DUE_PERIOD"
    PAYABLE_AGING = "PAYABLE_AGING"
    OVERDUE_PAYABLE_SUMMARY = "OVERDUE_PAYABLE_SUMMARY"
    RECEIVABLE_COUNT = "RECEIVABLE_COUNT"
    RECEIVABLE_SUMMARY = "RECEIVABLE_SUMMARY"
    RECEIVABLE_BY_CUSTOMER = "RECEIVABLE_BY_CUSTOMER"
    RECEIVABLE_BY_DUE_PERIOD = "RECEIVABLE_BY_DUE_PERIOD"
    RECEIVABLE_AGING = "RECEIVABLE_AGING"
    OVERDUE_RECEIVABLE_SUMMARY = "OVERDUE_RECEIVABLE_SUMMARY"
    CASH_TRANSACTION_COUNT = "CASH_TRANSACTION_COUNT"
    CASH_INFLOW_SUMMARY = "CASH_INFLOW_SUMMARY"
    CASH_OUTFLOW_SUMMARY = "CASH_OUTFLOW_SUMMARY"
    NET_CASH_BY_PERIOD = "NET_CASH_BY_PERIOD"
    CASH_BY_CATEGORY = "CASH_BY_CATEGORY"
    CASH_BY_ACCOUNT = "CASH_BY_ACCOUNT"


class AnomalyOperation(str, Enum):
    SALES_ANOMALY_SCREEN = "SALES_ANOMALY_SCREEN"
    PROFIT_ANOMALY_SCREEN = "PROFIT_ANOMALY_SCREEN"


@dataclass(frozen=True, slots=True)
class DatasetUpload:
    filename: str
    content: bytes
    sheet: str | None = None
    provenance_note: str | None = None

    def extension(self) -> str:
        if (type(self.filename) is not str or not self.filename
                or len(self.filename) > 255 or not self.filename.isprintable()
                or PurePath(self.filename).name != self.filename
                or PureWindowsPath(self.filename).name != self.filename):
            return ""
        return PurePath(self.filename).suffix.lower()


@dataclass(frozen=True, slots=True)
class StagedDatasetUpload:
    """A server-controlled upload artifact; never populated from a client path."""

    filename: str
    staged_path: Path
    sheet: str | None = None
    provenance_note: str | None = None

    def extension(self) -> str:
        return DatasetUpload(self.filename, b"").extension()


@dataclass(frozen=True, slots=True)
class DatasetSummary:
    dataset_id: str
    source_filename: str
    source_type: str
    row_count: int
    column_count: int
    lifecycle_state: str
    readiness_state: str
    approved_domain: str | None
    currency_state: str
    supported_operations: tuple[str, ...]
    limitations: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ColumnProfileProjection:
    column_id: str
    name: str
    source_representation: str
    structural_type: str
    missing_count: int
    missing_percentage: str
    unique_count: int
    decimal_parse_success: int
    date_parse_success: int
    ambiguous_date_count: int
    numeric_min: str | None
    numeric_max: str | None
    decimal_scales: tuple[int, ...]
    date_min: str | None
    date_max: str | None
    categorical_cardinality: int
    examples: tuple[str, ...]
    frequencies: tuple[tuple[str, int], ...]
    possible_identifier: bool
    likely_sensitive: bool
    patterns: tuple[str, ...]
    formatting_observations: tuple[str, ...]
    confirmation_values: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class DatasetProfileProjection:
    dataset_id: str
    status: str
    profile_version: str
    profile_digest: str
    row_count: int
    column_count: int
    duplicate_row_candidates: int
    currency_state: str
    columns: tuple[ColumnProfileProjection, ...]
    bounds: Mapping[str, int]


@dataclass(frozen=True, slots=True)
class SemanticMappingProjection:
    dataset_id: str
    status: str
    mapping_version: int
    mapping_digest: str
    approved_domain: str | None
    domain_suggestions: tuple[str, ...]
    currency_state: str
    confirmed_currency: str | None
    proposals: tuple[Mapping[str, object], ...]
    decisions: tuple[Mapping[str, object], ...]
    qualifiers: Mapping[str, str]
    unresolved_requirements: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CurrencyReadinessProjection:
    state: str
    code: str | None


@dataclass(frozen=True, slots=True)
class OperationReadinessProjection:
    identifier: str
    state: str
    required_semantics: tuple[str, ...]
    reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CapabilityReadinessProjection:
    identifier: str
    state: str
    semantic_readiness: str
    policy_readiness: str
    execution_readiness: str
    reasons: tuple[str, ...]
    limitations: tuple[str, ...]
    operations: tuple[OperationReadinessProjection, ...]


@dataclass(frozen=True, slots=True)
class ReadinessProjection:
    version: str
    dataset_id: str
    canonical_domain: str | None
    mapping_digest: str
    currency: CurrencyReadinessProjection
    capabilities: tuple[CapabilityReadinessProjection, ...]


@dataclass(frozen=True, slots=True)
class AnalysisCommand:
    dataset_id: str
    operation: FinancialOperation
    granularity: PeriodGranularity | None = None
    missing_dimension: MissingDimensionPolicy | None = None
    as_of_date: str | None = None


@dataclass(frozen=True, slots=True)
class AnomalyCommand:
    dataset_id: str
    operation: AnomalyOperation


@dataclass(frozen=True, slots=True)
class ApplicationResult:
    status: str
    payload: Mapping[str, object]
    limitations: tuple[str, ...]
    errors: tuple[Mapping[str, object], ...]


@dataclass(frozen=True, slots=True)
class SessionProjection:
    session_id: str
    status: str
    created_at: str | None
    last_activity_at: str | None
    inactivity_expires_at: str | None
    absolute_expires_at: str | None
    active_context: Mapping[str, object] | None
    dynamic_dataset: Mapping[str, object] | None


@dataclass(frozen=True, slots=True)
class SessionActionResult:
    status: str
    outcome: Mapping[str, object]
    session: SessionProjection


@dataclass(frozen=True, slots=True)
class ConversationTurnResult:
    status: str
    outcome: Mapping[str, object] | None
    text: str | None
    notice: str | None
    replaced_pending: bool
    labels: tuple[str, ...]

