"""Strict request normalization and parameterized three-valued predicates."""

import calendar
from dataclasses import dataclass
from datetime import date
import re

from .contracts import CF, RG, CONTRACTS, DATES, DIMENSIONS, FIELDS, FILTERS, SALES_MEASURES, STATS
from .models import ContractError, invalid


@dataclass(frozen=True)
class Request:
    name: str
    dataset: str
    kind: str
    filters: dict
    period: dict | None
    group: str | None
    measures: tuple
    statistics: tuple
    options: dict
    detail: str


def enum(value, allowed, field):
    if not isinstance(value, str) or value not in allowed:
        invalid(field, "Unrecognized option value.")
    return value


def choice_list(value, known, field):
    if not isinstance(value, list) or not value or any(not isinstance(v, str) for v in value):
        invalid(field, "Expected a nonempty list of operation names.")
    if len(value) != len(set(value)) or any(v not in known for v in value):
        invalid(field, "Operations must be recognized and unique.")
    return value


def normalize_filters(dataset, filters):
    if not isinstance(filters, dict) or any(k not in FILTERS[dataset] for k in filters):
        invalid("filters", "Only the dataset's approved categorical filters are accepted.")
    normalized = {}
    for field, predicate in sorted(filters.items()):
        if not isinstance(predicate, dict) or not predicate or set(predicate) - {"eq", "in", "nulls"}:
            invalid(field, "Expected an approved equality, membership or null predicate.")
        if "eq" in predicate and "in" in predicate:
            invalid(field, "Equality and membership cannot be combined.")
        nulls = enum(predicate.get("nulls", "exclude"), ("only", "include", "exclude"), field)
        operator = "eq" if "eq" in predicate else "in" if "in" in predicate else None
        if operator and nulls == "only":
            invalid(field, "Null-only cannot contain a value predicate.")
        values = [predicate[operator]] if operator == "eq" else predicate.get("in", [])
        if operator == "in" and (not isinstance(values, list) or not values):
            invalid(field, "Membership requires a nonempty list.")
        for value in values:
            if field == "fiscal_month":
                valid = type(value) is int and 1 <= value <= 12
            else:
                valid = isinstance(value, str) and bool(value) and value == value.strip()
                if valid and field == "fiscal_year":
                    valid = re.fullmatch(r"[0-9]{4}/[0-9]{4}", value) is not None
                if valid and field == "debit_credit":
                    valid = value in ("DR", "CR")
            if not valid:
                invalid(field, "Filter value does not match the source field type/form.")
        values = sorted(set(values))
        if operator and len(values) > 100:
            invalid(field, "Membership permits at most 100 distinct values.")
        result = {"nulls": nulls}
        if operator:
            result[operator] = values[0] if operator == "eq" else values
        normalized[field] = result
    return normalized


def normalize_period(period):
    if period is None:
        return None
    if not isinstance(period, dict):
        invalid("period", "Period must be an object or null.")
    keys = set(period)
    if keys == {"start_date", "end_date"}:
        bounds = []
        for field in ("start_date", "end_date"):
            value = period[field]
            if not isinstance(value, str) or re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value) is None:
                invalid("period", "Expected ISO dates, without time or timezone.")
            try:
                bounds.append(date.fromisoformat(value))
            except ValueError:
                invalid("period", "Invalid calendar date.")
        start, end = bounds
    elif keys in ({"year"}, {"year", "month"}):
        year, month = period["year"], period.get("month")
        if type(year) is not int or not 1 <= year <= 9999:
            invalid("period", "Year must be an integer from 1 to 9999.")
        if "month" in period and (type(month) is not int or not 1 <= month <= 12):
            invalid("period", "Month must be an integer from 1 to 12.")
        start = date(year, month or 1, 1)
        end_month = month or 12
        end = date(year, end_month, calendar.monthrange(year, end_month)[1])
    else:
        invalid("period", "Use bounds, year, or year/month exclusively.")
    if start > end:
        invalid("period", "Start date must not follow end date.")
    return {"start_date": start.isoformat(), "end_date": end.isoformat()}


def normalize(request):
    if not isinstance(request, dict) or any(not isinstance(k, str) for k in request):
        invalid(None, "Request must be an object with string keys.")
    if request.get("contract_version") != "1.0":
        invalid("contract_version", "Only contract version 1.0 is accepted.")
    name = request.get("query_name")
    if not isinstance(name, str) or name not in CONTRACTS:
        invalid("query_name", "Unknown query contract.")
    contract = CONTRACTS[name]
    if request.get("dataset") != contract.dataset:
        invalid("dataset", "Dataset must match the named contract.")
    common = {"contract_version", "query_name", "dataset", "filters", "period", "quality_detail"}
    if set(request) - common - set(contract.options):
        invalid(None, "Unknown or inapplicable request properties.")
    filters = normalize_filters(contract.dataset, request.get("filters", {}))
    period = normalize_period(request.get("period"))
    detail = enum(request.get("quality_detail", "summary"), ("summary", "full"), "quality_detail")
    group, measures, stats = contract.group, contract.measures, ("count", "sum")
    options, unsupported = {}, []
    if "group_by" in contract.options:
        group = request.get("group_by")
        allowed = DIMENSIONS if contract.dataset == RG else (None, "discount_band")
        if group not in allowed:
            if isinstance(group, str) and group in set(FIELDS[RG]) | set(FIELDS[CF]) | {"record_id", "source_row_number"}:
                unsupported.append(("group_by", "grouping_not_supported"))
            else:
                invalid("group_by", "Expected one approved grouping dimension.")
        options["group_by"] = group
    if "missing_dimension" in contract.options:
        if not group and "missing_dimension" in request:
            invalid("missing_dimension", "Missing-dimension policy requires grouping.")
        if group:
            options["missing_dimension"] = enum(request.get("missing_dimension", "bucket"), ("bucket", "exclude"), "missing_dimension")
    if "granularity" in contract.options:
        granularity = enum(request.get("granularity", "month"), ("day", "month", "year"), "granularity")
        options["granularity"] = granularity
        if contract.dataset == CF and granularity == "day":
            unsupported.append(("granularity", "monthly_grain_only"))
    if "measures" in contract.options:
        selected = choice_list(request.get("measures", ["sales"]), SALES_MEASURES + ("units_sold", "sale_price", "manufacturing_price", "accounting_amount"), "measures")
        if any(m not in SALES_MEASURES for m in selected):
            unsupported.append(("measures", "measure_not_supported"))
        measures = tuple(m for m in SALES_MEASURES if m in selected)
        options["measures"] = list(measures)
    if "statistics" in contract.options:
        default = ["count", "sum"] if name == "company_financials_sales_summary" else ["count", "sum", "min", "max"]
        selected = choice_list(request.get("statistics", default), STATS + ("share", "percentage", "ratio", "margin", "growth"), "statistics")
        allowed = STATS if name != "company_financials_sales_summary" else tuple(s for s in STATS if s != "median")
        if any(s not in allowed for s in selected):
            unsupported.append(("statistics", "statistic_not_supported"))
        stats = tuple(s for s in STATS if s in selected)
        options["statistics"] = list(stats)
    elif contract.kind == "discount":
        stats = ("count", "sum", "mean", "min", "max")
    if contract.kind == "extreme":
        options["direction"] = enum(request.get("direction", "highest"), ("highest", "lowest"), "direction")
        limit = request.get("limit", 10)
        if type(limit) is not int or not 1 <= limit <= 100:
            invalid("limit", "Limit must be an integer from 1 to 100.")
        options["limit"] = limit
    if period and contract.dataset == CF:
        start, end = (date.fromisoformat(period[f]) for f in ("start_date", "end_date"))
        if start.day != 1 or end.day != calendar.monthrange(end.year, end.month)[1]:
            unsupported.append(("period", "monthly_grain_only"))
    # All syntax/type validation above precedes unsupported semantics.
    if unsupported:
        field, code = unsupported[0]
        raise ContractError("UNSUPPORTED", code, "This operation is outside contract 1.0; no substitute was calculated.", field)
    return Request(name, contract.dataset, contract.kind, filters, period, group, measures, stats, options, detail)


def predicates(request):
    """Return trusted SQL expressions plus bound values, sorted by public field."""
    expressions = []
    for field, predicate in request.filters.items():
        column = 'd."' + FIELDS[request.dataset][field] + '"'
        nulls = predicate["nulls"]
        operator = "eq" if "eq" in predicate else "in" if "in" in predicate else None
        if operator:
            values = [predicate["eq"]] if operator == "eq" else predicate["in"]
            sql = column + " IN (" + ",".join("?" for _ in values) + ")"
            if nulls == "include":
                sql = "(" + sql + " OR " + column + " IS NULL)"
        else:
            values = []
            sql = "1" if nulls == "include" else column + (" IS NULL" if nulls == "only" else " IS NOT NULL")
        expressions.append((field, sql, values))
    if request.period:
        field = DATES[request.dataset]
        column = FIELDS[request.dataset][field]
        expressions.append((field, f'd."{column}" BETWEEN ? AND ?', list(request.period.values())))
    return sorted(expressions, key=lambda item: item[0])
