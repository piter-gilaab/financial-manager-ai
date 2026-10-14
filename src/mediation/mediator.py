"""Natural language -> validated intent -> one existing session operation -> grounded presentation."""

from dataclasses import dataclass
import re

from src.agents.provider import ProviderLocation
from src.dynamic_anomaly import DYNAMIC_ANOMALY_OPERATIONS

from .catalog import CAPABILITY_CLARIFICATION_REQUEST
from .grounding import build_packet, locate
from .models import DynamicDatasetOption, REFERENCE_LABELS, InterpretationContext
from .presentation import (
    EVIDENCE_STATUSES, FALLBACK_NOTICE, bears_evidence, compose, deterministic_dynamic,
    outcome_text, text,
)
from .prompts import interpret_request, respond_request
from .validation import parse_intent, validate_natural_response


MAX_MEDIATED_INPUT_CHARACTERS = 2_000
DATASET_ID = re.compile(r"(?<![A-Za-z0-9_/\\])ds_[0-9a-f]{20}(?![A-Za-z0-9_/\\])")
DATASET_TOKEN = re.compile(r"(?<![A-Za-z0-9_])ds_[^\s,;]+")


@dataclass(frozen=True, slots=True)
class MediationContext:
    """Labels for the session's current anomaly handles. Navigation only, never evidence."""

    session_id: str
    labels: tuple[tuple[str, str], ...]  # (display label, session-issued handle)


@dataclass(frozen=True, slots=True)
class MediatedTurn:
    outcome: dict | None  # the session outcome, when a session operation ran
    text: str | None  # mediated presentation; None means "use the deterministic presentation"
    notice: str | None = None
    replaced_pending: bool = False
    labels: tuple[tuple[str, str], ...] = ()  # labels issued by this turn


def _pending_choices(status):
    context = status.get("active_context") if status.get("status") == "ACTIVE" else None
    pending = context.get("pending_clarification") if type(context) is dict else None
    return tuple(pending["choices"]) if type(pending) is dict else ()


class ConversationMediator:
    """One deep seam over FinancialManagerSession; the session keeps every authority it had."""

    def __init__(self, session, provider):
        self._session = session
        self._provider = provider
        self._context = None

    @property
    def session(self):
        return self._session

    def handle(self, user_text):
        status = self._session.status()
        pending = _pending_choices(status)
        replaced = bool(pending)
        labels = self._current_labels(status)
        exact_ids = tuple(dict.fromkeys(DATASET_ID.findall(user_text))) if type(user_text) is str else ()
        dataset_tokens = tuple(DATASET_TOKEN.findall(user_text)) if type(user_text) is str else ()
        normalized_tokens = tuple(
            item.rstrip(".,;:!?)]}\"'") for item in dataset_tokens
        )
        catalog = self._session.dynamic_dataset_catalog(
            candidate_id=exact_ids[0] if len(exact_ids) == 1 else None,
        )
        options = tuple(DynamicDatasetOption(
            item["dataset_id"], item["canonical_domain"], item["state"],
            tuple(item["supported_operations"]),
            item.get("anomaly_state"), tuple(item.get("supported_anomaly_operations", ())),
        ) for item in catalog["datasets"])
        available_ids = {item.dataset_id for item in options}
        dynamic = status.get("dynamic_dataset") or {}
        had_dynamic_selection = dynamic.get("dataset_id") is not None
        selected = dynamic.get("dataset_id")
        if selected not in available_ids:
            selected = None
        explicit_ids = tuple(item for item in exact_ids if item in available_ids)
        context = InterpretationContext(
            pending,
            tuple(label for label, _ in labels),
            options,
            selected,
            dynamic.get("last_operation") if selected is not None else None,
            explicit_ids,
            bool(
                dataset_tokens and (
                    len(exact_ids) != 1
                    or len(explicit_ids) != 1
                    or any(item != exact_ids[0] for item in normalized_tokens)
                )
                or catalog.get("stale_selection_cleared") and not explicit_ids
            ),
        )
        proposal = self._interpret(user_text, context)
        if proposal is None:
            if had_dynamic_selection or dataset_tokens:
                return MediatedTurn(
                    None,
                    text("pt-BR" if _looks_portuguese(user_text) else "en",
                         "dynamic_mediation_unavailable"),
                    FALLBACK_NOTICE,
                    replaced,
                )
            outcome = self._session.new_request(user_text)
            return MediatedTurn(outcome, None, FALLBACK_NOTICE, replaced, self._remember(outcome))
        turn = _Turn(user_text, proposal.response_language, proposal.presentation_hint)

        # A model cannot silently reinterpret an explicit/current dynamic target as a
        # legacy dataset request. Legacy requests remain available when named explicitly.
        request = proposal.request
        dynamic_targeted = had_dynamic_selection or selected is not None or bool(exact_ids)
        explicit_legacy = _explicit_legacy_dataset(user_text)
        legacy_redirect = (
            proposal.operation == "NEW_REQUEST"
            and (request is None or request.capability in {
                "FINANCIAL_ANALYSIS", "ANOMALY_DETECTION",
            })
        )
        if dynamic_targeted and legacy_redirect and not explicit_legacy:
            key = ("stale_dynamic_dataset" if catalog.get("stale_selection_cleared")
                   else "dynamic_mediation_unavailable")
            return MediatedTurn(None, text(turn.language, key))

        if proposal.operation == "NEW_REQUEST":
            question = user_text if proposal.use_user_text else proposal.request.text
            return self._new_request(turn, question, replaced)
        if proposal.operation == "SELECT_DYNAMIC_DATASET":
            outcome = self._session.select_dynamic_dataset(proposal.dataset_id)
            key = "dataset_selected" if outcome["status"] == "DATASET_SELECTED" else "dataset_selection_failed"
            return MediatedTurn(outcome, text(turn.language, key), replaced_pending=replaced)
        if proposal.operation == "DYNAMIC_FINANCIAL_ANALYSIS":
            outcome = self._session.execute_dynamic_financial_analysis(
                proposal.dynamic_operation,
                dataset_id=proposal.dataset_id,
                granularity=proposal.period_granularity,
                missing_dimension=proposal.missing_dimension,
            )
            return self._present(turn, outcome, replaced=replaced)
        if proposal.operation == "DYNAMIC_ANOMALY_SCREEN":
            outcome = self._session.execute_dynamic_anomaly(
                proposal.dynamic_operation, dataset_id=proposal.dataset_id,
            )
            labels = self._remember(outcome)
            return self._present(turn, outcome, labels=labels, replaced=replaced)
        if proposal.operation == "ANSWER_CLARIFICATION":
            outcome = self._session.answer(proposal.clarification_answer)
            return self._present(turn, outcome, labels=self._remember(outcome))
        if proposal.operation == "EVIDENCE_FOLLOWUP":
            handles = dict(labels)
            label = proposal.evidence_reference
            if label is None and len(handles) == 1:
                label = next(iter(handles))
            if label is None:
                return MediatedTurn(None, text(turn.language, "evidence_reference", count=len(handles)))
            outcome = self._session.follow_up(reference=handles[label], intent=proposal.follow_up_intent)
            return self._present(turn, outcome, reference=(label, proposal.follow_up_intent))
        if proposal.clarification_kind == "CAPABILITY_CHOICE":
            # The session, not the mediator, creates and owns the approved clarification.
            return self._new_request(turn, CAPABILITY_CLARIFICATION_REQUEST, replaced)
        if proposal.clarification_kind == "EVIDENCE_REFERENCE":
            key = "evidence_reference" if labels else "no_evidence_reference"
            return MediatedTurn(None, text(turn.language, key, count=len(labels)))
        if proposal.clarification_kind == "DYNAMIC_DATASET":
            choices = ", ".join(item.dataset_id for item in options)
            return MediatedTurn(None, text(turn.language, "dynamic_dataset", choices=choices))
        if proposal.clarification_kind == "DYNAMIC_ANOMALY_DEFERRED":
            return MediatedTurn(None, text(turn.language, "dynamic_anomaly_deferred"))
        return MediatedTurn(None, text(turn.language, "restate"))

    def _local_provider(self):
        # Identity check: only the LOCAL enum member qualifies; anything else fails closed.
        return getattr(self._provider, "location", None) is ProviderLocation.LOCAL

    def _interpret(self, user_text, context):
        if (not self._local_provider() or type(user_text) is not str or not user_text.strip()
                or len(user_text) > MAX_MEDIATED_INPUT_CHARACTERS):
            return None
        try:
            return parse_intent(self._provider.complete(interpret_request(user_text, context)), context)
        except Exception:
            # Provider/model failure never makes the financial system unavailable.
            return None

    def _current_labels(self, status):
        context = self._context
        active = status.get("active_context") if status.get("status") == "ACTIVE" else None
        if (context is None or status.get("session_id") != context.session_id
                or type(active) is not dict or active.get("kind") != "ANOMALY_EVIDENCE"
                or active.get("reference_count") != len(context.labels)):
            self._context = None
            return ()
        return context.labels

    def _remember(self, outcome):
        """Replace the label context with labels for this outcome's references, if any."""
        references = outcome.get("references") or []
        self._context = None
        if not references or len(references) > len(REFERENCE_LABELS):
            return ()
        labels = tuple(zip(REFERENCE_LABELS, (item["handle"] for item in references)))
        self._context = MediationContext(self._session.status()["session_id"], labels)
        return labels

    def _new_request(self, turn, question, replaced):
        outcome = self._session.new_request(question)
        return self._present(turn, outcome, labels=self._remember(outcome), replaced=replaced)

    def _present(self, turn, outcome, *, labels=(), replaced=False, reference=None):
        prefix = text(turn.language, "replaced") + "\n\n" if replaced else ""
        deterministic = MediatedTurn(outcome, None, None, replaced, labels)
        try:
            if not bears_evidence(outcome):
                if outcome.get("status") in EVIDENCE_STATUSES:
                    return deterministic  # e.g. two independent results: shown deterministically
                return MediatedTurn(outcome, prefix + outcome_text(outcome, turn.language),
                                    None, replaced, labels)
            view = locate(outcome)
            if view is None or not self._local_provider():
                return (MediatedTurn(outcome, deterministic_dynamic(view, turn.language),
                                     FALLBACK_NOTICE, replaced, labels)
                        if _is_dynamic_view(outcome, view)
                        else deterministic)
            result = outcome.get("result") or {}
            interpreted = result.get("original_request") if reference is None else None
            packet = build_packet(view, language=turn.language, question=turn.user_text,
                                  interpreted=interpreted or None,
                                  labels=tuple(label for label, _ in labels))
            response = validate_natural_response(self._provider.complete(respond_request(packet)), packet)
            allowed = packet["allowed_presentations"]
            hint = (turn.presentation_hint if turn.presentation_hint in allowed
                    else response.presentation_hint)
            body = compose(view, response.message, turn.language, hint=hint,
                           labels=tuple(label for label, _ in labels),
                           interpreted=interpreted, reference=reference)
        except Exception:
            # Ungrounded, malformed or unavailable verbalization: show nothing the model wrote.
            view = locate(outcome)
            if _is_dynamic_view(outcome, view):
                return MediatedTurn(outcome, deterministic_dynamic(view, turn.language),
                                    FALLBACK_NOTICE, replaced, labels)
            return MediatedTurn(outcome, None, FALLBACK_NOTICE, replaced, labels)
        return MediatedTurn(outcome, prefix + body, None, replaced, labels)


@dataclass(frozen=True, slots=True)
class _Turn:
    """Per-turn values from a validated intent; never stored after the turn."""

    user_text: str
    language: str
    presentation_hint: str | None


def _looks_portuguese(value):
    words = set(re.findall(r"[^\W\d_]+", value.casefold(), re.UNICODE)) if type(value) is str else set()
    return bool(words & {"usar", "dados", "vendas", "país", "mes", "mês", "lucro"})


def _explicit_legacy_dataset(value):
    normalized = " ".join(value.casefold().replace("_", " ").split()) if type(value) is str else ""
    return "receiver general" in normalized or "company financials" in normalized


def _is_dynamic_view(outcome, view):
    if view is None:
        return False
    if outcome.get("operation") in {"dynamic_financial_analysis", "dynamic_anomaly_screen"}:
        return True
    return (
        outcome.get("operation") == "follow_up"
        and view.kind == "followup"
        and type(view.detail) is dict
        and view.detail.get("operation") in DYNAMIC_ANOMALY_OPERATIONS
    )
