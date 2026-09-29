"""Local top-level classification and bounded request adapters. No execution."""

import json
import re

from src.anomaly.service import normalize_analysis

from .models import Availability, Capability, PlanStep, RoutingPlan


FA = Capability.FINANCIAL_ANALYSIS
AD = Capability.ANOMALY_DETECTION
FC = Capability.CASH_FLOW_FORECASTING
DR = Capability.DOCUMENT_RETRIEVAL


class NeedDecision(Exception):
    def __init__(self, status, code, message, field=None, choices=()):
        self.status, self.code, self.message = status, code, message
        self.field, self.choices = field, tuple(choices)


def clarify(code, message, field="question", choices=()):
    raise NeedDecision("CLARIFICATION_REQUIRED", code, message, field, choices)


def unsupported(code, message):
    raise NeedDecision("UNSUPPORTED", code, message)


def masked(text):
    """Preserve positions while keeping quoted category values out of intent tests."""
    return re.sub(r'"[^"\n]*"', lambda match: " " * len(match[0]), text)


def guard(text):
    rules = (
        (r"\b(sql|select|insert|delete|drop|update|execute|eval|exec|python|import|shell|bash|subprocess|open|upload|download)\b|__\w+__|\$\(",
         "arbitrary_execution", "Only registered financial capabilities can be requested; executable instructions and file access are unsupported."),
        (r"\b(fraud\w*|misconduct|malicious|criminal|guilt|errors?)\b|\bconfirmed anomal\w*\b",
         "unverified_claim", "The available screening identifies statistical investigation candidates; it cannot determine wrongdoing, validity or a probability of wrongdoing."),
        (r"\b(invest\w*|stocks?|crypto\w*|portfolio|trading|recommendations?)\b",
         "investment_advice_unavailable", "No investment recommendation capability is registered."),
        (r"\b(pay|transfer|edit|write|remove|create|train|fit)\b",
         "operation_unavailable", "The registered analytical capabilities do not perform mutations, payments or model training."),
        (r"\b(ignore|suppress|hide|omit)\b",
         "required_disclosures", "Routing instructions cannot suppress required evidence or disclosures."),
    )
    for pattern, code, message in rules:
        if re.search(pattern, text, re.I):
            unsupported(code, message)


def analysis_question(clause):
    # Surface-language aliases only. No dataset, field, statistic, filter or
    # RG/CF contract is selected here; all remaining language stays intact.
    text = re.sub(r"^(please\s+)?summari[sz]e\s+", r"\1Show ", clause, flags=re.I)
    return re.sub(r"^(please\s+)?what (?:were|was)\s+", r"\1What are ", text, flags=re.I)


def anomaly_request(clause):
    """Recognize only complete, unfiltered Step 14 target requests."""
    text = re.sub(r"\s+", " ", clause.strip().rstrip("?.")).casefold()
    text = re.sub(r"^please ", "", text)
    target = r"(?P<target>(?:(?:receiver general|rg|company financials|cf) )?(?:accounting amounts?|sales|profit)(?: records)?)"
    patterns = (
        r"(?:show|find|identify|detect|screen)(?: me)? (?:the )?(?:unusual|unusually high|unusually low|anomalous|outlying) " + target,
        r"(?:find|identify|detect|show|screen)(?: me)? (?:anomalies|anomaly candidates|outliers|unusual values)(?: in| for| among) " + target,
        r"screen (?:extreme )?" + target + r"(?: for (?:anomalies|anomaly candidates|outliers|unusual values))?",
        r"compare " + target + r" (?:to|with) (?:their |supported )?(?:peers|peer groups)",
    )
    match = next((m for pattern in patterns if (m := re.fullmatch(pattern, text))), None)
    if match is None:
        clarify("screening_scope_required",
                "Specify one unfiltered screening target: accounting amounts, Sales or Profit. For filters/periods use explicit ANOMALY_DETECTION execution; no modifier was discarded.",
                "screening_target", ("accounting amounts", "sales", "profit"))
    selected = match["target"]
    measure = "accounting_amount" if "accounting amount" in selected else "profit" if "profit" in selected else "sales"
    dataset = "receiver_general" if measure == "accounting_amount" else "company_financials"
    if (selected.startswith(("company financials ", "cf ")) and dataset == "receiver_general") or (
        selected.startswith(("receiver general ", "rg ")) and dataset == "company_financials"):
        unsupported("screening_domain_mismatch", "The named dataset does not support that screening measure.")
    if "unusually low" in text and dataset == "receiver_general":
        unsupported("lower_accounting_screen_unavailable", "The existing accounting baseline screens the upper tail only; lower-tail accounting screening is unavailable.")
    payload = {"analysis_version": "1.0", "dataset": dataset, "measure": measure}
    normalize_analysis(payload)  # Reuse the selected service's pure validator; no query.
    notes = ["Complete selected dataset; existing global and fixed-peer rules are returned unchanged."]
    if "unusually high" in text or "unusually low" in text:
        notes.append("Requested tail wording is retained in the original clause. The complete service response is returned without tail filtering; Sales/Profit include both tails.")
    return payload, tuple(notes)


def classify(clause, registry):
    text = masked(clause).casefold()
    if re.search(r"\b(not|instead|unless|except|then|same|those|these|them)\b|don't|rather than|based on", text):
        clarify("scope_or_dependency_unclear", "State each independent request explicitly without exclusions, negation or references to another result.")
    forecast = bool(re.search(r"\b(forecast\w*|predict\w*|project\w*)\b", text))
    documents = bool(re.search(r"\b(contracts?|invoices?|statements?|policies|policy|procedures?|reports?|pdfs?|documents?|rag)\b", text))
    screening = bool(re.search(r"\b(unusual\w*|outliers?|anomal\w*|screen\w*|peers?)\b", text))
    if sum((forecast, documents, screening)) > 1:
        clarify("overlapping_capabilities", "Separate the requested capabilities into independent clauses, or choose one purpose.")
    notes = ()
    if forecast:
        if not re.search(r"\bcash(?:[ -]flows?| balances?| inflows?| outflows?)?\b", text):
            unsupported("prediction_target_unavailable", "Only cash-flow forecasting is represented in the registry, and it is blocked; other predictive targets are unsupported.")
        capability, payload, reason = FC, {}, "cash_forecast_requested"
    elif documents:
        capability, payload, reason = DR, {}, "document_evidence_requested"
    elif screening:
        payload, notes = anomaly_request(clause)
        capability, reason = AD, "statistical_screening_requested"
    elif re.search(r"\bextrem\w*\b", text):
        clarify("extreme_meaning_ambiguous", "Do you want ranked highest/lowest records or statistical screening?", choices=("ranked records", "statistical screening"))
    elif re.search(r"\b(counts?|totals?|summar\w*|sales|profits?|discounts?|units|amounts?|accounting|receiver general|rg|cf|company|companies|revenue|expenses?|assets?|liabilities|balance|equity|currency|convert\w*|fx|margin|ratio|growth|debit|credit|cogs|records?)\b", text):
        capability, payload, reason = FA, {"question": analysis_question(clause)}, "descriptive_financial_request"
    else:
        clarify("capability_required", "Do you want a financial summary or statistical screening? State the measure and purpose.",
                "capability", (FA.value, AD.value))
    info = registry.get(capability)
    if info is None:
        unsupported("capability_not_registered", "The requested capability is not registered.")
    return PlanStep(info, clause, json.dumps(payload, ensure_ascii=False, allow_nan=False), reason, notes)


def route(question, registry):
    """Return an immutable validated top-level plan; never invoke a capability."""
    if not isinstance(question, str) or not question.strip() or len(question) > 4000:
        return RoutingPlan(question if isinstance(question, str) else None, "INVALID_REQUEST", "invalid_question",
                           "Supply a nonempty question of at most 4000 characters.")
    steps = []
    try:
        if question.count('"') % 2:
            raise NeedDecision("INVALID_REQUEST", "unbalanced_quotes", "Close quoted category values before routing.")
        visible = masked(question)
        guard(visible)
        # Split only at explicit boundaries outside quoted source values. Bare
        # 'sales and profit' and filter conjunctions stay owned by Step 13.
        separators = list(re.finditer(r";|\s+and\s+(?=(?:summari[sz]e|show|identify|detect|find|screen|compare|forecast|predict|search|retrieve)\b)", visible, re.I))
        if len(separators) > 1:
            clarify("too_many_clauses", "Use at most one financial-analysis clause and one independent screening clause.")
        clauses, start = [], 0
        for separator in separators:
            clauses.append(question[start:separator.start()].strip())
            start = separator.end()
        clauses.append(question[start:].strip())
        if any(not clause for clause in clauses):
            clarify("empty_clause", "Each separated clause must state an independent request.")
        for clause in clauses:
            steps.append(classify(clause, registry))
        if len(steps) == 2:
            if {step.capability.identifier for step in steps} != {FA, AD} or any(step.capability.status != Availability.AVAILABLE for step in steps):
                clarify("unsupported_capability_combination", "Automatic multi-capability execution supports one available analysis request and one available screening request. Submit other requests separately.")
            steps.sort(key=lambda step: step.capability.identifier != FA)
            return RoutingPlan(question, "MULTI_CAPABILITY", "independent_analysis_and_screening",
                               "Execute Financial Analysis, then Anomaly Detection, using independent clause inputs.", tuple(steps))
        step = steps[0]
        if step.capability.status != Availability.AVAILABLE:
            return RoutingPlan(question, "BLOCKED", "capability_unavailable", step.capability.reason, tuple(steps))
        return RoutingPlan(question, "ROUTED", step.reason_code, "Delegate only to the selected capability.", tuple(steps))
    except NeedDecision as decision:
        return RoutingPlan(question, decision.status, decision.code, decision.message, tuple(steps), decision.field, decision.choices)
