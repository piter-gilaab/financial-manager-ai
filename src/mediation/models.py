"""Closed mediation vocabularies and typed, data-only mediation records."""

from dataclasses import dataclass

from src.dynamic_financial import (
    DYNAMIC_FINANCIAL_OPERATIONS, MISSING_DIMENSION_POLICIES, PERIOD_GRANULARITIES,
)
from src.dynamic_anomaly import DYNAMIC_ANOMALY_OPERATIONS
from src.manager.models import Capability

from .catalog import CatalogRequest


MEDIATION_VERSION = "1.0"
DATASET_MEDIATION_VERSION = "1.1"
CURRENT_MEDIATION_VERSION = "1.2"
LEGACY_OPERATIONS = ("NEW_REQUEST", "ANSWER_CLARIFICATION", "EVIDENCE_FOLLOWUP", "REQUEST_CLARIFICATION")
OPERATIONS = (*LEGACY_OPERATIONS, "SELECT_DYNAMIC_DATASET", "DYNAMIC_FINANCIAL_ANALYSIS",
              "DYNAMIC_ANOMALY_SCREEN")
LEGACY_CLARIFICATION_KINDS = (
    "CAPABILITY_CHOICE", "EVIDENCE_REFERENCE", "RESTATE_REQUEST",
)
DATASET_CLARIFICATION_KINDS = (
    *LEGACY_CLARIFICATION_KINDS, "DYNAMIC_DATASET", "DYNAMIC_ANOMALY_DEFERRED",
)
CLARIFICATION_KINDS = (*LEGACY_CLARIFICATION_KINDS, "DYNAMIC_DATASET")
FOLLOW_UP_INTENTS = ("why_selected", "record_detail")
PRESENTATIONS = ("TEXT", "TABLE", "LIST")
LANGUAGES = ("en", "pt-BR")
CAPABILITIES = tuple(item.value for item in Capability)
MAX_REFERENCE_LABELS = 10
REFERENCE_LABELS = tuple(f"A{index}" for index in range(1, MAX_REFERENCE_LABELS + 1))


class MediationRejected(Exception):
    """A provider proposal failed closed. The code is fixed; no provider text is kept."""

    def __init__(self, code):
        super().__init__(code)
        self.code = code


@dataclass(frozen=True, slots=True)
class DynamicDatasetOption:
    dataset_id: str
    canonical_domain: str
    state: str
    supported_operations: tuple[str, ...]
    anomaly_state: str | None = None
    supported_anomaly_operations: tuple[str, ...] = ()

    def __post_init__(self):
        if (type(self.dataset_id) is not str or type(self.canonical_domain) is not str
                or type(self.state) is not str or type(self.supported_operations) is not tuple
                or any(item not in DYNAMIC_FINANCIAL_OPERATIONS
                       for item in self.supported_operations)
                or (self.anomaly_state is not None and type(self.anomaly_state) is not str)
                or type(self.supported_anomaly_operations) is not tuple
                or any(item not in DYNAMIC_ANOMALY_OPERATIONS
                       for item in self.supported_anomaly_operations)):
            raise ValueError("Dynamic dataset option is invalid.")


@dataclass(frozen=True, slots=True)
class InterpretationContext:
    """What the mediator may legitimately continue: canonical choices and issued labels only."""

    pending_choices: tuple[str, ...] = ()
    reference_labels: tuple[str, ...] = ()
    dynamic_datasets: tuple[DynamicDatasetOption, ...] = ()
    selected_dynamic_dataset: str | None = None
    last_dynamic_operation: str | None = None
    explicit_dynamic_dataset_ids: tuple[str, ...] = ()
    invalid_dynamic_dataset_reference: bool = False

    def __post_init__(self):
        # Plain tuples only: a string here would turn `in` into a substring match.
        for values in (self.pending_choices, self.reference_labels):
            if type(values) is not tuple or any(type(value) is not str for value in values):
                raise ValueError("Interpretation context values must be tuples of text.")
        if (type(self.dynamic_datasets) is not tuple
                or any(type(value) is not DynamicDatasetOption for value in self.dynamic_datasets)
                or type(self.explicit_dynamic_dataset_ids) is not tuple
                or any(type(value) is not str for value in self.explicit_dynamic_dataset_ids)
                or type(self.invalid_dynamic_dataset_reference) is not bool):
            raise ValueError("Dynamic interpretation context is invalid.")
        identifiers = tuple(item.dataset_id for item in self.dynamic_datasets)
        if (len(set(identifiers)) != len(identifiers)
                or (self.selected_dynamic_dataset is not None
                    and self.selected_dynamic_dataset not in identifiers)
                or (self.last_dynamic_operation is not None
                    and (self.selected_dynamic_dataset is None
                         or self.last_dynamic_operation not in DYNAMIC_FINANCIAL_OPERATIONS))
                or any(value not in identifiers for value in self.explicit_dynamic_dataset_ids)):
            raise ValueError("Dynamic interpretation context is inconsistent.")


@dataclass(frozen=True, slots=True)
class MediationIntent:
    operation: str
    request: CatalogRequest | None
    use_user_text: bool
    clarification_answer: str | None
    clarification_kind: str | None
    evidence_reference: str | None
    follow_up_intent: str | None
    presentation_hint: str | None
    response_language: str
    dataset_id: str | None
    dynamic_operation: str | None
    period_granularity: str | None
    missing_dimension: str | None


@dataclass(frozen=True, slots=True)
class NaturalResponse:
    message: str
    used_fact_ids: tuple[str, ...]
    warning_fact_ids: tuple[str, ...]
    presentation_hint: str
    language: str
