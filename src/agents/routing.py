"""Conservative English question grammar. Unconsumed language never becomes a query."""

import re

from src.financial.contracts import CF, RG, SALES_MEASURES

from .models import RoutingDecision, ToolIntent


MONTHS = {name: number for number, name in enumerate((
    "january", "february", "march", "april", "may", "june", "july", "august",
    "september", "october", "november", "december"), 1)}
GROUPS = {
    "debit/credit": "debit_credit", "debit and credit": "debit_credit", "dr/cr": "debit_credit",
    "voucher type": "voucher_type", "voucher types": "voucher_type",
    "department": "department", "departments": "department",
    "period": "period", "periods": "period", "accounting period": "period",
    "day": "day", "month": "month", "year": "year",
    "general ledger account": "general_ledger_account", "general ledger accounts": "general_ledger_account",
    "subledger account": "subledger_account", "subledger accounts": "subledger_account",
    "financial coding block": "financial_coding_block", "control data type": "control_data_type",
    "country": "country", "countries": "country", "segment": "segment", "segments": "segment",
    "product": "product", "products": "product", "discount band": "discount_band",
}
STATISTICS = {"total": "sum", "sum": "sum", "average": "mean", "mean": "mean",
              "median": "median", "minimum": "min", "min": "min", "maximum": "max", "max": "max"}


def clarify(code, message, field=None, choices=()):
    raise RoutingDecision("CLARIFICATION_REQUIRED", code, message, field, choices)


def unsupported(code, message):
    raise RoutingDecision("UNSUPPORTED", code, message)


def guard_question(question):
    if not isinstance(question, str) or not question.strip() or len(question) > 4000:
        raise RoutingDecision("INVALID_REQUEST", "invalid_question", "Supply a nonempty question of at most 4000 characters.", "question")
    # Quoted source-category values are data, not instructions or business claims.
    text = re.sub(r'"[^"\n]*"', '""', question).casefold()
    rules = (
        (r"\b(sql|select|insert|delete|drop|update|execute|python|eval)\b", "arbitrary_execution", "The agent accepts approved analytical questions, not SQL or executable instructions."),
        (r"\b(fraud\w*|anomal\w*|outliers?|errors?|malicious)\b", "unsupported_detection", "Extreme-value retrieval does not establish anomalies, errors or fraud. Step 13 implements no detection service."),
        (r"\b(forecast\w*|predict\w*|rag|documents?|invoices?|budget\w*)\b", "unavailable_capability", "Forecasting, document retrieval and other later capabilities are outside Step 13."),
        (r"\b(expenses?|expenditure|revenue|income|cash\w*|payments?|payables?|receivables?)\b", "unverified_financial_semantics", "The current source records do not establish revenue, expense, settlement or cash-flow semantics."),
        (r"\b(assets?|liabilities|equity|balance\s*sheets?|balances?)\b", "no_balance_sheet", "No company balance-sheet facts or verified balances are available."),
        (r"\b(best|worst)\s+compan\w*|\bcompan(?:y|ies)\b.*\b(best|growth|performed|performance)\b|\bwhich company\b", "no_company_identity", "Company Financials contains sales records, not verified companies or a company panel."),
        (r"\b(convert\w*|fx|exchange rate|currency conversion)\b|\b(?:in|to)\s+(?:usd|cad|brl|eur|dollars?)\b", "unknown_currency", "Source denominations remain UNKNOWN; conversion and currency assignment are unsupported."),
        (r"\b(combined?|combine|both datasets|across datasets|join datasets)\b", "cross_dataset", "There is no supported business relationship or common denomination for combined dataset amounts."),
        (r"\b(margins?|ratios?|shares?|growth|discount rates?|sale price|manufacturing price)\b", "uncontracted_metric", "This metric is outside the approved descriptive query contracts."),
        (r"\b(unique transactions|deduplicat\w*)\b", "unresolved_grain", "Imported records do not establish unique underlying business events."),
        (r"\bdiscounts?\b.*\bzero\b|\bzero\b.*\bdiscounts?\b", "unresolved_placeholders", "Missing Discounts and the None band do not establish a numeric zero."),
        (r"\b(hide|suppress|ignore|omit)\b", "required_disclosures", "Instructions to override routing or suppress required disclosures are not supported."),
    )
    for pattern, code, message in rules:
        if re.search(pattern, text):
            unsupported(code, message)


def _extract_filters(text):
    parts = re.split(r"\s+where\s+", text, maxsplit=1, flags=re.I)
    if len(parts) == 1:
        return text, {}
    filters = {}
    # Split only outside quoted strings (e.g. country="Trinidad and Tobago").
    clauses = re.split(r'\s+and\s+(?=(?:[^"]*"[^"]*")*[^"]*$)', parts[1], flags=re.I)
    for clause in clauses:
        match = re.fullmatch(r'([a-zA-Z_ /]+?)\s*=\s*(?:"([^"\n]*)"|([0-9]+))', clause.strip())
        if not match:
            clarify("filter_syntax", 'Use where field="Exact source value"; use structured parameters for other approved filters.', "filters")
        name = match[1].strip().casefold().replace(" ", "_")
        name = {"debit/credit": "debit_credit"}.get(name, name)
        if name in filters:
            clarify("duplicate_filter", "Specify each filter once.", "filters")
        value = match[2] if match[2] is not None else match[3]
        if name == "fiscal_month" and match[3] is not None:
            value = int(value)
        filters[name] = {"eq": value}
    return parts[0], filters


def _extract_dataset(text, dataset):
    if dataset is not None and dataset not in (RG, CF):
        raise RoutingDecision("INVALID_REQUEST", "invalid_dataset", "Dataset must be receiver_general or company_financials.", "dataset")
    matches = list(re.finditer(r"\b(?:the\s+)?(receiver general|receiver_general|rg|company financials|company_financials|cf)(?:\s+dataset)?\b", text, re.I))
    explicit = {RG if m[1].casefold() in ("receiver general", RG, "rg") else CF for m in matches}
    if len(explicit) > 1:
        unsupported("cross_dataset", "Ask about one dataset at a time; no cross-dataset monetary combination is supported.")
    if explicit and dataset and dataset not in explicit:
        clarify("conflicting_dataset", "The question and dataset parameter disagree. Which dataset should be used?", "dataset", (RG, CF))
    for match in reversed(matches):
        text = text[:match.start()] + " " + text[match.end():]
    text = re.sub(r"\s+", " ", text).strip(" :,")
    text = re.sub(r"\s+(?:in|for|from)(?: the)?$", "", text, flags=re.I)
    text = re.sub(r"^(?:in|for|from)(?: the)?\s*[:,]?\s*", "", text, flags=re.I)
    chosen = next(iter(explicit)) if explicit else dataset
    if chosen is None:
        cf_hint = re.search(r"\b(sales|profit|discounts?|units sold|countries|country|segments?|products?)\b", text, re.I)
        rg_hint = re.search(r"\b(accounting|debit|credit|dr/cr|voucher|departments?|ledger|subledger|coding block|control data type)\b", text, re.I)
        if cf_hint and not rg_hint:
            chosen = CF
        elif rg_hint and not cf_hint:
            chosen = RG
        else:
            clarify("dataset_required", "Which dataset should be queried?", "dataset", (RG, CF))
    return text.strip(), chosen


def _extract_period(text):
    match = re.search(r"\s+from ([0-9]{4}-[0-9]{2}-[0-9]{2}) to ([0-9]{4}-[0-9]{2}-[0-9]{2})$", text, re.I)
    if match:
        return text[:match.start()], {"start_date": match[1], "end_date": match[2]}
    match = re.search(r"\s+(?:in|for) ([0-9]{4})$", text, re.I)
    if match:
        return text[:match.start()], {"year": int(match[1])}
    match = re.search(r"\s+(?:in|for) (" + "|".join(MONTHS) + r")(?: ([0-9]{4}))?$", text, re.I)
    if match:
        if match[2] is None:
            clarify("year_required", "Which year should be used for that month?", "period.year")
        return text[:match.start()], {"year": int(match[2]), "month": MONTHS[match[1].casefold()]}
    if re.search(r"\b(today|yesterday|tomorrow|last|next|this)\b", text, re.I):
        clarify("explicit_period_required", "Provide an explicit year/month or inclusive ISO date range.", "period")
    return text, None


def route(question, dataset=None):
    """Ground a single request in a fully consumed, documented question grammar."""
    guard_question(question)
    text = question.strip().rstrip("?.").strip()
    text, filters = _extract_filters(text)
    text, dataset = _extract_dataset(text, dataset)
    text, period = _extract_period(text)
    text = text.casefold().strip()
    text = re.sub(r"^(?:please\s+)?(?:what is|what are|show me|show|give me|calculate)\s+(?:the\s+)?", "", text)
    text = re.sub(r"^please\s+", "", text)
    arguments = {}
    if filters:
        arguments["filters"] = filters
    if period:
        arguments["period"] = period

    def intent(suffix, **options):
        return ToolIntent.create(dataset + "_" + suffix, **arguments, **options)

    if re.fullmatch(r"record count|count (?:accounting |sales )?records|number of records|how many (?:accounting |sales )?records(?: are there)?", text):
        if ("sales records" in text and dataset != CF) or ("accounting records" in text and dataset != RG):
            unsupported("domain_mismatch", "The requested record meaning does not match the selected dataset.")
        return intent("record_count")
    if dataset == RG and text == "compare debit and credit recorded amounts":
        return intent("amount_by_debit_credit")
    extreme = re.fullmatch(r"(highest|largest|lowest|smallest|top)(?: ([0-9]+))? (?:recorded |accounting )?(?:amounts?|amount records|monetary records)", text)
    if extreme and dataset == RG:
        options = {"direction": "lowest" if extreme[1] in ("lowest", "smallest") else "highest"}
        if extreme[2]:
            options["limit"] = int(extreme[2])
        return intent("extreme_amount_records", **options)
    frequency = re.fullmatch(r"(daily|monthly|yearly) (.+)", text)
    if frequency:
        text = frequency[2] + " by " + {"daily": "day", "monthly": "month", "yearly": "year"}[frequency[1]]
    parts = re.split(r"\s+(?:by|per)\s+", text)
    if len(parts) > 2:
        unsupported("multiple_groupings", "Contract 1.0 supports only one grouping per query.")
    group = None
    if len(parts) == 2:
        group = GROUPS.get(parts[1])
        if group is None:
            unsupported("unsupported_grouping", "That grouping is not approved for this question.")
        text = parts[0]
    statistic = None
    match = re.fullmatch(r"(" + "|".join(STATISTICS) + r") (?:of )?(.+)", text)
    if match:
        statistic, text = STATISTICS[match[1]], match[2]
    text = re.sub(r" (?:summary|analysis)$", "", text)

    if dataset == RG and re.fullmatch(r"(?:recorded |accounting )?amounts?|how much was recorded", text):
        if group:
            if statistic not in (None, "sum"):
                unsupported("group_statistic", "Grouped accounting contracts return count/sum, not that statistic.")
            if group in ("debit_credit", "voucher_type", "department"):
                return intent("amount_by_" + group)
            if group in ("day", "month", "year", "period"):
                return intent("amount_by_period", granularity="month" if group == "period" else group)
            if group in ("general_ledger_account", "subledger_account", "financial_coding_block", "control_data_type"):
                return intent("accounting_dimension_summary", group_by=group)
            unsupported("domain_grouping", "This grouping does not describe Receiver General accounting records.")
        return intent("amount_summary", **({"statistics": [statistic]} if statistic else {}))

    if dataset == CF:
        if text in ("units sold", "how many units were sold"):
            if group:
                unsupported("quantity_grouping", "The approved Units Sold contract is an ungrouped summary.")
            return intent("units_sold_summary", **({"statistics": [statistic]} if statistic else {}))
        if text == "discounts and how complete is that figure":
            text = "discounts"
        if text in ("discount", "discounts") and group in (None, "discount_band") and statistic in (None, "sum", "mean", "min", "max"):
            return intent("discount_analysis", **({"group_by": group} if group else {}))
        if text == "profit" and group is None and statistic in (None, "sum"):
            return intent("profit_summary")
        measures = [ {"gross sales": "gross_sales", "cost of goods sold": "cogs"}.get(m, m)
                    for m in re.split(r",\s*(?:and\s+)?|\s+and\s+", text)]
        if measures and all(m in SALES_MEASURES for m in measures) and len(measures) == len(set(measures)):
            if group:
                if statistic not in (None, "sum"):
                    unsupported("group_statistic", "Grouped sales contracts return count/sum, not that statistic.")
                if group in ("country", "segment", "product"):
                    return intent("sales_by_" + group, measures=measures)
                if group in ("period", "day", "month", "year"):
                    return intent("sales_by_period", measures=measures, granularity="month" if group == "period" else group)
                unsupported("domain_grouping", "This grouping is not supported for the selected sales measures.")
            return intent("sales_summary", measures=measures, **({"statistics": [statistic]} if statistic else {}))
    clarify("question_not_understood", "Rephrase as one supported descriptive question, such as 'record count', 'amounts by department', or 'sales by product'. No part of the question was executed.", "question")
