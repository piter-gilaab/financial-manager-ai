"""Closed mediation vocabularies and typed, data-only mediation records."""

from dataclasses import dataclass

from src.manager.models import Capability

from .catalog import CatalogRequest


MEDIATION_VERSION = "1.0"
OPERATIONS = ("NEW_REQUEST", "ANSWER_CLARIFICATION", "EVIDENCE_FOLLOWUP", "REQUEST_CLARIFICATION")
CLARIFICATION_KINDS = ("CAPABILITY_CHOICE", "EVIDENCE_REFERENCE", "RESTATE_REQUEST")
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
class InterpretationContext:
    """What the mediator may legitimately continue: canonical choices and issued labels only."""

    pending_choices: tuple[str, ...] = ()
    reference_labels: tuple[str, ...] = ()

    def __post_init__(self):
        # Plain tuples only: a string here would turn `in` into a substring match.
        for values in (self.pending_choices, self.reference_labels):
            if type(values) is not tuple or any(type(value) is not str for value in values):
                raise ValueError("Interpretation context values must be tuples of text.")


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


@dataclass(frozen=True, slots=True)
class NaturalResponse:
    message: str
    used_fact_ids: tuple[str, ...]
    warning_fact_ids: tuple[str, ...]
    presentation_hint: str
    language: str
