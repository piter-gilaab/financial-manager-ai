"""Financial Core calculations over approved canonical SALES_RECORD inputs."""

from dataclasses import dataclass
from collections import Counter, defaultdict

from .arithmetic import canonical_count_sum, canonical_decimal, canonical_statistics
from .quality import (
    QualityAssessment,
    coverage,
    dimension_coverage_counts,
    ordered_group_keys,
    result_status,
    unfiltered_record_accounting,
)


@dataclass(frozen=True, slots=True)
class CanonicalSalesRecord:
    canonical_record_id: str
    source_row_number: int
    source_sheet: str | None
    sales: str | None = None
    sales_status: str = "source_missing"
    country: str | None = None
    country_status: str = "source_missing"
    transaction_date: str | None = None
    transaction_date_status: str = "source_missing"
    segment: str | None = None
    segment_status: str = "source_missing"
    product: str | None = None
    product_status: str = "source_missing"
    profit: str | None = None
    profit_status: str = "source_missing"
    discount: str | None = None
    discount_status: str = "source_missing"
    units_sold: str | None = None
    units_sold_status: str = "source_missing"


def sales_record_count(records: tuple[CanonicalSalesRecord, ...]) -> dict:
    population = len(records)
    accounting = unfiltered_record_accounting(population, ())
    status, no_data = result_status(
        accounting, False, population, "count", QualityAssessment({}, False),
    )
    return {
        "status": status,
        "result": {"record_count": population},
        "records": accounting,
        "participation": {
            record.canonical_record_id: ("USED", None) for record in records
        },
        "no_data_reason": no_data,
    }


def sales_summary(records: tuple[CanonicalSalesRecord, ...]) -> dict:
    used = sum(record.sales is not None for record in records)
    missing = len(records) - used
    reason = "measure:sales:source_missing"
    measure_coverage = coverage(len(records), used, [reason] * missing)
    reasons = [reason] * missing
    accounting = unfiltered_record_accounting(len(records), reasons)
    statistics = canonical_count_sum(
        record.sales for record in records if record.sales is not None
    )
    statistics.update(unit="monetary", coverage=measure_coverage)
    status, no_data = result_status(
        accounting, False, len(records), "summary", QualityAssessment({}, bool(missing)),
    )
    participation = {
        record.canonical_record_id: (
            ("USED", None) if record.sales is not None else ("EXCLUDED", reason)
        ) for record in records
    }
    return {
        "status": status,
        "result": {"measures": {"sales": statistics}},
        "records": accounting,
        "participation": participation,
        "no_data_reason": no_data,
        "missing_sales": missing,
    }


def _dimension_value(record: CanonicalSalesRecord, dimension: str) -> str | None:
    if dimension == "country":
        return record.country
    if dimension == "transaction_date":
        return record.transaction_date
    if dimension == "segment":
        return record.segment
    if dimension == "product":
        return record.product
    raise ValueError("Unrecognized internal SALES_RECORD dimension")


def _dimension_status(record: CanonicalSalesRecord, dimension: str) -> str:
    if dimension == "country":
        return record.country_status
    if dimension == "transaction_date":
        return record.transaction_date_status
    if dimension == "segment":
        return record.segment_status
    if dimension == "product":
        return record.product_status
    raise ValueError("Unrecognized internal SALES_RECORD dimension")


def _sales_by_dimension(records: tuple[CanonicalSalesRecord, ...], *,
                        dimension: str, exclude_missing: bool,
                        key_length: int | None = None) -> dict:
    unavailable_dimensions = Counter(
        _dimension_status(record, dimension)
        for record in records if _dimension_value(record, dimension) is None
    )
    missing_dimension = sum(unavailable_dimensions.values())
    dimension_coverage = dimension_coverage_counts(
        len(records),
        unavailable_dimensions,
        "exclude" if exclude_missing else "bucket",
    )
    groups = defaultdict(list)
    participation = {}
    top_reasons = []
    for record in records:
        value = _dimension_value(record, dimension)
        if value is None and exclude_missing:
            dimension_reason = f"dimension:{dimension}:{_dimension_status(record, dimension)}"
            participation[record.canonical_record_id] = ("EXCLUDED", dimension_reason)
            top_reasons.append(dimension_reason)
            continue
        key = value if value is None or key_length is None else value[:key_length]
        groups[key].append(record)
        if record.sales is None:
            measure_reason = f"measure:sales:{record.sales_status}"
            participation[record.canonical_record_id] = ("EXCLUDED", measure_reason)
            top_reasons.append(measure_reason)
        else:
            participation[record.canonical_record_id] = ("USED", None)
    output = []
    for key in ordered_group_keys(groups):
        group_records = groups[key]
        used_in_group = sum(record.sales is not None for record in group_records)
        measure_reasons = [
            f"measure:sales:{record.sales_status}"
            for record in group_records if record.sales is None
        ]
        measure = canonical_count_sum(
            record.sales for record in group_records if record.sales is not None
        )
        measure.update(
            unit="monetary",
            coverage=coverage(len(group_records), used_in_group, measure_reasons),
        )
        output.append({
            "key": {"value": key, "kind": "unavailable" if key is None else "source_value"},
            "record_count": len(group_records),
            "measures": {"sales": measure},
            "canonical_record_ids": [record.canonical_record_id for record in group_records],
        })
    used = sum(state == "USED" for state, _ in participation.values())
    accounting = unfiltered_record_accounting(len(records), top_reasons)
    global_coverage = coverage(len(records), used, top_reasons)
    eligible = len(records) - missing_dimension if exclude_missing else len(records)
    status, no_data = result_status(
        accounting,
        True,
        eligible,
        "group",
        QualityAssessment({}, bool(missing_dimension or top_reasons)),
    )
    return {
        "status": status,
        "result": {
            "groups": output,
            "dimension_coverage": dimension_coverage,
            "measure_coverage": {"sales": global_coverage},
        },
        "records": accounting,
        "participation": participation,
        "no_data_reason": no_data,
        "missing_sales": sum(
            record.sales is None and record.sales_status == "source_missing"
            for record in records
        ),
        f"missing_{dimension}": unavailable_dimensions.get("source_missing", 0),
        "unavailable_by_field": {
            "sales": dict(Counter(
                record.sales_status for record in records if record.sales is None
            )),
            dimension: dict(unavailable_dimensions),
        },
    }


def sales_by_country(records: tuple[CanonicalSalesRecord, ...], *, exclude_missing: bool) -> dict:
    return _sales_by_dimension(
        records, dimension="country", exclude_missing=exclude_missing,
    )


def sales_by_period(records: tuple[CanonicalSalesRecord, ...], *, exclude_missing: bool,
                    granularity) -> dict:
    key_length = 7 if granularity.value == "MONTH" else 4
    return _sales_by_dimension(
        records, dimension="transaction_date", exclude_missing=exclude_missing,
        key_length=key_length,
    )


def sales_by_segment(records: tuple[CanonicalSalesRecord, ...], *, exclude_missing: bool) -> dict:
    return _sales_by_dimension(
        records, dimension="segment", exclude_missing=exclude_missing,
    )


def sales_by_product(records: tuple[CanonicalSalesRecord, ...], *, exclude_missing: bool) -> dict:
    return _sales_by_dimension(
        records, dimension="product", exclude_missing=exclude_missing,
    )


def _measure_summary(records: tuple[CanonicalSalesRecord, ...], *, name: str,
                     unit: str, statistics: tuple[str, ...], value_of, status_of) -> dict:
    tokens = []
    reasons = []
    participation = {}
    unavailable = Counter()
    for record in records:
        value = value_of(record)
        if value is None:
            status = status_of(record)
            reason = f"measure:{name}:{status}"
            reasons.append(reason)
            unavailable[status] += 1
            participation[record.canonical_record_id] = ("EXCLUDED", reason)
        else:
            tokens.append(value)
            participation[record.canonical_record_id] = ("USED", None)
    measure = canonical_statistics(tokens, statistics)
    measure.update(
        unit=unit,
        coverage=coverage(len(records), len(tokens), reasons),
    )
    accounting = unfiltered_record_accounting(len(records), reasons)
    status, no_data = result_status(
        accounting, False, len(records), "summary",
        QualityAssessment({}, bool(reasons)),
    )
    return {
        "status": status,
        "result": {"measures": {name: measure}},
        "records": accounting,
        "participation": participation,
        "no_data_reason": no_data,
        "unavailable_by_field": {name: dict(unavailable)} if unavailable else {},
    }


def profit_summary(records: tuple[CanonicalSalesRecord, ...]) -> dict:
    summary = _measure_summary(
        records,
        name="profit",
        unit="monetary",
        statistics=("count", "sum"),
        value_of=lambda record: record.profit,
        status_of=lambda record: record.profit_status,
    )
    values = [canonical_decimal(record.profit) for record in records if record.profit is not None]
    summary["result"].update(
        record_count=len(records),
        negative_count=sum(value < 0 for value in values),
        zero_count=sum(value == 0 for value in values),
        positive_count=sum(value > 0 for value in values),
    )
    return summary


def discount_analysis(records: tuple[CanonicalSalesRecord, ...]) -> dict:
    summary = _measure_summary(
        records,
        name="discount",
        unit="monetary",
        statistics=("count", "sum", "mean", "min", "max"),
        value_of=lambda record: record.discount,
        status_of=lambda record: record.discount_status,
    )
    unavailable = summary.get("unavailable_by_field", {}).get("discount", {})
    summary["result"].update(
        record_count=len(records),
        unavailable_value_count=sum(unavailable.values()),
    )
    return summary


def units_sold_summary(records: tuple[CanonicalSalesRecord, ...]) -> dict:
    return _measure_summary(
        records,
        name="units_sold",
        unit="quantity",
        statistics=("count", "sum", "min", "max"),
        value_of=lambda record: record.units_sold,
        status_of=lambda record: record.units_sold_status,
    )
