"""Deterministic fact catalog built from authoritative evidence. No arithmetic beyond counting/ordering."""

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation


PACKET_VERSION = "1.0"
MAX_GROUP_FACTS = 25
MAX_WARNING_FACTS = 8
MAX_QUESTION_CHARACTERS = 500
DATASETS = {"receiver_general": "Receiver General accounting records",
            "company_financials": "Company Financials sales records"}
GROUPINGS = {
    "country": "country", "segment": "segment", "product": "product", "period": "period",
    "debit_credit": "debit/credit code", "voucher_type": "voucher type",
    "department": "department", "discount_band": "discount band",
    "general_ledger_account": "general ledger account", "subledger_account": "subledger account",
    "financial_coding_block": "financial coding block", "control_data_type": "control data type",
}
PRESENTATIONS = {
    "count": ("TEXT",), "summary": ("LIST", "TEXT"), "groups": ("TABLE", "LIST", "TEXT"),
    "records": ("TABLE", "TEXT"), "screening": ("TABLE", "LIST", "TEXT"),
    "followup": ("LIST", "TEXT"),
}
# Worded so a model can echo it safely: the required disclaimers are appended by code.
TERMINOLOGY = (
    "Values summarize imported source records under an approved query; describe them only as "
    "the measures named in the facts.",
    "Currency UNKNOWN means the denomination is not established; do not name or imply any currency.",
    "CANDIDATE means a statistical screening candidate for review. NOT_SELECTED is not a validity "
    "finding; NOT_ASSESSED means the assessment could not be performed.",
)


@dataclass(frozen=True, slots=True)
class EvidenceView:
    """A located, shape-checked slice of one authoritative result. Holds references, not copies."""

    kind: str
    capability: str
    dataset: str
    evidence: dict
    grouping: str | None = None
    detail: dict | None = None


def _decimal(value):
    try:
        number = Decimal(value) if type(value) in (str, int) else None
    except InvalidOperation:
        return None
    return number if number is not None and number.is_finite() else None


def locate(outcome):
    """Return an EvidenceView for supported single results, or None (deterministic fallback)."""
    result = outcome.get("result")
    if outcome.get("operation") == "follow_up":
        if type(result) is dict and result.get("reference_type") == "ANOMALY_RECORD":
            return EvidenceView("followup", "ANOMALY_DETECTION", result["dataset"], result, detail=result)
        return None
    steps = result.get("results") if type(result) is dict else None
    if type(steps) is not list or len(steps) != 1:
        return None
    capability = steps[0]["capability"]
    delegated = steps[0]["response"].get("delegated_result")
    if capability == "ANOMALY_DETECTION":
        if type(delegated) is dict and type(delegated.get("result")) is dict:
            return EvidenceView("screening", capability, delegated["dataset"], delegated)
        return None
    evidence = delegated.get("tool_result") if type(delegated) is dict else None
    body = evidence.get("result") if type(evidence) is dict else None
    if type(body) is not dict:
        return None
    request = delegated.get("tool_request") or {}
    query = evidence.get("query_name", "")
    if "groups" in body:
        grouping = request.get("group_by") or next(
            (name for name in GROUPINGS if query.endswith("_by_" + name)), None)
        if query.endswith("_by_period"):
            grouping = "period"
        return EvidenceView("groups", capability, evidence["dataset"], evidence, grouping=grouping)
    if "items" in body:
        return EvidenceView("records", capability, evidence["dataset"], evidence)
    if "measures" in body:
        return EvidenceView("summary", capability, evidence["dataset"], evidence)
    if "record_count" in body:
        return EvidenceView("count", capability, evidence["dataset"], evidence)
    return None


def words(text):
    """Prose form of internal keys ("record_granularity" -> "record granularity")."""
    return str(text).replace("_", " ")


def record_amount(item):
    """The parsed amount of an extreme-value record (never its raw token or status)."""
    return next((item[key] for key in item
                 if key.endswith("amount") and not key.endswith(("_raw", "_status"))), None)


def quality_warnings(view):
    if view.kind == "followup":
        return view.detail.get("quality_warnings") or []
    return (view.evidence.get("quality") or {}).get("warnings") or []


def currency_status(view):
    """Read from evidence: the envelope, or the follow-up's own currency disclosure."""
    if view.kind == "followup":
        codes = {warning.get("code") for warning in quality_warnings(view)}
        return "UNKNOWN" if "currency_unknown" in codes else None
    currency = view.evidence.get("currency")
    return currency.get("status") if type(currency) is dict else None


def group_label(key):
    return "(value missing in source)" if key.get("value") is None else str(key["value"])


def ordered_groups(view):
    """Categorical groups by exact descending first-measure sum; periods keep evidence order.

    Ordering compares exact Decimal values only; it creates no new financial value.
    """
    groups = list(view.evidence["result"]["groups"])
    if view.grouping == "period":
        return groups

    def first_sum(group):
        measures = list(group["measures"].values())
        value = _decimal(measures[0].get("sum")) if measures else None
        return value is None, -(value or 0)

    return sorted(groups, key=first_sum)  # Stable: ties keep evidence order.


def screening_candidates(evidence):
    """Items with any CANDIDATE assessment, in evidence order (the order handles are issued in)."""
    return [item for item in evidence["result"]["items"]
            if any(assessment.get("status") == "CANDIDATE"
                   for assessment in item["assessments"].values())]


class _Catalog:
    def __init__(self):
        self.facts, self.warnings = [], []

    def fact(self, label, value, unit, semantic_type, source, **extra):
        if value is None:
            return
        value = str(value) if _decimal(value) is not None else words(value)
        self.facts.append({"id": f"F{len(self.facts) + 1}", "label": words(label), "value": value,
                           "unit": unit, "semantic_type": semantic_type, "source": source, **extra})

    def warning(self, label, value, source):
        self.warnings.append({"id": f"W{len(self.warnings) + 1}", "label": words(label),
                              "value": words(value), "source": source})


def _unit(evidence, measure_unit):
    if measure_unit == "monetary":
        status = (evidence.get("currency") or {}).get("status") or "UNKNOWN"
        return f"monetary amount, currency {status}"
    return measure_unit


def _records(catalog, evidence):
    records = evidence.get("records") or {}
    catalog.fact("Records available for the query", records.get("candidates"), "records", "count", "records.candidates")
    catalog.fact("Records used", records.get("used"), "records", "count", "records.used")
    if records.get("excluded"):
        catalog.fact("Records excluded", records["excluded"], "records", "count", "records.excluded")
        for reason, count in (records.get("exclusion_reasons") or {}).items():
            catalog.fact("Records excluded because of " + reason.replace(":", " ").replace("_", " "),
                         count, "records", "count", "records.exclusion_reasons")


def _coverage(catalog, body):
    coverage = body.get("measure_coverage") or {}
    entries = {"measure": coverage} if "percentage" in coverage else coverage
    for measure, values in entries.items():
        if type(values) is dict:
            catalog.fact(f"{measure.replace('_', ' ')} coverage percentage", values.get("percentage"),
                         "percent", "percentage", "result.measure_coverage")


def _measures(catalog, evidence, measures, source, prefix=""):
    for measure, facts in measures.items():
        name = measure.replace("_", " ")
        for statistic in ("count", "sum", "mean", "median", "min", "max"):
            if statistic in facts:
                unit = "records" if statistic == "count" else _unit(evidence, facts.get("unit"))
                catalog.fact(f"{prefix}{name} {statistic}", facts[statistic], unit,
                             "count" if statistic == "count" else statistic,
                             f"{source}.{measure}.{statistic}")
        coverage = facts.get("coverage") or {}
        if not prefix:
            catalog.fact(f"{name} coverage percentage", coverage.get("percentage"), "percent",
                         "percentage", f"{source}.{measure}.coverage.percentage")


def _warnings(catalog, view):
    status = currency_status(view)
    if status is not None:
        catalog.warning("Currency status", status, "currency.status")
    seen = set()
    for warning in quality_warnings(view):
        key = (warning.get("code"), warning.get("field"))
        if key in seen or key[0] == "currency_unknown" or len(catalog.warnings) >= MAX_WARNING_FACTS:
            continue
        seen.add(key)
        # Counted disclosures carry their count; descriptive ones carry their message.
        value = warning.get("affected_records")
        catalog.warning(f"Quality disclosure: {key[0]} ({warning.get('field') or 'dataset'})",
                        warning.get("message") if value is None else value, "quality.warnings")


def _assessment_text(assessment):
    tail = assessment.get("tail")
    return assessment["status"] + (f" ({tail} tail)" if tail else "")


def build_packet(view, *, language, question, interpreted, labels=()):
    """GroundedResponsePacket: the only evidence-derived data the model ever receives."""
    catalog = _Catalog()
    evidence = view.evidence
    measure = None
    if view.kind == "count":
        catalog.fact("Record count", evidence["result"]["record_count"], "records", "count", "result.record_count")
    elif view.kind == "summary":
        body = evidence["result"]
        measure = ", ".join(body["measures"])
        _measures(catalog, evidence, body["measures"], "result.measures")
        for field in ("record_count", "negative_count", "zero_count", "positive_count",
                      "unresolved_placeholder_count"):
            catalog.fact(field.replace("_", " ").capitalize(), body.get(field), "records", "count", "result." + field)
        _records(catalog, evidence)
    elif view.kind == "groups":
        groups = ordered_groups(view)
        catalog.fact("Number of groups", len(groups), "groups", "count", "result.groups")
        for rank, group in enumerate(groups[:MAX_GROUP_FACTS], 1):
            label = group_label(group["key"])
            extra = {} if view.grouping == "period" else {"rank": rank}
            for name, facts in group["measures"].items():
                for statistic in ("sum", "mean", "min", "max"):
                    if statistic in facts:
                        catalog.fact(f"{name.replace('_', ' ')} {statistic} for {label}", facts[statistic],
                                     _unit(evidence, facts.get("unit")), statistic,
                                     "result.groups[].measures", **extra)
                        extra = {}
            catalog.fact(f"Records in {label}", group.get("record_count"), "records", "count",
                         "result.groups[].record_count")
        if len(groups) > MAX_GROUP_FACTS:
            catalog.fact("Groups not listed in these facts", len(groups) - MAX_GROUP_FACTS, "groups",
                         "count", "result.groups")
        measure = ", ".join(evidence["result"].get("measure_coverage", {}))
        _coverage(catalog, evidence["result"])
        _records(catalog, evidence)
    elif view.kind == "records":
        body = evidence["result"]
        for item in body["items"][:MAX_GROUP_FACTS]:
            details = ", ".join(f"{field.replace('_', ' ')} {item[field]}" for field in (
                "effective_date", "debit_credit", "voucher_type", "department")
                if item.get(field) is not None)
            catalog.fact(f"Record ranked {item['rank']} (source row {item['source_row_number']}; {details})",
                         record_amount(item), _unit(evidence, "monetary"), "record_value",
                         "result.items[]", rank=item["rank"])
        if len(body["items"]) > MAX_GROUP_FACTS:
            catalog.fact("Records not listed in these facts", len(body["items"]) - MAX_GROUP_FACTS,
                         "records", "count", "result.items[]")
        records = evidence.get("records") or {}
        catalog.fact("Records returned", records.get("returned"), "records", "count", "records.returned")
        catalog.fact("Records not returned", records.get("not_returned"), "records", "count", "records.not_returned")
        measure = "accounting amount"
        _coverage(catalog, body)
        _records(catalog, evidence)
    elif view.kind == "screening":
        body = evidence["result"]
        measure = evidence["measure"].replace("_", " ")
        for mode in ("global", "peer"):
            for status in ("candidate", "not_selected", "not_assessed"):
                catalog.fact(f"{mode} screening {status.upper()} records", body["summary"][mode][status],
                             "records", "count", f"result.summary.{mode}.{status}")
        for field, count in body["comparison"].items():
            catalog.fact("Records " + field.replace("_", " "), count, "records", "count", "result.comparison")
        candidates = screening_candidates(evidence)
        catalog.fact("Records flagged CANDIDATE by at least one assessment", len(candidates),
                     "records", "count", "result.items[]")
        method = (evidence.get("metadata") or {}).get("method") or {}
        catalog.fact("IQR fence multiplier", method.get("multiplier"), "multiplier", "method", "metadata.method")
        catalog.fact("Minimum numeric records per reference", method.get("minimum_numeric_records"),
                     "records", "method", "metadata.method")
        for label, item in zip(labels, candidates):
            assessments = item["assessments"]
            peers = ", ".join(f"{words(name)} {value.get('value')}"
                              for name, value in (item.get("peer_values") or {}).items())
            catalog.fact(f"{label}: source row {item['lineage']['source_row_number']}, peer group {peers}; "
                         f"global {_assessment_text(assessments['global'])}, peer {_assessment_text(assessments['peer'])}",
                         item.get("observed_value"), _unit(evidence, "monetary"), "observed_value",
                         "result.items[]", reference_label=label)
        _coverage(catalog, body)
        _records(catalog, evidence)
    else:  # followup
        detail = view.detail
        measure = detail["measure"].replace("_", " ")
        lineage = detail["lineage"]
        catalog.fact("Source row", lineage.get("source_row_number"), "row", "identifier", "lineage.source_row_number")
        unit = f"monetary amount, currency {currency_status(view) or 'not stated'}"
        catalog.fact(f"Observed {measure}", detail.get("observed_value"), unit, "observed_value",
                     "observed_value")
        for name, value in (detail.get("peer_values") or {}).items():
            catalog.fact(f"Peer attribute {name.replace('_', ' ')}", value.get("value") if type(value) is dict else value,
                         "source value", "category", "peer_values")
        for mode, entry in detail["assessments"].items():
            assessment, reference = entry["assessment"], entry.get("reference") or {}
            catalog.fact(f"{mode} assessment status", _assessment_text(assessment), "status", "status",
                         f"assessments.{mode}.assessment")
            if assessment.get("reason"):
                catalog.fact(f"{mode} assessment not performed because", assessment["reason"].replace("_", " "),
                             "reason", "reason", f"assessments.{mode}.assessment.reason")
            catalog.fact(f"{mode} reference size (numeric records)", reference.get("numeric_size"), "records",
                         "count", f"assessments.{mode}.reference")
            for field in ("q1", "q3", "iqr", "lower_fence", "upper_fence"):
                catalog.fact(f"{mode} reference {field}", reference.get(field), unit, "statistic",
                             f"assessments.{mode}.reference.{field}")

    _warnings(catalog, view)
    allowed = PRESENTATIONS[view.kind]
    return {
        "packet_version": PACKET_VERSION,
        "language": language,
        "user_question": question[:MAX_QUESTION_CHARACTERS],
        "interpreted_request": interpreted,
        "capability": view.capability,
        "status": evidence.get("status", "SUCCESS"),
        "subject": {"dataset": DATASETS.get(view.dataset, view.dataset), "measure": measure,
                    "grouping": GROUPINGS.get(view.grouping) if view.grouping else None},
        "facts": catalog.facts,
        "warnings": catalog.warnings,
        "allowed_presentations": list(allowed),
        "default_presentation": allowed[0],
        "terminology": list(TERMINOLOGY),
    }
