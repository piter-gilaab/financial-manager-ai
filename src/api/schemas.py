"""Explicit Pydantic v2 transport contracts for /api/v1."""

from datetime import date
from enum import Enum
from typing import Annotated, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field, JsonValue, StringConstraints, field_validator, model_validator

from src.application import AnomalyOperation, FinancialOperation
from src.dynamic_financial import MissingDimensionPolicy, PeriodGranularity, dynamic_parameters_supported


DatasetId = Annotated[
    str,
    StringConstraints(strict=True, pattern=r"^ds_[0-9a-f]{20}$", min_length=23, max_length=23),
]
SessionId = Annotated[str, StringConstraints(strict=True, min_length=1, max_length=128)]
EvidenceText = Annotated[str, StringConstraints(strict=True, strip_whitespace=True, min_length=1, max_length=1000)]


class StrictSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ApiStatus(str, Enum):
    SUCCESS = "SUCCESS"
    PARTIAL = "PARTIAL"
    NO_DATA = "NO_DATA"
    INVALID_REQUEST = "INVALID_REQUEST"
    UNSUPPORTED = "UNSUPPORTED"
    BLOCKED = "BLOCKED"
    DATA_QUALITY_BLOCKER = "DATA_QUALITY_BLOCKER"
    CLARIFICATION_REQUIRED = "CLARIFICATION_REQUIRED"
    PROVIDER_UNAVAILABLE = "PROVIDER_UNAVAILABLE"
    PROVIDER_ERROR = "PROVIDER_ERROR"


class ApiError(StrictSchema):
    code: str
    field: str | None = None
    message: str


ProjectionData = TypeVar("ProjectionData")


class ProjectionEnvelope(StrictSchema, Generic[ProjectionData]):
    api_version: str = "1"
    status: str
    data: ProjectionData
    limitations: list[str] = Field(default_factory=list)
    errors: list[ApiError] = Field(default_factory=list)


class ExecutionEnvelope(StrictSchema):
    api_version: str = "1"
    status: str
    evidence: JsonValue = Field(
        description=("Complete authoritative Manager evidence. Every Decimal value is encoded "
                     "as an exact base-10 JSON string; counts remain integers."),
    )
    limitations: list[str] = Field(default_factory=list)
    errors: list[ApiError] = Field(default_factory=list)


class ErrorEnvelope(StrictSchema):
    api_version: str = "1"
    status: str
    data: None = None
    limitations: list[str] = Field(default_factory=list)
    errors: list[ApiError]


ERROR_RESPONSES = {
    400: {"model": ErrorEnvelope, "description": "Closed request is invalid or unsupported."},
    404: {"model": ErrorEnvelope, "description": "Exact local resource was not found."},
    409: {"model": ErrorEnvelope, "description": "Known blocked or clarification outcome."},
    422: {"model": ErrorEnvelope, "description": "Transport schema validation failed."},
    500: {"model": ErrorEnvelope, "description": "Safe unexpected internal failure."},
}


class HealthData(StrictSchema):
    status: str
    api_version: str
    product_version: str


class DatasetSummaryResponse(StrictSchema):
    dataset_id: DatasetId
    source_filename: str
    source_type: str
    row_count: int
    column_count: int
    lifecycle_state: str
    readiness_state: str
    approved_domain: str | None
    currency_state: str
    supported_operations: list[str]
    limitations: list[str]


class ColumnProfileResponse(StrictSchema):
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
    decimal_scales: list[int]
    date_min: str | None
    date_max: str | None
    categorical_cardinality: int
    examples: list[str]
    frequencies: list[tuple[str, int]]
    possible_identifier: bool
    likely_sensitive: bool
    patterns: list[str]
    formatting_observations: list[str]
    confirmation_values: list[str]


class DatasetProfileResponse(StrictSchema):
    dataset_id: DatasetId
    status: str
    profile_version: str
    profile_digest: str
    row_count: int
    column_count: int
    duplicate_row_candidates: int
    currency_state: str
    columns: list[ColumnProfileResponse]
    bounds: dict[str, int]


class SemanticProposalResponse(StrictSchema):
    source_column: str
    column_id: str
    proposed_role: str | None
    status: str
    confidence: str
    rationale: str
    confirmation_required: bool
    conflicts: list[str]
    alternatives: list[str]
    authority_source: str | None
    structural_type: str
    observed_values: list[str]
    approved_format: str | None


class SemanticDecisionResponse(StrictSchema):
    approved_role: str | None
    authority_source: str
    column_id: str
    date_format: str | None
    decision: str
    evidence: str
    mapping_version: int
    previous_proposal: SemanticProposalResponse | None
    source_column: str
    timestamp: str
    value_mapping: dict[str, str] | None


class DomainDecisionResponse(StrictSchema):
    approved_domain: str
    authority_source: str
    decision: str
    evidence: str
    mapping_version: int
    previous_domain: str | None
    timestamp: str


class QualifierDecisionResponse(StrictSchema):
    authority_source: str
    decision: str
    evidence: str
    mapping_version: int
    qualifiers: dict[str, str]
    timestamp: str


class SemanticMappingResponse(StrictSchema):
    dataset_id: DatasetId
    status: str
    mapping_version: int
    mapping_digest: str
    approved_domain: str | None
    domain_suggestions: list[str]
    currency_state: str
    confirmed_currency: str | None
    proposals: list[SemanticProposalResponse]
    decisions: list[SemanticDecisionResponse | DomainDecisionResponse | QualifierDecisionResponse]
    qualifiers: dict[str, str]
    unresolved_requirements: list[str]


class OnboardingResponse(StrictSchema):
    dataset: DatasetSummaryResponse
    profile: DatasetProfileResponse
    mappings: SemanticMappingResponse


class CurrencyReadinessResponse(StrictSchema):
    state: str
    code: str | None


class OperationReadinessResponse(StrictSchema):
    identifier: str
    state: str
    required_semantics: list[str]
    reasons: list[str]


class CapabilityReadinessResponse(StrictSchema):
    identifier: str
    state: str
    semantic_readiness: str
    policy_readiness: str
    execution_readiness: str
    reasons: list[str]
    limitations: list[str]
    operations: list[OperationReadinessResponse]


class ReadinessResponse(StrictSchema):
    version: str
    dataset_id: DatasetId
    canonical_domain: str | None
    mapping_digest: str
    currency: CurrencyReadinessResponse
    capabilities: list[CapabilityReadinessResponse]


class GlobalCapabilityResponse(StrictSchema):
    identifier: str
    name: str
    status: str
    reason: str | None
    documentation: list[str]
    limitations: list[str]


class CapabilityCatalogResponse(StrictSchema):
    capabilities: list[GlobalCapabilityResponse]
    financial_operations: dict[str, list[str]]
    anomaly_operations: list[str]


class PendingClarificationResponse(StrictSchema):
    source: str
    code: str
    field: str
    choices: list[str]


class ReconstructionDescriptorResponse(StrictSchema):
    kind: str


class ClarificationContextResponse(StrictSchema):
    reconstruction_descriptor: ReconstructionDescriptorResponse
    pending_clarification: PendingClarificationResponse


class EvidenceContextResponse(StrictSchema):
    kind: str
    capability: str
    dataset: str
    measure: str | list[str]
    operation: str | None
    reference_count: int


class DynamicDatasetResponse(StrictSchema):
    dataset_id: DatasetId
    last_operation: str | None


class SessionProjectionResponse(StrictSchema):
    session_id: str
    status: str
    created_at: str | None
    last_activity_at: str | None
    inactivity_expires_at: str | None
    absolute_expires_at: str | None
    active_context: ClarificationContextResponse | EvidenceContextResponse | None
    dynamic_dataset: DynamicDatasetResponse | None


class ConversationReferenceResponse(StrictSchema):
    handle: str
    kind: str


class ConversationOutcomeResponse(StrictSchema):
    conversation_version: str
    operation: str
    status: str
    result: JsonValue | None
    error: JsonValue | None
    references: list[ConversationReferenceResponse]


class SessionActionResponse(StrictSchema):
    status: str
    outcome: ConversationOutcomeResponse
    session: SessionProjectionResponse


class ConversationTurnResponse(StrictSchema):
    status: str
    outcome: ConversationOutcomeResponse | None
    text: str | None
    notice: str | None
    replaced_pending: bool
    labels: list[str]


class AnalysisParameters(StrictSchema):
    granularity: PeriodGranularity | None = None
    missing_dimension: MissingDimensionPolicy | None = None
    as_of_date: str | None = None

    @field_validator("as_of_date")
    @classmethod
    def strict_iso_date(cls, value):
        if value is None:
            return None
        try:
            if date.fromisoformat(value).isoformat() != value:
                raise ValueError
        except (TypeError, ValueError):
            raise ValueError("as_of_date must use strict YYYY-MM-DD format") from None
        return value


class AnalysisRequest(StrictSchema):
    dataset_id: DatasetId
    operation: FinancialOperation
    parameters: AnalysisParameters = Field(default_factory=AnalysisParameters)

    @model_validator(mode="after")
    def compatible_parameters(self):
        parameters = self.parameters
        if not dynamic_parameters_supported(
            self.operation.value,
            granularity=(parameters.granularity.value if parameters.granularity else None),
            missing_dimension=(parameters.missing_dimension.value if parameters.missing_dimension else None),
            as_of_date=parameters.as_of_date,
        ):
            raise ValueError("Parameters are not supported for this closed operation.")
        return self


class AnomalyRequest(StrictSchema):
    dataset_id: DatasetId
    operation: AnomalyOperation


class CanonicalDomain(str, Enum):
    ACCOUNTING_TRANSACTION = "ACCOUNTING_TRANSACTION"
    SALES_RECORD = "SALES_RECORD"
    CASH_TRANSACTION = "CASH_TRANSACTION"
    PAYABLE = "PAYABLE"
    RECEIVABLE = "RECEIVABLE"
    BUDGET_RECORD = "BUDGET_RECORD"
    BALANCE_RECORD = "BALANCE_RECORD"
    DOCUMENT_METADATA = "DOCUMENT_METADATA"


class SemanticRole(str, Enum):
    TRANSACTION_DATE = "TRANSACTION_DATE"
    POSTING_DATE = "POSTING_DATE"
    DUE_DATE = "DUE_DATE"
    AMOUNT = "AMOUNT"
    CURRENCY = "CURRENCY"
    DESCRIPTION = "DESCRIPTION"
    ACCOUNT = "ACCOUNT"
    CATEGORY = "CATEGORY"
    DEBIT_CREDIT_INDICATOR = "DEBIT_CREDIT_INDICATOR"
    VOUCHER_TYPE = "VOUCHER_TYPE"
    DEPARTMENT = "DEPARTMENT"
    ENTITY = "ENTITY"
    COUNTRY = "COUNTRY"
    SEGMENT = "SEGMENT"
    PRODUCT = "PRODUCT"
    UNITS_SOLD = "UNITS_SOLD"
    SALES = "SALES"
    PROFIT = "PROFIT"
    DISCOUNT = "DISCOUNT"
    GROSS_SALES = "GROSS_SALES"
    COGS = "COGS"
    SALE_PRICE = "SALE_PRICE"
    MANUFACTURING_PRICE = "MANUFACTURING_PRICE"
    INVOICE_ID = "INVOICE_ID"
    SUPPLIER = "SUPPLIER"
    STATUS = "STATUS"
    ACTUAL_BUDGET_INDICATOR = "ACTUAL_BUDGET_INDICATOR"
    CASH_DIRECTION = "CASH_DIRECTION"
    BALANCE = "BALANCE"
    CUSTOMER = "CUSTOMER"


class SemanticDecisionKind(str, Enum):
    CONFIRM = "CONFIRM"
    CORRECT = "CORRECT"
    REJECT = "REJECT"


class SemanticDecisionRequest(StrictSchema):
    column: Annotated[str, StringConstraints(strict=True, min_length=1, max_length=256)]
    decision: SemanticDecisionKind
    role: SemanticRole | None = None
    evidence: EvidenceText
    value_mapping: dict[str, str] | None = None
    date_format: str | None = None


class DomainConfirmationRequest(StrictSchema):
    domain: CanonicalDomain
    evidence: EvidenceText


class AmountBasis(str, Enum):
    OUTSTANDING_BALANCE = "OUTSTANDING_BALANCE"


class CashAmountConvention(str, Enum):
    MAGNITUDE_WITH_DIRECTION = "MAGNITUDE_WITH_DIRECTION"
    SIGNED_WITH_DIRECTION = "SIGNED_WITH_DIRECTION"


class QualifierConfirmationRequest(StrictSchema):
    evidence: EvidenceText
    amount_basis: AmountBasis | None = None
    dataset_reference_date: str | None = None
    cash_amount_convention: CashAmountConvention | None = None

    @field_validator("dataset_reference_date")
    @classmethod
    def strict_reference_date(cls, value):
        return AnalysisParameters.strict_iso_date(value)

    @model_validator(mode="after")
    def at_least_one_qualifier(self):
        if (self.amount_basis is None and self.dataset_reference_date is None
                and self.cash_amount_convention is None):
            raise ValueError("At least one approved qualifier is required.")
        return self


class StopDatasetRequest(StrictSchema):
    reject: bool
    evidence: EvidenceText


class SessionTurnRequest(StrictSchema):
    message: Annotated[str, StringConstraints(strict=True, strip_whitespace=True, min_length=1, max_length=2000)]


class ClarificationAnswerRequest(StrictSchema):
    value: Annotated[str, StringConstraints(strict=True, strip_whitespace=True, min_length=1, max_length=256)]


class FollowUpIntent(str, Enum):
    WHY_SELECTED = "why_selected"
    RECORD_DETAIL = "record_detail"


class FollowUpRequest(StrictSchema):
    reference: Annotated[str, StringConstraints(strict=True, min_length=1, max_length=128)]
    intent: FollowUpIntent

