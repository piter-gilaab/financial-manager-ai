"""Scope-aware quality evidence, coverage and status effects; no financial repair."""

from collections import Counter, defaultdict
from dataclasses import dataclass
import calendar
from datetime import date

from .arithmetic import percentage
from .contracts import DATES, FIELDS, RG
from .currency import UNKNOWN_DISCLOSURE


def coverage(candidates, used, reasons):
    counts = dict(sorted(Counter(reasons).items()))
    if candidates != used + sum(counts.values()):
        raise ValueError("Coverage does not reconcile")
    return {"candidates": candidates, "used": used, "excluded": candidates - used,
            "exclusion_reasons": counts, "percentage": percentage(used, candidates)}


def dimension_coverage(rows, field, column, policy):
    unavailable = Counter(row[column + "_status"] for row in rows if row[column] is None)
    available = len(rows) - sum(unavailable.values())
    return {"candidates": len(rows), "available": available, "unavailable": len(rows) - available,
            "unavailable_by_status": dict(sorted(unavailable.items())),
            "percentage": percentage(available, len(rows)), "policy": policy}


def select_rows(rows, fields, dataset):
    candidates, unavailable, reasons = [], [], Counter()
    diagnostics = [{"field": f, "matched": 0, "nonmatching": 0, "unavailable": 0} for f in fields]
    for row in rows:
        states = [row[f"_filter_{i}"] for i in range(len(fields))]
        for diagnostic, state in zip(diagnostics, states):
            diagnostic["unavailable" if state is None else "matched" if state else "nonmatching"] += 1
        if 0 in states:
            continue
        if None in states:
            unavailable.append(row)
            field = fields[states.index(None)]
            reasons[field + ":" + row[FIELDS[dataset][field] + "_status"]] += 1
        else:
            candidates.append(row)
    records = {
        "population": len(rows), "filtered_out": len(rows) - len(candidates) - len(unavailable),
        "filter_unavailable": len(unavailable), "candidates": len(candidates),
        "used": 0, "excluded": 0, "exclusion_reasons": {},
        "filter_unavailable_reasons": dict(sorted(reasons.items())),
    }
    return candidates, unavailable, records, diagnostics


def observed_period(rows, dataset):
    column = FIELDS[dataset][DATES[dataset]]
    values = [row[column] for row in rows if row[column] is not None]
    return {"start_date": min(values), "end_date": max(values)} if values else None


def period_limited(request, population):
    if not request.period:
        return False
    observed = observed_period(population, request.dataset)
    if observed is None:
        return True
    start, end = observed["start_date"], observed["end_date"]
    if request.dataset != RG:
        final = date.fromisoformat(end)
        end = final.replace(day=calendar.monthrange(final.year, final.month)[1]).isoformat()
    return request.period["start_date"] < start or request.period["end_date"] > end


@dataclass(frozen=True)
class QualityAssessment:
    disclosure: dict
    partial: bool


def assess(request, flags, population, candidates, unavailable, returned, measure_coverage, dimension,
           *, additional_fields=()):
    """Expose all scoped evidence; only relevant limitations affect the answer."""
    scoped_ids = {row["record_id"] for row in candidates + unavailable}
    returned_ids = {row["record_id"] for row in returned}
    mapping = FIELDS[request.dataset]
    fields = {mapping[f] for f in request.filters}
    fields.update(mapping[m] for m in request.measures)
    # Trusted service dependencies (e.g. compound statistical peers), never SQL
    # or caller-selected fields. Existing contract callers retain identical scope.
    fields.update(additional_fields)
    if request.group:
        fields.add(mapping[request.group])
    if request.period:
        fields.add(mapping[DATES[request.dataset]])
    context_fields = {mapping[f] for f in ("effective_date", "debit_credit", "voucher_type", "department")} if request.kind == "extreme" else set()
    monetary = bool(request.measures) and request.measures != ("units_sold",)
    temporal = bool(request.period or request.group == "effective_date" or {"fiscal_year", "fiscal_month"} & set(request.filters))

    def relevant(flag):
        field = flag["field"]
        if flag["scope"] != "dataset":
            return field in fields or (field in context_fields and flag["record_id"] in returned_ids)
        if flag["flag"] == "currency_unknown":
            return monetary
        if flag["flag"] == "fiscal_alignment_unresolved":
            return temporal
        if flag["flag"] == "source_semantics_unresolved":
            return field in {"record_granularity", "provenance", "entity_scope"} or field in fields
        return True

    selected = []
    for flag in flags:
        if flag["scope"] == "dataset" or flag["record_id"] in scoped_ids:
            selected.append({k: v for k, v in flag.items() if k != "flag_id"} | {"relevant": relevant(flag)})
    selected.sort(key=lambda f: f["flag_row_number"])
    warnings = []
    warning_groups = defaultdict(list)
    for flag in selected:
        if flag["relevant"]:
            warning_groups[(flag["flag"], flag["field"], flag["scope"])].append(flag)
    for (code, field, scope), entries in sorted(warning_groups.items()):
        affected = None if scope == "dataset" else len({f["record_id"] for f in entries})
        message = " ".join(dict.fromkeys(f["reason"] for f in entries))
        if code == "currency_unknown":
            message = UNKNOWN_DISCLOSURE
        if affected is not None:
            message += f" Affected scoped records: {affected}; see filter diagnostics and dimension/measure coverage for participation and exclusions."
        warnings.append({"code": code, "field": field, "scope": scope, "affected_records": affected,
                         "message": message, "flag_row_numbers": [f["flag_row_number"] for f in entries]})
    limited = period_limited(request, population)
    if limited:
        warnings.append({"code": "period_coverage_limited", "field": DATES[request.dataset], "scope": "dataset",
                         "affected_records": None, "message": f"Requested bounds {request.period} extend beyond extract coverage {observed_period(population, request.dataset)}; no missing periods are filled.",
                         "flag_row_numbers": []})
    warnings.sort(key=lambda f: (f["code"], f["field"] or "", f["scope"]))
    if request.detail == "summary":
        groups = {}
        keys = ("scope", "field", "rule_id", "flag", "status", "reason")
        for flag in selected:
            key = tuple(flag[k] for k in keys)
            groups.setdefault(key, []).append(flag)
        disclosed = []
        for key, entries in groups.items():
            disclosed.append(dict(zip(keys, key)) | {
                "flag_count": len(entries),
                "affected_records": None if key[0] == "dataset" else len({f["record_id"] for f in entries}),
                "flag_row_numbers": [f["flag_row_number"] for f in entries],
                "relevant": any(f["relevant"] for f in entries),
            })
    else:
        disclosed = selected
    context_missing = any(row[col] is None for row in returned for col in context_fields)
    partial = bool(unavailable or limited or context_missing or
                   any(c["excluded"] for c in measure_coverage.values()) or
                   (dimension and dimension["unavailable"]))
    return QualityAssessment({"warnings": warnings, "flags": disclosed, "detail": request.detail}, partial)


def result_status(records, grouped, eligible_count, kind, assessment):
    if not records["candidates"]:
        return "NO_DATA", "no_matching_records"
    if grouped and not eligible_count:
        return "NO_DATA", "no_group_eligible_records"
    if kind != "count" and not records["used"]:
        return "NO_DATA", "no_numeric_values"
    return ("PARTIAL" if assessment.partial else "SUCCESS"), None
