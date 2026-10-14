"""Fail-closed validation of untrusted provider output."""

from decimal import Decimal, InvalidOperation
import json
import re
import unicodedata

from src.dynamic_financial import dynamic_parameters_supported

from .catalog import REQUESTS, USER_TEXT
from .models import (
    CAPABILITIES, CLARIFICATION_KINDS, CURRENT_MEDIATION_VERSION,
    DATASET_CLARIFICATION_KINDS, DATASET_MEDIATION_VERSION, DYNAMIC_ANOMALY_OPERATIONS,
    DYNAMIC_FINANCIAL_OPERATIONS, FOLLOW_UP_INTENTS, LANGUAGES,
    LEGACY_CLARIFICATION_KINDS, LEGACY_OPERATIONS, MEDIATION_VERSION,
    MISSING_DIMENSION_POLICIES, OPERATIONS, PERIOD_GRANULARITIES,
    PRESENTATIONS, MediationIntent, MediationRejected, NaturalResponse,
)


MAX_INTENT_CHARACTERS = 4_096
INTENT_KEYS = frozenset((
    "version", "operation", "intent", "capability_hint", "clarification_answer",
    "clarification_kind", "evidence_reference", "follow_up_intent", "presentation_hint",
    "response_language",
))
DYNAMIC_INTENT_KEYS = INTENT_KEYS | frozenset((
    "dataset_id", "dynamic_operation", "period_granularity", "missing_dimension",
))
FENCED_JSON = re.compile(r"\A```(?:json)?\s*\n(.*)\n```\Z", re.S)


def load_object(raw, maximum):
    """Parse exactly one JSON object (optionally one ```json fence); duplicates and NaN are rejected."""
    if type(raw) is not str:
        raise MediationRejected("provider_output_not_text")
    if len(raw) > maximum:
        raise MediationRejected("provider_output_too_large")
    text = raw.strip()
    fenced = FENCED_JSON.fullmatch(text)
    if fenced:
        text = fenced[1].strip()

    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise MediationRejected("duplicate_key")
            result[key] = value
        return result

    def no_constant(_value):
        raise MediationRejected("non_finite_number")

    try:
        value = json.loads(text, object_pairs_hook=unique, parse_constant=no_constant)
    except MediationRejected:
        raise
    except (ValueError, RecursionError):
        raise MediationRejected("malformed_json") from None
    if type(value) is not dict:
        raise MediationRejected("json_object_required")
    return value


def _enum(value, allowed, *, nullable=True):
    if value is None and nullable:
        return None
    if type(value) is not str or value not in allowed:
        raise MediationRejected("value_not_allowlisted")
    return value


def parse_intent(raw, context):
    """Return a validated MediationIntent or raise MediationRejected. Never repairs input."""
    data = load_object(raw, MAX_INTENT_CHARACTERS)
    version = data.get("version")
    dynamic_versions = (DATASET_MEDIATION_VERSION, CURRENT_MEDIATION_VERSION)
    expected_keys = DYNAMIC_INTENT_KEYS if version in dynamic_versions else INTENT_KEYS
    if set(data) != expected_keys:
        raise MediationRejected("intent_keys_mismatch")
    if version not in (MEDIATION_VERSION, *dynamic_versions):
        raise MediationRejected("unsupported_version")
    operation = _enum(
        data["operation"], OPERATIONS if version == CURRENT_MEDIATION_VERSION else (
            (*LEGACY_OPERATIONS, "SELECT_DYNAMIC_DATASET", "DYNAMIC_FINANCIAL_ANALYSIS")
            if version == DATASET_MEDIATION_VERSION else LEGACY_OPERATIONS
        ),
        nullable=False,
    )
    identifier = _enum(data["intent"], (*REQUESTS, USER_TEXT))
    capability = _enum(data["capability_hint"], CAPABILITIES)
    answer = _enum(data["clarification_answer"], context.pending_choices)
    clarification_kinds = (
        CLARIFICATION_KINDS if version == CURRENT_MEDIATION_VERSION else
        DATASET_CLARIFICATION_KINDS if version == DATASET_MEDIATION_VERSION else
        LEGACY_CLARIFICATION_KINDS
    )
    kind = _enum(data["clarification_kind"], clarification_kinds)
    reference = _enum(data["evidence_reference"], context.reference_labels)
    follow_up = _enum(data["follow_up_intent"], FOLLOW_UP_INTENTS)
    presentation = _enum(data["presentation_hint"], PRESENTATIONS)
    language = _enum(data["response_language"], LANGUAGES, nullable=False)
    dataset_ids = tuple(item.dataset_id for item in context.dynamic_datasets)
    dataset_id = _enum(data.get("dataset_id"), dataset_ids)
    dynamic_operation = _enum(
        data.get("dynamic_operation"),
        (*DYNAMIC_FINANCIAL_OPERATIONS, *DYNAMIC_ANOMALY_OPERATIONS),
    )
    granularity = _enum(data.get("period_granularity"), PERIOD_GRANULARITIES)
    missing_dimension = _enum(data.get("missing_dimension"), MISSING_DIMENSION_POLICIES)

    used = {name for name, value in (
        ("intent", identifier), ("clarification_answer", answer),
        ("clarification_kind", kind), ("evidence_reference", reference),
        ("follow_up_intent", follow_up),
        ("dataset_id", dataset_id), ("dynamic_operation", dynamic_operation),
        ("period_granularity", granularity), ("missing_dimension", missing_dimension),
    ) if value is not None}
    # operation -> (fields it may set, fields it must set)
    permitted, required = {
        "NEW_REQUEST": ({"intent"}, {"intent"}),
        "ANSWER_CLARIFICATION": ({"clarification_answer"}, {"clarification_answer"}),
        "EVIDENCE_FOLLOWUP": ({"evidence_reference", "follow_up_intent"}, {"follow_up_intent"}),
        "REQUEST_CLARIFICATION": ({"clarification_kind"}, {"clarification_kind"}),
        "SELECT_DYNAMIC_DATASET": ({"dataset_id"}, {"dataset_id"}),
        "DYNAMIC_FINANCIAL_ANALYSIS": (
            {"dataset_id", "dynamic_operation", "period_granularity", "missing_dimension"},
            {"dynamic_operation"},
        ),
        "DYNAMIC_ANOMALY_SCREEN": (
            {"dataset_id", "dynamic_operation"}, {"dynamic_operation"},
        ),
    }[operation]
    if not used <= permitted or not required <= used:
        raise MediationRejected("operation_fields_inconsistent")
    if operation == "EVIDENCE_FOLLOWUP" and not context.reference_labels:
        raise MediationRejected("no_evidence_context")
    if (operation in {"SELECT_DYNAMIC_DATASET", "DYNAMIC_FINANCIAL_ANALYSIS",
                      "DYNAMIC_ANOMALY_SCREEN"}
            and context.invalid_dynamic_dataset_reference):
        raise MediationRejected("invalid_dataset_target")
    if operation in {"SELECT_DYNAMIC_DATASET", "DYNAMIC_FINANCIAL_ANALYSIS",
                     "DYNAMIC_ANOMALY_SCREEN"}:
        explicit = context.explicit_dynamic_dataset_ids
        if (explicit and (len(explicit) != 1 or dataset_id != explicit[0])
                or not explicit and dataset_id is not None
                and dataset_id != context.selected_dynamic_dataset):
            raise MediationRejected("dataset_target_not_authorized")
    if (operation == "DYNAMIC_FINANCIAL_ANALYSIS"
            and not dynamic_parameters_supported(
                dynamic_operation,
                granularity=granularity,
                missing_dimension=missing_dimension,
            )):
        raise MediationRejected("dynamic_parameter_mismatch")
    if (operation == "DYNAMIC_ANOMALY_SCREEN"
            and dynamic_operation not in DYNAMIC_ANOMALY_OPERATIONS):
        raise MediationRejected("dynamic_anomaly_operation_mismatch")

    request = REQUESTS.get(identifier)
    expected_capability = (
        ("FINANCIAL_ANALYSIS" if operation == "DYNAMIC_FINANCIAL_ANALYSIS"
         else "ANOMALY_DETECTION" if operation == "DYNAMIC_ANOMALY_SCREEN"
         else None)
        or (request.capability if request is not None else None)
    )
    if capability is not None and capability != expected_capability:
        # A hint can confirm the catalog entry; it can never select or change a capability.
        raise MediationRejected("capability_hint_mismatch")
    return MediationIntent(
        operation=operation,
        request=request,
        use_user_text=identifier == USER_TEXT,
        clarification_answer=answer,
        clarification_kind=kind,
        evidence_reference=reference,
        follow_up_intent=follow_up,
        presentation_hint=presentation,
        response_language=language,
        dataset_id=dataset_id,
        dynamic_operation=dynamic_operation,
        period_granularity=granularity,
        missing_dimension=missing_dimension,
    )


MAX_RESPONSE_CHARACTERS = 16_384
MAX_MESSAGE_CHARACTERS = 1_200
MAX_MESSAGE_LINES = 12
RESPONSE_KEYS = frozenset(("message", "used_fact_ids", "warning_fact_ids", "presentation_hint", "language"))
SCALES = {
    "thousand": 3, "thousands": 3, "mil": 3, "k": 3,
    "million": 6, "millions": 6, "milhão": 6, "milhao": 6, "milhões": 6, "milhoes": 6,
    "mi": 6, "mn": 6, "m": 6,
    "billion": 9, "billions": 9, "bilhão": 9, "bilhao": 9, "bilhões": 9, "bilhoes": 9,
    "bi": 9, "bn": 9, "b": 9,
    "trillion": 12, "trilhão": 12, "trilhões": 12, "tri": 12,
}
# Letters before a numeral do not exempt it ("FY2026", "x10", "1e7"); only issued labels
# (A1-A10) and quartile names (Q1, Q3) are removed before scanning.
NUMBER = re.compile(
    r"(?<![\d.,])(?P<sign>[-−])?(?P<digits>\d(?:[\d.,]*\d)?)"
    r"(?:\s*(?P<percent>%|percent\b|per cent\b|pct\b|por cento\b)"
    r"|\s*(?P<scale>" + "|".join(sorted(map(re.escape, SCALES), key=len, reverse=True)) + r")\b)?",
    re.I,
)
FORBIDDEN_PATTERNS = (
    # Currency prose stays forbidden; code renders any approved evidence status separately.
    ("currency_claim", re.compile(
        r"\b(?:USD|CAD|BRL|EUR|GBP|MXN|JPY|CNY|CHF|AUD|NZD|INR|ARS|CLP|COP|PEN|ZAR|SEK|NOK|DKK|"
        r"HKD|SGD|KRW|RUB|TRY|PLN)\b|[$€£¥₹₩₽]")),
    ("currency_claim", re.compile(
        r"\b(?:usd|brl|eur|cad|gbp|mxn|jpy|cny|chf|aud|inr)\b|\bu\.\s?s\.\s?d\b", re.I)),
    ("currency_claim", re.compile(
        r"\b(?:dollars?|d[óo]lar(?:es)?|reais|euros?|pounds? sterling|libras? esterlinas?|yen|"
        r"ienes?|yuan|francs?|francos?|rupees?|r[úu]pias?|bucks|greenbacks?|pesos? (?:mexican|"
        r"argentin|chilen|colombian)\w*|mexican pesos?)\b"
        r"|\b(?:canadian|american|u\.?s\.?|mexican|brazilian|european|british|japanese|chinese|"
        r"swiss|australian|indian|french|german)\s+(?:currency|money)\b"
        r"|\b(?:moedas?|dinheiro)\s+(?:canadense|american[ao]|norte-american[ao]|mexican[ao]|"
        r"brasileir[ao]|europeia|brit[âa]nica|japonesa|chinesa|su[íi][çc]a|francesa|alem[ãa])\b", re.I)),
    # Screening produces candidates for review, never verdicts or likelihoods.
    ("unverified_claim", re.compile(
        r"\b(?:fraud\w*|fraude\w*|misconduct|m[áa] conduta|wrongdoing|irregularidade\w*|"
        r"errors?|erros?|mistakes?|il+egal\w*|crim\w*|certain(?:ly|ty)|for certain|certeza|"
        r"definitely|definitivamente|undoubtedly|sem d[úu]vida|confirmed anomal\w*|"
        r"anomalias? confirmadas?|probabl\w*|probabilidade\w*|likel(?:y|ihood)|odds|"
        r"prov[áa]ve(?:l|is)|provavelmente|guaranteed|garantid\w*|suspic\w*|suspeit\w*|"
        r"abnormal\w*|anorma\w*)\b", re.I)),
    # Blocked capabilities and unverified financial semantics.
    ("capability_claim", re.compile(
        r"\b(?:forecast\w*|predict\w*|projection\w*|previs\w*|prever|prev[êe]\w*|proje[çc]\w*|"
        r"projetad\w*|cash[ -]?flows?|fluxos? de caixa|cash (?:inflows?|outflows?|receipts?)|"
        r"entradas? de caixa|sa[íi]das? de caixa|receipts?|recebimentos?|invoices?|faturas?|"
        r"contracts?|contratos?|documents?|documentos?|payments?|pagamentos?|revenue|"
        r"receitas?|faturamento|cash|caixa|income|earnings|billings?|"
        r"will (?:grow|increase|decrease|decline|fall|rise|reach|be)|next (?:month|quarter|year)|"
        r"pr[óo]xim[oa]s? (?:m[êe]s|meses|trimestres?|anos?)|"
        r"(?:v[ãa]o|vai|ir[áa]|ir[ãa]o) (?:crescer|aumentar|cair|diminuir|subir))\b", re.I)),
    # Multiplicative comparisons are arithmetic the model may not perform, even without numerals.
    ("derived_claim", re.compile(
        r"\b(?:twice|double[sd]?|half|halved|triple[sd]?|quadruple[sd]?|times (?:as|more|less|higher|"
        r"lower)|dobr\w*|metade|tripl\w*|qu[áa]drupl\w*|vezes)\b", re.I)),
    # Internal identifiers, digests, handles and paths stay out of user-facing prose.
    ("internal_identifier", re.compile(
        r"\b[a-z0-9]+(?:_[a-z0-9]+)+\b|\b[0-9a-f]{16,}\b|\b(?:RG|CF)-\d{2}\b|\b[FW]\d+\b|"
        r"\bevidence-\w+|(?:^|\s)(?:/|\./|~/|src/|docs/|data/)\S+")),
    ("markup", re.compile(r"```|^\s*\|.*\|\s*$|\t|<[a-z/][^>]*>", re.M | re.I)),
)


SPELLED_NUMBER = re.compile(
    r"\b(?:twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|hundreds?|vinte|trinta|"
    r"quarenta|cinquenta|sessenta|setenta|oitenta|noventa|cem|cento|centenas?|duzent\w+|"
    r"trezent\w+|quatrocent\w+|quinhent\w+|seiscent\w+|setecent\w+|oitocent\w+|"
    r"novecent\w+)\b", re.I)
SCALE_WORD = re.compile(
    r"\b(?:thousands?|millions?|billions?|trillions?|mil|milh(?:ão|ao|ões|oes)|"
    r"bilh(?:ão|ao|ões|oes)|trilh(?:ão|ao|ões|oes))\b", re.I)
EXEMPT_LABELS = re.compile(r"\b(?:A(?:10|[1-9])|Q[13])\b")
LANGUAGE_MARKERS = {
    "en": frozenset((
        "the", "this", "that", "there", "these", "those", "and", "with", "for", "from",
        "is", "are", "was", "were", "has", "have", "reports", "records", "values", "used",
        "currency", "review", "screening", "flagged", "profit", "looks", "unusual", "check",
        "highlighted", "entries",
    )),
    "pt-BR": frozenset((
        "o", "os", "a", "as", "este", "esta", "isso", "esses", "essas", "e", "com", "para",
        "de", "da", "das", "do", "dos", "é", "são", "foi", "foram", "tem", "têm", "mostra",
        "registros", "valores", "usados", "moeda", "revisão", "triagem", "sinalizados",
        "lucro", "parece", "estranho", "confira", "itens", "destacados",
    )),
}


def _obvious_language_mismatch(message, expected):
    """Detect only prose dominated by common markers of the other supported language."""
    words = re.findall(r"[^\W\d_]+", message.casefold(), re.UNICODE)
    counts = {language: sum(word in markers for word in words)
              for language, markers in LANGUAGE_MARKERS.items()}
    other = "en" if expected == "pt-BR" else "pt-BR"
    return counts[other] >= 2 and counts[other] >= counts[expected] + 1


def _interpretations(digits):
    """Possible (value, decimal_places) readings of a numeral in English or Brazilian style."""
    readings = []
    if "." in digits and "," in digits:
        decimal_mark = "." if digits.rfind(".") > digits.rfind(",") else ","
        whole, _, fraction = digits.rpartition(decimal_mark)
        readings.append((whole.replace(".", "").replace(",", ""), fraction))
    elif "." in digits or "," in digits:
        mark = "." if "." in digits else ","
        parts = digits.split(mark)
        if len(parts) > 2:
            readings.append(("".join(parts), ""))
        else:
            readings.append((parts[0], parts[1]))
            if len(parts[1]) == 3:
                readings.append((parts[0] + parts[1], ""))
    else:
        readings.append((digits, ""))
    values = []
    for whole, fraction in readings:
        if whole.isdigit() and (fraction == "" or fraction.isdigit()):
            values.append((Decimal(whole + ("." + fraction if fraction else "")), len(fraction)))
    return values


def _grounded_numbers(packet, declared):
    """Exact integer tokens plus Decimal values of the facts the response declares it used.

    Tokens come from labels, whole-integer values, non-numeric values (such as "2013-09") and
    ranks, never from the fractional digits of a decimal value.
    """
    tokens, values, percentages = set(), [], []
    for item in packet["facts"] + packet["warnings"]:
        if item["id"] not in declared:
            continue
        tokens.update(re.findall(r"\d+", str(item.get("label", ""))))
        if "rank" in item:
            tokens.add(str(item["rank"]))
        value = str(item.get("value", ""))
        try:
            number = Decimal(value)
        except (InvalidOperation, ValueError):
            tokens.update(re.findall(r"\d+", value))
            continue
        if not number.is_finite():
            continue
        if re.fullmatch(r"-?\d+", value):
            tokens.add(value.lstrip("-"))
        (percentages if item.get("semantic_type") == "percentage" else values).append(number)
    return tokens, values, percentages


def _number_is_grounded(match, tokens, values, percentages):
    digits = match["digits"]
    scale, percent = match["scale"], match["percent"]
    if scale is None and percent is None and digits.isdigit() and digits in tokens:
        return True
    multiplier = Decimal(10) ** SCALES[scale.casefold()] if scale else Decimal(1)
    candidates = percentages if percent else values
    negative = match["sign"] is not None
    for claimed, places in _interpretations(digits):
        if scale and claimed == 0:
            continue
        amount = claimed * multiplier
        tolerance = Decimal(5) * Decimal(10) ** (-(places + 1)) * multiplier
        for fact in candidates:
            # The sign must agree: "500" never stands for -500.
            if abs((-amount if negative else amount) - fact) <= tolerance:
                return True
    return False


def validate_natural_response(raw, packet):
    """Return a NaturalResponse only if it is well-formed and grounded; otherwise fail closed."""
    data = load_object(raw, MAX_RESPONSE_CHARACTERS)
    if set(data) != RESPONSE_KEYS:
        raise MediationRejected("response_keys_mismatch")
    message, used, warned = data["message"], data["used_fact_ids"], data["warning_fact_ids"]
    fact_ids = {item["id"] for item in packet["facts"]}
    warning_ids = {item["id"] for item in packet["warnings"]}
    if (type(message) is not str or not message.strip() or len(message) > MAX_MESSAGE_CHARACTERS
            or message.count("\n") >= MAX_MESSAGE_LINES
            or not all(line.isprintable() for line in message.split("\n"))):
        raise MediationRejected("message_invalid")
    for ids, known, minimum in ((used, fact_ids, 1), (warned, warning_ids, 0)):
        if (type(ids) is not list or not minimum <= len(ids) <= 60
                or any(type(item) is not str or item not in known for item in ids)
                or len(set(ids)) != len(ids)):
            raise MediationRejected("unknown_fact_reference")
    if data["presentation_hint"] not in packet["allowed_presentations"]:
        raise MediationRejected("presentation_not_allowed")
    if data["language"] != packet["language"]:
        raise MediationRejected("language_mismatch")
    # Compatibility forms (fullwidth digits/symbols, ligatures) are checked as what they render.
    message = unicodedata.normalize("NFKC", message).strip()
    for code, pattern in FORBIDDEN_PATTERNS:
        if pattern.search(message):
            raise MediationRejected(code)
    if _obvious_language_mismatch(message, packet["language"]):
        raise MediationRejected("language_mismatch")
    # Spelled-out large numbers and bare scale words cannot be grounded, so they are refused.
    if SPELLED_NUMBER.search(message) or any(
            not re.search(r"\d\s*$", message[:match.start()]) for match in SCALE_WORD.finditer(message)):
        raise MediationRejected("ungrounded_number")
    tokens, values, percentages = _grounded_numbers(packet, set(used) | set(warned))
    issued = {item.get("reference_label") for item in packet["facts"]}
    scanned = EXEMPT_LABELS.sub(lambda match: " " if match[0] in issued or match[0][0] == "Q"
                                else match[0], message)
    for match in NUMBER.finditer(scanned):
        if not _number_is_grounded(match, tokens, values, percentages):
            raise MediationRejected("ungrounded_number")
    return NaturalResponse(message, tuple(used), tuple(warned), data["presentation_hint"],
                           data["language"])
