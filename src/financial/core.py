"""Deterministic Financial Data Analysis interface, without an LLM or network."""

from collections import Counter, defaultdict
from pathlib import Path

from src.database.loaders import APPROVED_RUN_ID

from .arithmetic import decimal, statistics
from .contracts import CONTRACTS, FIELDS
from .currency import query_currency
from .filters import normalize
from .models import ContractError, arithmetic_metadata, envelope
from .quality import assess, coverage, dimension_coverage, observed_period, result_status, select_rows
from .snapshot import ApprovedSnapshot


def dimension_exclusion(row, request):
    if request.group and request.options["missing_dimension"] == "exclude":
        column = FIELDS[request.dataset][request.group]
        if row[column] is None:
            return f"dimension:{request.group}:{row[column + '_status']}"
    return None


def measure_result(rows, request, measure, *, grouped=False, calculate=True):
    column = FIELDS[request.dataset][measure]
    tokens, reasons = [], []
    for row in rows:
        reason = None if grouped else dimension_exclusion(row, request)
        if reason is None and row[column] is None:
            reason = f"measure:{measure}:{row[column + '_status']}"
        if reason:
            reasons.append(reason)
        else:
            tokens.append(row[column])
    result = {"unit": "quantity" if measure == "units_sold" else "monetary"}
    if calculate:
        result.update(statistics(tokens, request.statistics))
    result["coverage"] = coverage(len(rows), len(tokens), reasons)
    return result


def calculate(candidates, request, records):
    eligible = [row for row in candidates if dimension_exclusion(row, request) is None]
    reasons = []
    for row in candidates:
        reason = dimension_exclusion(row, request)
        if reason is None and request.measures and all(row[FIELDS[request.dataset][m]] is None for m in request.measures):
            if len(request.measures) == 1:
                measure = request.measures[0]
                reason = f"measure:{measure}:{row[FIELDS[request.dataset][measure] + '_status']}"
            else:
                reason = "no_requested_measure_available"
        if reason:
            reasons.append(reason)
    records.update(used=len(candidates) - len(reasons), excluded=len(reasons),
                   exclusion_reasons=dict(sorted(Counter(reasons).items())))
    if request.kind == "count":
        return {"record_count": len(candidates)}, {}, None, [], len(eligible)

    # Global coverage is required even when only per-group statistics are requested.
    measures = {m: measure_result(candidates, request, m, calculate=not request.group and request.kind != "extreme") for m in request.measures}
    coverages = {m: value["coverage"] for m, value in measures.items()}
    dimension, returned = None, []
    if request.group:
        column = FIELDS[request.dataset][request.group]
        dimension = dimension_coverage(candidates, request.group, column, request.options["missing_dimension"])
        groups = defaultdict(list)
        for row in eligible:
            key = row[column]
            if key is not None and "granularity" in request.options:
                key = key[:{"day": 10, "month": 7, "year": 4}[request.options["granularity"]]]
            groups[key].append(row)
        output = []
        for key in sorted(groups, key=lambda key: (key is None, key or "")):
            group_rows = groups[key]
            item = {"key": {"value": key, "kind": "unavailable" if key is None else "source_value"},
                    "record_count": len(group_rows),
                    "measures": {m: measure_result(group_rows, request, m, grouped=True) for m in request.measures}}
            if request.kind == "discount":
                item["unresolved_placeholder_count"] = sum(r["discounts_status"] == "unresolved_placeholder" for r in group_rows)
            output.append(item)
        result = {"groups": output, "dimension_coverage": dimension, "measure_coverage": coverages}
    elif request.kind == "extreme":
        column = FIELDS[request.dataset]["accounting_amount"]
        ranked = [r for r in eligible if r[column] is not None]
        # Stable two-pass sort keeps source-row ties ascending in either direction.
        ranked.sort(key=lambda r: (r["source_row_number"], r["record_id"]))
        ranked.sort(key=lambda r: decimal(r[column]), reverse=request.options["direction"] == "highest")
        returned = ranked[:request.options["limit"]]
        records.update(returned=len(returned), not_returned=len(ranked) - len(returned), selection_reason="limit")
        items = []
        for rank, row in enumerate(returned, 1):
            item = {key: row[key] for key in ("record_id", "source_row_number", "processed_row_number")}
            item.update(rank=rank, accounting_amount=row[column], accounting_amount_raw=row[column + "_raw"],
                        accounting_amount_status=row[column + "_status"])
            for field in ("effective_date", "debit_credit", "voucher_type", "department"):
                source = FIELDS[request.dataset][field]
                item[field], item[field + "_status"] = row[source], row[source + "_status"]
            items.append(item)
        result = {"items": items, "ties_policy": "truncate_by_source_row", "measure_coverage": coverages}
    else:
        result = {"measures": measures}
    if request.kind in ("discount", "profit"):
        result["record_count"] = len(candidates)
    if request.kind == "discount":
        result["unresolved_placeholder_count"] = sum(r["discounts_status"] == "unresolved_placeholder" for r in candidates)
    if request.kind == "profit":
        values = [decimal(r["profit"]) for r in candidates if r["profit"] is not None]
        result.update(negative_count=sum(v < 0 for v in values), zero_count=sum(v == 0 for v in values),
                      positive_count=sum(v > 0 for v in values))
    return result, coverages, dimension, returned, len(eligible)


class FinancialCore:
    """One controlled request interface; configuration stays outside requests."""

    def __init__(self, project_root=None):
        root = Path(project_root) if project_root is not None else Path(__file__).resolve().parents[2]
        self._snapshot = ApprovedSnapshot(root)

    def query(self, request):
        response = envelope(request)
        try:
            normalized = normalize(request)
            with self._snapshot.open() as connection:
                population, flags, snapshot, fields = self._snapshot.read(connection, normalized)
            candidates, unavailable, records, diagnostics = select_rows(population, fields, normalized.dataset)
            result, coverages, dimension, returned, eligible = calculate(candidates, normalized, records)
            assessment = assess(normalized, flags, population, candidates, unavailable, returned, coverages, dimension)
            status, no_data = result_status(records, bool(normalized.group), eligible, normalized.kind, assessment)
            response.update(status=status, result=result, records=records, filter_diagnostics=diagnostics,
                            quality=assessment.disclosure,
                            currency=query_currency(bool(normalized.measures) and normalized.measures != ("units_sold",)))
            response["metadata"] = {
                "run_id": APPROVED_RUN_ID, "schema_version": 1, "snapshot": snapshot,
                "filters": normalized.filters, "group_by": normalized.group, "period": normalized.period,
                "observed_period": observed_period(candidates, normalized.dataset),
                "options": normalized.options, "value_basis": "imported_source_records",
                "arithmetic": arithmetic_metadata(),
            }
            if no_data:
                response["metadata"]["no_data_reason"] = no_data
        except ContractError as error:
            response.update(status=error.status, errors=[error.error])
        return response

    def _named(self, name, options):
        request = {"contract_version": "1.0", "query_name": name, "dataset": CONTRACTS[name].dataset}
        if set(options) & set(request):
            response = envelope(request)
            response.update(status="INVALID_REQUEST", errors=[{"code": "invalid_parameter", "field": None,
                            "message": "Named tools fix their contract identity/version; use query for a full request."}])
            return response
        return self.query(request | options)
