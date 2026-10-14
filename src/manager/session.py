"""Bounded process-local conversation state over the stateless manager facade."""

from copy import deepcopy
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from enum import Enum
from hashlib import sha256
import json
import re
from uuid import uuid4

from src.dynamic_financial import DYNAMIC_FINANCIAL_OPERATIONS, dynamic_parameters_supported
from src.dynamic_anomaly import DYNAMIC_ANOMALY_OPERATIONS

from .agent import FinancialManagerAgent


CONVERSATION_VERSION = "1.0"
INACTIVITY_LIMIT = timedelta(minutes=30)
ABSOLUTE_LIMIT = timedelta(hours=4)
MAX_EVIDENCE_HANDLES = 10
CAPABILITY_ALIASES = {
    "financial analysis": "FINANCIAL_ANALYSIS",
    "financial summary": "FINANCIAL_ANALYSIS",
    "anomaly detection": "ANOMALY_DETECTION",
    "anomaly screening": "ANOMALY_DETECTION",
    "statistical screening": "ANOMALY_DETECTION",
    "financial_analysis": "FINANCIAL_ANALYSIS",
    "anomaly_detection": "ANOMALY_DETECTION",
}
CAPABILITY_REQUESTS = {
    "FINANCIAL_ANALYSIS": "Summarize financial data.",
    "ANOMALY_DETECTION": "Screen financial data for anomalies.",
}
DATASET_ALIASES = {
    "receiver general": "receiver_general",
    "receiver_general": "receiver_general",
    "rg": "receiver_general",
    "company financials": "company_financials",
    "company_financials": "company_financials",
    "cf": "company_financials",
}
DATASET_REQUESTS = {
    "receiver_general": "Receiver General record count",
    "company_financials": "Company Financials record count",
}
ANOMALY_REQUESTS = {
    ("receiver_general", "accounting_amount"): "Screen accounting amounts",
    ("company_financials", "sales"): "Screen sales",
    ("company_financials", "profit"): "Screen profit",
}
RECORD_COUNT_QUESTIONS = {
    "how many records are there",
    "record count",
    "number of records",
    "count records",
}
SHA256_PATTERN = re.compile(r"[0-9a-f]{64}\Z")
RUN_ID_PATTERN = re.compile(r"[0-9]{8}T[0-9]{12}Z_[0-9a-f]{8}\Z")
DATASET_ID_PATTERN = re.compile(r"ds_[0-9a-f]{20}\Z")
CANONICAL_RECORD_ID_PATTERN = re.compile(r"rec_[0-9a-f]{20}\Z")


class ReconstructionKind(str, Enum):
    CAPABILITY_CHOICE = "CAPABILITY_CHOICE"
    FINANCIAL_RECORD_COUNT = "FINANCIAL_RECORD_COUNT"


@dataclass(frozen=True, slots=True)
class PendingClarification:
    source: str
    code: str
    field: str
    choices: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ActiveContext:
    reconstruction_kind: ReconstructionKind
    pending: PendingClarification


@dataclass(frozen=True, slots=True)
class SnapshotBinding:
    approved_run_id: str
    dataset: str
    schema_sha256: str
    manifest_sha256: str
    validation_sha256: str
    flags_sha256: str
    source_sha256: str
    processed_sha256: str


@dataclass(frozen=True, slots=True)
class DynamicSnapshotBinding:
    dataset_id: str
    operation: str
    lineage_digest: str


@dataclass(frozen=True, slots=True)
class EvidenceHandle:
    handle: str
    session_id: str
    capability: str
    dataset: str
    measure: str
    record_id: str
    snapshot: SnapshotBinding | DynamicSnapshotBinding
    result_digest: str


@dataclass(frozen=True, slots=True)
class EvidenceContext:
    capability: str
    dataset: str
    measure: str
    handles: tuple[EvidenceHandle, ...]
    operation: str | None = None


@dataclass(frozen=True, slots=True)
class DynamicDatasetContext:
    dataset_id: str
    last_operation: str | None = None


@dataclass(frozen=True, slots=True)
class SessionState:
    schema_version: str
    session_id: str
    created_at: datetime
    last_activity_at: datetime
    absolute_expires_at: datetime
    active_context: ActiveContext | EvidenceContext | None = None
    dynamic_dataset: DynamicDatasetContext | None = None


def _utc_now():
    return datetime.now(timezone.utc)


def _valid_session_id(value):
    return type(value) is str and bool(value) and len(value) <= 128 and value.isprintable()


def _valid_sha256(value):
    return type(value) is str and SHA256_PATTERN.fullmatch(value) is not None


def _valid_run_id(value):
    return type(value) is str and RUN_ID_PATTERN.fullmatch(value) is not None


def _valid_optional_text(value, *, maximum=512):
    return value is None or (type(value) is str and len(value) <= maximum
                             and value.isprintable())


def _valid_anomaly_reference(reference):
    if type(reference) is not dict or set(reference) != {
            "reference_id", "peer_definition", "peer_values", "numeric_size",
            "eligibility", "reason", "q1", "q3", "iqr", "lower_fence",
            "upper_fence",
    }:
        return False
    if (not _valid_session_id(reference["reference_id"])
            or type(reference["peer_definition"]) is not list
            or any(type(value) is not str for value in reference["peer_definition"])
            or type(reference["peer_values"]) is not dict
            or type(reference["numeric_size"]) is not int
            or reference["numeric_size"] < 0):
        return False
    fences = tuple(reference[field] for field in (
        "q1", "q3", "iqr", "lower_fence", "upper_fence",
    ))
    if reference["eligibility"] == "ELIGIBLE":
        return reference["reason"] is None and all(type(value) is str for value in fences)
    if reference["eligibility"] == "NOT_ASSESSED":
        return (type(reference["reason"]) is str and bool(reference["reason"])
                and len(reference["reason"]) <= 512
                and all(value is None for value in fences))
    return False


def _validate_context(context):
    if context is None:
        return
    if type(context) is EvidenceContext:
        legacy = context.dataset in ("receiver_general", "company_financials")
        dynamic = DATASET_ID_PATTERN.fullmatch(context.dataset) is not None
        if (context.capability != "ANOMALY_DETECTION" or not (legacy or dynamic)
                or type(context.handles) is not tuple or not context.handles
                or len(context.handles) > MAX_EVIDENCE_HANDLES
                or any(type(item) is not EvidenceHandle for item in context.handles)):
            raise ValueError("Conversation evidence context is outside the approved scope.")
        if legacy and (context.operation is not None
                       or context.measure not in (("accounting_amount",)
                                                  if context.dataset == "receiver_general"
                                                  else ("sales", "profit"))):
            raise ValueError("Conversation legacy evidence context is invalid.")
        if dynamic and (context.operation not in DYNAMIC_ANOMALY_OPERATIONS
                        or context.measure not in ("SALES", "PROFIT")):
            raise ValueError("Conversation dynamic evidence context is invalid.")
        if len({item.handle for item in context.handles}) != len(context.handles):
            raise ValueError("Conversation evidence handles must be unique.")
        for item in context.handles:
            if (item.capability != context.capability
                    or item.dataset != context.dataset or item.measure != context.measure
                    or not _valid_session_id(item.handle)
                    or not _valid_session_id(item.session_id)
                    or (legacy and not _valid_sha256(item.record_id))
                    or (dynamic and CANONICAL_RECORD_ID_PATTERN.fullmatch(item.record_id) is None)
                    or not _valid_sha256(item.result_digest)
                    or (legacy and (
                        type(item.snapshot) is not SnapshotBinding
                        or item.snapshot.dataset != item.dataset
                        or not _valid_run_id(item.snapshot.approved_run_id)
                        or not all(_valid_sha256(value) for value in (
                            item.snapshot.schema_sha256, item.snapshot.manifest_sha256,
                            item.snapshot.validation_sha256, item.snapshot.flags_sha256,
                            item.snapshot.source_sha256, item.snapshot.processed_sha256,
                        ))
                    ))
                    or (dynamic and (
                        type(item.snapshot) is not DynamicSnapshotBinding
                        or item.snapshot.dataset_id != item.dataset
                        or item.snapshot.operation != context.operation
                        or not _valid_sha256(item.snapshot.lineage_digest)
                    ))):
                raise ValueError("Conversation evidence handle is invalid.")
        return
    if type(context) is not ActiveContext or type(context.pending) is not PendingClarification:
        raise ValueError("Conversation context does not match schema version 1.0.")
    expected = {
        ReconstructionKind.CAPABILITY_CHOICE: (
            "STEP_18_ROUTER", "capability_required", "capability",
            ("FINANCIAL_ANALYSIS", "ANOMALY_DETECTION"),
        ),
        ReconstructionKind.FINANCIAL_RECORD_COUNT: (
            "FINANCIAL_ANALYSIS_AGENT", "dataset_required", "dataset",
            ("receiver_general", "company_financials"),
        ),
    }
    pending = context.pending
    if expected.get(context.reconstruction_kind) != (
            pending.source, pending.code, pending.field, pending.choices):
        raise ValueError("Conversation context contains an unsupported clarification.")


def _validate_state(state):
    if type(state) is not SessionState or state.schema_version != CONVERSATION_VERSION:
        raise ValueError("Conversation state has an unsupported schema version.")
    if not _valid_session_id(state.session_id):
        raise ValueError("Conversation state contains an invalid session identifier.")
    timestamps = (state.created_at, state.last_activity_at, state.absolute_expires_at)
    if any(type(value) is not datetime or value.tzinfo is None or value.utcoffset() is None
           for value in timestamps):
        raise ValueError("Conversation state timestamps must be timezone-aware.")
    if not (state.created_at <= state.last_activity_at <= state.absolute_expires_at
            and state.absolute_expires_at == state.created_at + ABSOLUTE_LIMIT):
        raise ValueError("Conversation state lifecycle is inconsistent.")
    _validate_context(state.active_context)
    dynamic = state.dynamic_dataset
    if (dynamic is not None
            and (type(dynamic) is not DynamicDatasetContext
                 or DATASET_ID_PATTERN.fullmatch(dynamic.dataset_id) is None
                 or (dynamic.last_operation is not None
                     and dynamic.last_operation not in DYNAMIC_FINANCIAL_OPERATIONS))):
        raise ValueError("Conversation dynamic dataset context is invalid.")
    if type(state.active_context) is EvidenceContext:
        if any(item.session_id != state.session_id for item in state.active_context.handles):
            raise ValueError("Conversation evidence belongs to another session.")


def _context_dict(context):
    if context is None:
        return None
    if type(context) is EvidenceContext:
        return {
            "kind": "ANOMALY_EVIDENCE",
            "capability": context.capability,
            "dataset": context.dataset,
            "measure": context.measure,
            "operation": context.operation,
            "reference_count": len(context.handles),
        }
    pending = context.pending
    return {
        "reconstruction_descriptor": {"kind": context.reconstruction_kind.value},
        "pending_clarification": {
            "source": pending.source,
            "code": pending.code,
            "field": pending.field,
            "choices": list(pending.choices),
        },
    }


def _snapshot_dict(binding):
    if type(binding) is DynamicSnapshotBinding:
        return {
            "dataset_id": binding.dataset_id,
            "operation": binding.operation,
            "lineage_digest": binding.lineage_digest,
        }
    return {
        "approved_run_id": binding.approved_run_id,
        "dataset": binding.dataset,
        "schema_sha256": binding.schema_sha256,
        "manifest_sha256": binding.manifest_sha256,
        "validation_sha256": binding.validation_sha256,
        "flags_sha256": binding.flags_sha256,
        "source_sha256": binding.source_sha256,
        "processed_sha256": binding.processed_sha256,
    }


def _semantic_digest(evidence):
    value = deepcopy(evidence)
    snapshot = value.get("metadata", {}).get("snapshot")
    if type(snapshot) is dict:
        snapshot.pop("database_sha256", None)

    def exact_decimal(item):
        if type(item) is Decimal and item.is_finite():
            return format(item, "f")
        raise TypeError("Unsupported evidence value.")

    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                         allow_nan=False, default=exact_decimal).encode()
    return sha256(payload).hexdigest()


class FinancialManagerSession:
    """One local in-memory session; financial authority remains in delegates."""

    def __init__(self, *, manager=None, clock=None, session_id_factory=None,
                 reference_id_factory=None):
        self._manager = FinancialManagerAgent() if manager is None else manager
        self._clock = _utc_now if clock is None else clock
        self._session_id_factory = (lambda: uuid4().hex) if session_id_factory is None else session_id_factory
        self._reference_id_factory = ((lambda: "evidence-" + uuid4().hex)
                                      if reference_id_factory is None else reference_id_factory)
        self._last_observed_at = None
        self._state = None
        self._start()

    def _now(self):
        value = self._clock()
        if type(value) is not datetime or value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Conversation clocks must return timezone-aware datetime values.")
        value = value.astimezone(timezone.utc)
        if self._last_observed_at is not None and value < self._last_observed_at:
            raise ValueError("Conversation clocks must not move backward.")
        self._last_observed_at = value
        return value

    def _new_session_id(self):
        value = self._session_id_factory()
        if not _valid_session_id(value):
            raise ValueError("Session identifiers must be printable nonempty text of at most 128 characters.")
        return value

    def _new_reference_id(self):
        value = self._reference_id_factory()
        if not _valid_session_id(value):
            raise ValueError("Evidence handles must be printable nonempty text of at most 128 characters.")
        return value

    def _start(self):
        now = self._now()
        state = SessionState(
            schema_version=CONVERSATION_VERSION,
            session_id=self._new_session_id(),
            created_at=now,
            last_activity_at=now,
            absolute_expires_at=now + ABSOLUTE_LIMIT,
        )
        _validate_state(state)
        self._state = state

    def _state_condition(self):
        state = self._state
        if state is None:
            return "EXPIRED"
        try:
            _validate_state(state)
        except ValueError:
            self._state = None
            return "INCOMPATIBLE_STATE"
        now = self._now()
        if now >= state.absolute_expires_at or now >= state.last_activity_at + INACTIVITY_LIMIT:
            self._state = None
            return "EXPIRED"
        return "ACTIVE"

    def _replace_state(self, *, context, last_activity_at=None, dynamic_dataset=...):
        state = self._state
        _validate_state(state)
        next_state = replace(
            state,
            active_context=context,
            dynamic_dataset=(state.dynamic_dataset if dynamic_dataset is ... else dynamic_dataset),
            last_activity_at=state.last_activity_at if last_activity_at is None else last_activity_at,
        )
        _validate_state(next_state)
        self._state = next_state

    def _capture_clarification(self, result, question):
        clarification = result.get("clarification")
        routing = result.get("routing", {})
        if (result.get("execution_status") == "CLARIFICATION_REQUIRED"
                and routing.get("reason_code") == "capability_required"
                and clarification == {
                    "field": "capability",
                    "question": "Do you want a financial summary or statistical screening? State the measure and purpose.",
                    "choices": ["FINANCIAL_ANALYSIS", "ANOMALY_DETECTION"],
                }):
            return ActiveContext(
                ReconstructionKind.CAPABILITY_CHOICE,
                PendingClarification(
                    "STEP_18_ROUTER", "capability_required", "capability",
                    ("FINANCIAL_ANALYSIS", "ANOMALY_DETECTION"),
                ),
            )
        normalized_question = (question.strip().rstrip("?.").strip().casefold()
                               if type(question) is str else None)
        if (result.get("execution_status") == "CLARIFICATION_REQUIRED"
                and normalized_question in RECORD_COUNT_QUESTIONS
                and routing.get("reason_code") == "descriptive_financial_request"
                and clarification == {
                    "code": "dataset_required",
                    "field": "dataset",
                    "question": "Which dataset should be queried?",
                    "choices": ["receiver_general", "company_financials"],
                }):
            return ActiveContext(
                ReconstructionKind.FINANCIAL_RECORD_COUNT,
                PendingClarification(
                    "FINANCIAL_ANALYSIS_AGENT", "dataset_required", "dataset",
                    ("receiver_general", "company_financials"),
                ),
            )
        return None

    def _evidence_parts(self, result):
        steps = result.get("results") if type(result) is dict else None
        if (type(steps) is not list or len(steps) != 1 or type(steps[0]) is not dict
                or steps[0].get("capability") != "ANOMALY_DETECTION"):
            return None
        response = steps[0].get("response")
        evidence = response.get("delegated_result") if type(response) is dict else None
        if (type(evidence) is not dict or evidence.get("status") not in ("SUCCESS", "PARTIAL")
                or evidence.get("dataset") not in ("receiver_general", "company_financials")
                or type(evidence.get("result")) is not dict):
            return None
        dataset, measure = evidence["dataset"], evidence.get("measure")
        if measure not in (("accounting_amount",) if dataset == "receiver_general" else ("sales", "profit")):
            return None
        result_body = evidence["result"]
        metadata = evidence.get("metadata")
        quality = evidence.get("quality")
        if type(metadata) is not dict or type(quality) is not dict:
            return None
        items = result_body.get("items")
        references = result_body.get("references")
        warnings = quality.get("warnings")
        snapshot = metadata.get("snapshot")
        if (type(items) is not list or not items or any(type(item) is not dict for item in items)
                or type(references) is not list or any(type(item) is not dict for item in references)
                or type(warnings) is not list or any(type(item) is not dict for item in warnings)
                or type(snapshot) is not dict):
            return None
        reference_map = {item.get("reference_id"): item for item in references
                         if _valid_anomaly_reference(item)}
        if len(reference_map) != len(references):
            return None
        candidates = [item for item in items if type(item.get("assessments")) is dict
                      and any(type(assessment) is dict and assessment.get("status") == "CANDIDATE"
                              for assessment in item["assessments"].values())]
        if not candidates:
            return None
        for item in items:
            lineage = item.get("lineage")
            assessments = item.get("assessments")
            if (type(lineage) is not dict or set(lineage) != {
                    "record_id", "run_id", "source_id", "source_row_number",
                    "processed_row_number",
            } or not _valid_sha256(lineage.get("record_id"))
                    or not _valid_run_id(lineage.get("run_id"))
                    or lineage.get("source_id") != dataset or type(assessments) is not dict
                    or set(assessments) != {"global", "peer"}
                    or item.get("dataset") != dataset or item.get("measure") != measure
                    or type(lineage.get("source_row_number")) is not int
                    or lineage["source_row_number"] < 1
                    or type(lineage.get("processed_row_number")) is not int
                    or lineage["processed_row_number"] < 1
                    or type(item.get("quality_warning_indices")) is not list
                    or any(type(index) is not int or index < 0 or index >= len(warnings)
                           for index in item["quality_warning_indices"])
                    or not _valid_optional_text(item.get("observed_raw"))
                    or not _valid_optional_text(item.get("observed_value"))
                    or not _valid_optional_text(item.get("observed_status"))):
                return None
            for assessment in assessments.values():
                if (type(assessment) is not dict or set(assessment) != {
                        "status", "reason", "reference_id", "numeric_peer_size", "tail",
                } or assessment["status"] not in {
                        "CANDIDATE", "NOT_SELECTED", "NOT_ASSESSED",
                } or not _valid_optional_text(assessment["reason"])
                        or (assessment["reference_id"] is not None
                            and not _valid_session_id(assessment["reference_id"]))
                        or (assessment["numeric_peer_size"] is not None
                            and (type(assessment["numeric_peer_size"]) is not int
                                 or assessment["numeric_peer_size"] < 0))
                        or assessment["tail"] not in (None, "lower", "upper")):
                    return None
                reference_id = assessment.get("reference_id")
                if reference_id is not None and reference_id not in reference_map:
                    return None
                if assessment["status"] == "CANDIDATE" and (
                        reference_id is None or type(assessment["numeric_peer_size"]) is not int
                        or assessment["reason"] is not None
                        or assessment["tail"] not in ("lower", "upper")):
                    return None
                if assessment["status"] == "NOT_SELECTED" and (
                        reference_id is None or type(assessment["numeric_peer_size"]) is not int
                        or assessment["reason"] is not None or assessment["tail"] is not None):
                    return None
                if assessment["status"] == "NOT_ASSESSED" and (
                        type(assessment["reason"]) is not str or not assessment["reason"]
                        or assessment["tail"] is not None):
                    return None
        for item in candidates:
            if item.get("observed_status") != "parsed" or type(item.get("observed_value")) is not str:
                return None
            for assessment in item["assessments"].values():
                if assessment.get("status") != "CANDIDATE":
                    continue
                reference = reference_map.get(assessment.get("reference_id"))
                if reference is None or reference["eligibility"] != "ELIGIBLE":
                    return None
        run_ids = {item["lineage"]["run_id"] for item in items}
        source_ids = {item["lineage"]["source_id"] for item in items}
        logical_fields = ("schema_sha256", "manifest_sha256", "validation_sha256",
                          "flags_sha256", "source_sha256", "processed_sha256")
        if (len(run_ids) != 1 or None in run_ids or source_ids != {dataset}
                or any(not _valid_sha256(snapshot.get(field))
                       for field in logical_fields)):
            return None
        binding = SnapshotBinding(next(iter(run_ids)), dataset,
                                  *(snapshot[field] for field in logical_fields))
        try:
            digest = _semantic_digest(evidence)
        except (TypeError, ValueError):
            return None
        return evidence, dataset, measure, items, candidates, binding, digest

    def _capture_evidence(self, result):
        parts = self._evidence_parts(result)
        if parts is None:
            return None
        _evidence, dataset, measure, _items, candidates, binding, digest = parts
        handles = []
        for item in candidates[:MAX_EVIDENCE_HANDLES]:
            record_id = item.get("lineage", {}).get("record_id")
            if type(record_id) is not str or not record_id:
                return None
            handles.append(EvidenceHandle(
                self._new_reference_id(), self._state.session_id, "ANOMALY_DETECTION",
                dataset, measure, record_id, binding, digest,
            ))
        context = EvidenceContext("ANOMALY_DETECTION", dataset, measure, tuple(handles))
        _validate_context(context)
        return context

    def _dynamic_evidence_parts(self, result):
        evidence = result.get("delegated_result") if type(result) is dict else None
        body = evidence.get("result") if type(evidence) is dict else None
        if (result.get("execution_status") not in ("SUCCESS", "PARTIAL")
                or type(body) is not dict):
            return None
        dataset = body.get("dataset_id")
        operation = body.get("operation")
        measure = body.get("measure")
        assessments = body.get("assessments")
        candidate_references = body.get("candidate_references")
        lineage = body.get("lineage")
        reference = body.get("reference")
        quality = body.get("quality")
        if (DATASET_ID_PATTERN.fullmatch(dataset or "") is None
                or operation not in DYNAMIC_ANOMALY_OPERATIONS
                or measure not in ("SALES", "PROFIT")
                or body.get("scope") != "GLOBAL"
                or body.get("policy") != {"name": "tukey_iqr", "version": "1.0"}
                or type(assessments) is not list
                or type(candidate_references) is not list
                or type(lineage) is not dict
                or type(reference) is not dict
                or type(quality) is not dict
                or evidence.get("dataset") != dataset
                or evidence.get("query_name") != operation):
            return None
        by_id = {}
        for item in assessments:
            if (type(item) is not dict
                    or item.get("dataset_id") != dataset
                    or CANONICAL_RECORD_ID_PATTERN.fullmatch(
                        item.get("canonical_record_id") or ""
                    ) is None
                    or type(item.get("source_row_number")) is not int
                    or item["source_row_number"] < 1
                    or item.get("status") not in {
                        "CANDIDATE", "NOT_SELECTED", "NOT_ASSESSED",
                    }
                    or item.get("tail") not in (None, "lower", "upper")
                    or not _valid_optional_text(item.get("observed_value"))
                    or not _valid_optional_text(item.get("observed_raw"))
                    or not _valid_optional_text(item.get("observed_status"))
                    or type(item.get("quality_warning_indices")) is not list):
                return None
            by_id[item["canonical_record_id"]] = item
        if len(by_id) != len(assessments) or len(candidate_references) > 20:
            return None
        candidates = []
        for candidate in candidate_references:
            if (type(candidate) is not dict
                    or set(candidate) != {
                        "dataset_id", "canonical_record_id", "source_sheet",
                        "source_row_number",
                    }
                    or candidate["dataset_id"] != dataset
                    or CANONICAL_RECORD_ID_PATTERN.fullmatch(
                        candidate["canonical_record_id"]
                    ) is None
                    or type(candidate["source_row_number"]) is not int
                    or candidate["source_row_number"] < 1):
                return None
            item = by_id.get(candidate["canonical_record_id"])
            if (item is None or item.get("status") != "CANDIDATE"
                    or item.get("source_row_number") != candidate["source_row_number"]
                    or item.get("source_sheet") != candidate["source_sheet"]):
                return None
            candidates.append(item)
        expected_candidates = [
            item for item in assessments if item.get("status") == "CANDIDATE"
        ][:20]
        if ([item["canonical_record_id"] for item in candidates]
                != [item["canonical_record_id"] for item in expected_candidates]):
            return None
        try:
            binding = DynamicSnapshotBinding(
                dataset, operation, _semantic_digest(lineage),
            )
            digest = _semantic_digest(evidence)
        except (TypeError, ValueError):
            return None
        return evidence, dataset, operation, measure, assessments, candidates, binding, digest

    def _capture_dynamic_evidence(self, result):
        parts = self._dynamic_evidence_parts(result)
        if parts is None:
            return None
        _evidence, dataset, operation, measure, _items, candidates, binding, digest = parts
        if not candidates:
            return None
        handles = tuple(
            EvidenceHandle(
                self._new_reference_id(), self._state.session_id, "ANOMALY_DETECTION",
                dataset, measure, item["canonical_record_id"], binding, digest,
            )
            for item in candidates[:MAX_EVIDENCE_HANDLES]
        )
        context = EvidenceContext(
            "ANOMALY_DETECTION", dataset, measure, handles, operation,
        )
        _validate_context(context)
        return context

    def _followup_detail(self, evidence, item, binding, digest):
        references = {value.get("reference_id"): value
                      for value in evidence["result"]["references"] if type(value) is dict}
        assessments = {}
        for mode, assessment in item["assessments"].items():
            reference_id = assessment.get("reference_id") if type(assessment) is dict else None
            assessments[mode] = {
                "assessment": deepcopy(assessment),
                "reference": deepcopy(references.get(reference_id)) if reference_id is not None else None,
            }
        warnings = evidence.get("quality", {}).get("warnings", [])
        indices = item.get("quality_warning_indices", [])
        applicable = [deepcopy(warnings[index]) for index in indices
                      if type(index) is int and 0 <= index < len(warnings)]
        return {
            "reference_type": "ANOMALY_RECORD",
            "capability": "ANOMALY_DETECTION",
            "dataset": evidence["dataset"],
            "measure": evidence["measure"],
            "snapshot": _snapshot_dict(binding),
            "result_digest": digest,
            "lineage": deepcopy(item["lineage"]),
            "observed_value": item.get("observed_value"),
            "observed_raw": item.get("observed_raw"),
            "observed_status": item.get("observed_status"),
            "peer_values": deepcopy(item.get("peer_values")),
            "assessments": assessments,
            "unavailable_dependencies": deepcopy(item.get("unavailable_dependencies", [])),
            "quality_warnings": applicable,
        }

    def _dynamic_followup_detail(self, evidence, item, binding, digest):
        body = evidence["result"]
        warnings = body.get("quality", {}).get("warnings", [])
        applicable = [deepcopy(warnings[index]) for index in item["quality_warning_indices"]
                      if type(index) is int and 0 <= index < len(warnings)]
        assessment = {
            "status": item["status"],
            "reason": item.get("reason"),
            "reference_id": item.get("reference_id"),
            "numeric_peer_size": item.get("numeric_reference_size"),
            "tail": item.get("tail"),
        }
        return {
            "reference_type": "ANOMALY_RECORD",
            "capability": "ANOMALY_DETECTION",
            "dataset": body["dataset_id"],
            "measure": body["measure"].casefold(),
            "operation": body["operation"],
            "snapshot": _snapshot_dict(binding),
            "result_digest": digest,
            "lineage": {
                "canonical_record_id": item["canonical_record_id"],
                "source_sheet": item.get("source_sheet"),
                "source_row_number": item["source_row_number"],
            },
            "observed_value": item.get("observed_value"),
            "observed_raw": item.get("observed_raw"),
            "observed_status": item.get("observed_status"),
            "peer_values": {},
            "assessments": {
                "global": {
                    "assessment": assessment,
                    "reference": deepcopy(body["reference"]),
                },
            },
            "policy": deepcopy(body["policy"]),
            "currency": deepcopy(body["currency"]),
            "quality_warnings": applicable,
        }

    def _outcome(self, operation, status, result=None, *, error=None, references=()):
        return {
            "conversation_version": CONVERSATION_VERSION,
            "operation": operation,
            "status": status,
            "result": deepcopy(result),
            "error": deepcopy(error),
            "references": deepcopy(list(references)),
        }

    def new_request(self, question):
        """Start one independent request; never treat it as a pending answer."""
        if self._state_condition() != "ACTIVE":
            self._start()
        self._replace_state(context=None)
        result = self._manager.ask(question)
        context = self._capture_clarification(result, question) or self._capture_evidence(result)
        self._replace_state(context=context, last_activity_at=self._now())
        references = ({"handle": item.handle, "kind": "ANOMALY_RECORD"}
                      for item in context.handles) if type(context) is EvidenceContext else ()
        return self._outcome("new_request", result["execution_status"], result,
                             references=references)

    def select_dynamic_dataset(self, dataset_id):
        """Select one exact current eligible dataset for this session only."""
        if self._state_condition() != "ACTIVE":
            self._start()
        catalog = self._manager.dynamic_dataset_catalog(
            candidate_id=dataset_id if type(dataset_id) is str else None,
        )
        selected = next((item for item in catalog["datasets"]
                         if type(dataset_id) is str and item["dataset_id"] == dataset_id), None)
        if selected is None:
            return self._outcome("select_dynamic_dataset", "INVALID_DATASET_SELECTION", error={
                "code": "invalid_dynamic_dataset",
                "message": "Select an exact currently eligible registered dataset identifier.",
            })
        self._replace_state(
            context=None,
            dynamic_dataset=DynamicDatasetContext(dataset_id),
            last_activity_at=self._now(),
        )
        return self._outcome("select_dynamic_dataset", "DATASET_SELECTED", {
            "dataset_id": dataset_id,
            "canonical_domain": selected["canonical_domain"],
            "state": selected["state"],
            "supported_operations": list(selected["supported_operations"]),
        })

    def dynamic_dataset_catalog(self, *, candidate_id=None):
        """Return the Manager's bounded safe catalog without exposing session internals."""
        condition = self._state_condition()
        current = (
            self._state.dynamic_dataset.dataset_id
            if condition == "ACTIVE" and self._state.dynamic_dataset is not None
            else None
        )
        catalog = self._manager.dynamic_dataset_catalog(candidate_id=candidate_id or current)
        stale_selection_cleared = False
        if current is not None and candidate_id in (None, current):
            if all(item["dataset_id"] != current for item in catalog["datasets"]):
                self._replace_state(
                    context=self._state.active_context,
                    dynamic_dataset=None,
                )
                stale_selection_cleared = True
        return deepcopy(catalog | {"stale_selection_cleared": stale_selection_cleared})

    def execute_dynamic_financial_analysis(
        self, operation, *, dataset_id=None, granularity=None, missing_dimension=None,
    ):
        """Resolve one session-scoped dataset and delegate one closed dynamic operation."""
        from src.execution import DynamicQueryParameters, DynamicQueryRequest

        if self._state_condition() != "ACTIVE":
            self._start()
        if not dynamic_parameters_supported(
                operation, granularity=granularity, missing_dimension=missing_dimension):
            return self._outcome("dynamic_financial_analysis", "INVALID_DYNAMIC_REQUEST", error={
                "code": "unsupported_dynamic_parameter",
                "message": "Use one approved dynamic Financial Analysis operation and its closed parameters.",
            })

        state = self._state
        current = state.dynamic_dataset.dataset_id if state.dynamic_dataset is not None else None
        explicit = dataset_id is not None
        if explicit and (type(dataset_id) is not str
                         or DATASET_ID_PATTERN.fullmatch(dataset_id) is None):
            return self._outcome("dynamic_financial_analysis", "INVALID_DATASET_SELECTION", error={
                "code": "invalid_dynamic_dataset",
                "message": "Select an exact currently eligible registered dataset identifier.",
            })
        target = dataset_id if explicit else current
        catalog = self._manager.dynamic_dataset_catalog(candidate_id=target)
        datasets = catalog["datasets"]
        if target is not None:
            selected = next((item for item in datasets if item["dataset_id"] == target), None)
            if selected is None:
                if not explicit and current is not None:
                    self._replace_state(
                        context=None, dynamic_dataset=None, last_activity_at=self._now(),
                    )
                    return self._outcome(
                        "dynamic_financial_analysis", "STALE_DATASET_SELECTION", error={
                            "code": "stale_dynamic_dataset",
                            "message": "The selected dataset is no longer currently executable; select it again.",
                        },
                    )
                return self._outcome(
                    "dynamic_financial_analysis", "INVALID_DATASET_SELECTION", error={
                        "code": "invalid_dynamic_dataset",
                        "message": "Select an exact currently eligible registered dataset identifier.",
                    },
                )
        elif target is None:
            return self._outcome(
                "dynamic_financial_analysis", "CLARIFICATION_REQUIRED", error={
                    "code": "dynamic_dataset_required",
                    "message": "Select one exact eligible dataset before dynamic analysis.",
                    "choices": [item["dataset_id"] for item in datasets],
                },
            )

        request = DynamicQueryRequest(
            target,
            operation,
            DynamicQueryParameters(
                missing_dimension=missing_dimension,
                granularity=granularity,
            ),
        )
        result = self._manager.execute_dataset_request(request)
        next_operation = (
            operation if result["execution_status"] in {"SUCCESS", "PARTIAL", "NO_DATA"}
            else (state.dynamic_dataset.last_operation
                  if state.dynamic_dataset is not None and state.dynamic_dataset.dataset_id == target
                  else None)
        )
        self._replace_state(
            context=None,
            dynamic_dataset=DynamicDatasetContext(target, next_operation),
            last_activity_at=self._now(),
        )
        return self._outcome(
            "dynamic_financial_analysis", result["execution_status"], result,
        )

    def execute_dynamic_anomaly(self, operation, *, dataset_id=None):
        """Resolve one dataset and delegate one closed GLOBAL anomaly screen."""
        from src.anomaly.dynamic import DynamicAnomalyRequest

        if self._state_condition() != "ACTIVE":
            self._start()
        if type(operation) is not str or operation not in DYNAMIC_ANOMALY_OPERATIONS:
            return self._outcome("dynamic_anomaly_screen", "INVALID_DYNAMIC_REQUEST", error={
                "code": "unsupported_dynamic_anomaly_operation",
                "message": "Use one approved dynamic GLOBAL anomaly operation.",
            })

        state = self._state
        current = state.dynamic_dataset.dataset_id if state.dynamic_dataset is not None else None
        explicit = dataset_id is not None
        if explicit and (type(dataset_id) is not str
                         or DATASET_ID_PATTERN.fullmatch(dataset_id) is None):
            return self._outcome("dynamic_anomaly_screen", "INVALID_DATASET_SELECTION", error={
                "code": "invalid_dynamic_dataset",
                "message": "Select an exact currently eligible registered dataset identifier.",
            })
        target = dataset_id if explicit else current
        catalog = self._manager.dynamic_dataset_catalog(candidate_id=target)
        datasets = catalog["datasets"]
        if target is not None:
            selected = next((item for item in datasets if item["dataset_id"] == target), None)
            if selected is None:
                if not explicit and current is not None:
                    self._replace_state(
                        context=None, dynamic_dataset=None, last_activity_at=self._now(),
                    )
                    return self._outcome(
                        "dynamic_anomaly_screen", "STALE_DATASET_SELECTION", error={
                            "code": "stale_dynamic_dataset",
                            "message": "The selected dataset is no longer currently executable; select it again.",
                        },
                    )
                return self._outcome(
                    "dynamic_anomaly_screen", "INVALID_DATASET_SELECTION", error={
                        "code": "invalid_dynamic_dataset",
                        "message": "Select an exact currently eligible registered dataset identifier.",
                    },
                )
        else:
            return self._outcome(
                "dynamic_anomaly_screen", "CLARIFICATION_REQUIRED", error={
                    "code": "dynamic_dataset_required",
                    "message": "Select one exact eligible dataset before dynamic anomaly screening.",
                    "choices": [item["dataset_id"] for item in datasets],
                },
            )

        result = self._manager.execute_dataset_anomaly_request(
            DynamicAnomalyRequest(target, operation),
        )
        context = self._capture_dynamic_evidence(result)
        previous_operation = (
            state.dynamic_dataset.last_operation
            if state.dynamic_dataset is not None and state.dynamic_dataset.dataset_id == target
            else None
        )
        self._replace_state(
            context=context,
            dynamic_dataset=DynamicDatasetContext(target, previous_operation),
            last_activity_at=self._now(),
        )
        references = (
            {"handle": item.handle, "kind": "ANOMALY_RECORD"}
            for item in context.handles
        ) if type(context) is EvidenceContext else ()
        return self._outcome(
            "dynamic_anomaly_screen", result["execution_status"], result,
            references=references,
        )

    def answer(self, choice):
        """Resolve only the current allowlisted clarification choice."""
        condition = self._state_condition()
        if condition != "ACTIVE":
            code = "incompatible_state" if condition == "INCOMPATIBLE_STATE" else "session_expired"
            status = condition if condition == "INCOMPATIBLE_STATE" else "SESSION_EXPIRED"
            return self._outcome("answer", status, error={
                "code": code,
                "message": "The session is unavailable; start a new request.",
            })
        state = self._state
        context = state.active_context
        if type(context) is not ActiveContext:
            return self._outcome("answer", "NO_PENDING_CLARIFICATION", error={
                "code": "no_pending_clarification",
                "message": "Start a new request before answering a clarification.",
            })
        pending = context.pending
        normalized = " ".join(choice.strip().casefold().split()) if type(choice) is str else None
        if context.reconstruction_kind == ReconstructionKind.CAPABILITY_CHOICE:
            canonical = CAPABILITY_ALIASES.get(normalized, choice.strip().upper()) if normalized is not None else None
            request = CAPABILITY_REQUESTS.get(canonical)
        elif context.reconstruction_kind == ReconstructionKind.FINANCIAL_RECORD_COUNT:
            canonical = DATASET_ALIASES.get(normalized)
            request = DATASET_REQUESTS.get(canonical)
        else:  # The closed union is validated before this branch.
            canonical = request = None
        if canonical not in pending.choices or request is None:
            return self._outcome("answer", "INVALID_ANSWER", error={
                "code": "invalid_clarification_choice",
                "message": "Answer with one of the pending clarification choices.",
                "choices": list(pending.choices),
            })
        result = self._manager.ask(request)
        next_context = self._capture_clarification(result, request)
        self._replace_state(context=next_context, last_activity_at=self._now())
        return self._outcome("answer", result["execution_status"], result)

    def follow_up(self, *, reference=None, intent=None):
        """Re-resolve one session-issued anomaly record against fresh evidence."""
        condition = self._state_condition()
        if condition != "ACTIVE":
            status = condition if condition == "INCOMPATIBLE_STATE" else "SESSION_EXPIRED"
            return self._outcome("follow_up", status, error={
                "code": "incompatible_state" if condition == "INCOMPATIBLE_STATE" else "session_expired",
                "message": "The session is unavailable; start a new request.",
            })
        context = self._state.active_context
        if type(context) is not EvidenceContext:
            return self._outcome("follow_up", "NO_EVIDENCE_CONTEXT", error={
                "code": "no_evidence_context",
                "message": "Run a supported anomaly request before following an evidence reference.",
            })
        handle = next((item for item in context.handles
                       if type(reference) is str and item.handle == reference), None)
        if handle is None:
            return self._outcome("follow_up", "UNKNOWN_REFERENCE", error={
                "code": "unknown_reference",
                "message": "The evidence reference is not valid for this session context.",
            })
        if type(intent) is not str or intent not in ("why_selected", "record_detail"):
            return self._outcome("follow_up", "UNSUPPORTED_FOLLOW_UP", error={
                "code": "unsupported_follow_up",
                "message": "Use why_selected or record_detail for an issued anomaly reference.",
            })
        if context.operation is not None:
            current = self._state.dynamic_dataset
            if current is None or current.dataset_id != handle.dataset:
                return self._outcome("follow_up", "STALE_REFERENCE", error={
                    "code": "stale_reference",
                    "message": "The candidate reference does not belong to the active dataset.",
                })
            catalog = self.dynamic_dataset_catalog(candidate_id=handle.dataset)
            if all(item["dataset_id"] != handle.dataset for item in catalog["datasets"]):
                return self._outcome("follow_up", "STALE_REFERENCE", error={
                    "code": "stale_reference",
                    "message": "The selected dataset is no longer currently executable.",
                })
            from src.anomaly.dynamic import DynamicAnomalyRequest
            result = self._manager.execute_dataset_anomaly_request(
                DynamicAnomalyRequest(handle.dataset, context.operation),
            )
            parts = self._dynamic_evidence_parts(result)
            if parts is None:
                return self._outcome("follow_up", "STALE_REFERENCE", error={
                    "code": "stale_reference",
                    "message": "The original evidence can no longer be reproduced.",
                })
            evidence, dataset, operation, measure, items, _candidates, binding, digest = parts
            if (dataset != handle.dataset or operation != context.operation
                    or measure != handle.measure or binding != handle.snapshot
                    or digest != handle.result_digest):
                return self._outcome("follow_up", "STALE_REFERENCE", error={
                    "code": "stale_reference",
                    "message": "The authoritative dataset or result no longer matches the reference.",
                })
            item = next((value for value in items
                         if value.get("canonical_record_id") == handle.record_id), None)
            if item is None or item.get("status") != "CANDIDATE":
                return self._outcome("follow_up", "STALE_REFERENCE", error={
                    "code": "stale_reference",
                    "message": "The referenced candidate no longer resolves.",
                })
            detail = self._dynamic_followup_detail(evidence, item, binding, digest)
            self._replace_state(context=context, last_activity_at=self._now())
            return self._outcome("follow_up", "SUCCESS", detail)
        request = ANOMALY_REQUESTS[(handle.dataset, handle.measure)]
        result = self._manager.ask(request)
        parts = self._evidence_parts(result)
        if parts is None:
            return self._outcome("follow_up", "STALE_REFERENCE", error={
                "code": "stale_reference",
                "message": "The original evidence can no longer be reproduced.",
            })
        evidence, dataset, measure, items, _candidates, binding, digest = parts
        if (dataset != handle.dataset or measure != handle.measure
                or binding != handle.snapshot or digest != handle.result_digest):
            return self._outcome("follow_up", "STALE_REFERENCE", error={
                "code": "stale_reference",
                "message": "The authoritative snapshot or result no longer matches the reference.",
            })
        item = next((value for value in items
                     if value.get("lineage", {}).get("record_id") == handle.record_id), None)
        if item is None:
            return self._outcome("follow_up", "STALE_REFERENCE", error={
                "code": "stale_reference",
                "message": "The referenced evidence identifier no longer resolves.",
            })
        detail = self._followup_detail(evidence, item, binding, digest)
        self._replace_state(context=context, last_activity_at=self._now())
        return self._outcome("follow_up", "SUCCESS", detail)

    def cancel(self):
        """Discard the active interaction without executing a capability."""
        condition = self._state_condition()
        if condition != "ACTIVE":
            code = "incompatible_state" if condition == "INCOMPATIBLE_STATE" else "session_expired"
            status = condition if condition == "INCOMPATIBLE_STATE" else "SESSION_EXPIRED"
            return self._outcome("cancel", status, error={
                "code": code,
                "message": "The session is unavailable; no interaction remains to cancel.",
            })
        self._replace_state(context=None, dynamic_dataset=None, last_activity_at=self._now())
        return self._outcome("cancel", "CANCELLED")

    def reset(self):
        """Delete all contextual state and rotate the session identity."""
        self._start()
        return self._outcome("reset", "RESET")

    def status(self):
        condition = self._state_condition()
        state = self._state
        if condition != "ACTIVE":
            return {
                "conversation_version": CONVERSATION_VERSION,
                "session_id": None,
                "status": condition,
                "created_at": None,
                "last_activity_at": None,
                "inactivity_expires_at": None,
                "absolute_expires_at": None,
                "active_context": None,
                "dynamic_dataset": None,
            }
        return {
            "conversation_version": state.schema_version,
            "session_id": state.session_id,
            "status": "ACTIVE",
            "created_at": state.created_at.isoformat(),
            "last_activity_at": state.last_activity_at.isoformat(),
            "inactivity_expires_at": (state.last_activity_at + INACTIVITY_LIMIT).isoformat(),
            "absolute_expires_at": state.absolute_expires_at.isoformat(),
            "active_context": _context_dict(state.active_context),
            "dynamic_dataset": ({
                "dataset_id": state.dynamic_dataset.dataset_id,
                "last_operation": state.dynamic_dataset.last_operation,
            } if state.dynamic_dataset is not None else None),
        }
