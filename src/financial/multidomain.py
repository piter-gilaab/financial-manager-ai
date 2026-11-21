"""Financial Core authority for the frozen V2 multi-domain operations.

The functions in this module accept only canonical, authenticated records and
closed parameters.  Adapters translate artifacts; all monetary, aging and net
cash arithmetic remains here.
"""

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from .arithmetic import canonical_decimal, canonical_statistics, exact_sum
from .quality import coverage, ordered_group_keys, unfiltered_record_accounting


SUMMARY_STATISTICS = ("count", "sum", "mean", "median", "min", "max")
AGING_BUCKETS = (
    "NOT_DUE", "OVERDUE_1_30", "OVERDUE_31_60",
    "OVERDUE_61_90", "OVERDUE_91_PLUS",
)


@dataclass(frozen=True, slots=True)
class CanonicalFinancialRecord:
    canonical_record_id: str
    source_row_number: int
    source_sheet: str | None
    amount: str | None = None
    amount_status: str = "source_missing"
    amount_raw: str | None = None
    due_date: str | None = None
    due_date_status: str = "source_missing"
    supplier: str | None = None
    supplier_status: str = "source_missing"
    customer: str | None = None
    customer_status: str = "source_missing"
    settlement_status: str | None = None
    settlement_status_status: str = "source_missing"
    settlement_status_raw: str | None = None
    transaction_date: str | None = None
    transaction_date_status: str = "source_missing"
    cash_direction: str | None = None
    cash_direction_status: str = "source_missing"
    cash_direction_raw: str | None = None
    category: str | None = None
    category_status: str = "source_missing"
    account: str | None = None
    account_status: str = "source_missing"


def record_count(records: tuple[CanonicalFinancialRecord, ...]) -> dict:
    population = len(records)
    return {
        "status": "SUCCESS" if population else "NO_DATA",
        "result": {"record_count": population},
        "records": unfiltered_record_accounting(population, ()),
        "participation": {
            item.canonical_record_id: ("USED", None) for item in records
        },
        "no_data_reason": None if population else "no_source_records",
    }


def _measure(records, *, values, name="amount", statistics=SUMMARY_STATISTICS):
    tokens, reasons, participation = [], [], {}
    for item in records:
        value, state = values(item)
        if value is None:
            reason = f"measure:{name}:{state}"
            reasons.append(reason)
            participation[item.canonical_record_id] = ("EXCLUDED", reason)
        else:
            tokens.append(value)
            participation[item.canonical_record_id] = ("USED", None)
    measure = canonical_statistics(tokens, statistics)
    measure.update(unit="monetary", coverage=coverage(len(records), len(tokens), reasons))
    return {
        "status": "NO_DATA" if not tokens else "PARTIAL" if reasons else "SUCCESS",
        "result": {"measures": {name: measure}},
        "records": unfiltered_record_accounting(len(records), reasons),
        "participation": participation,
        "no_data_reason": "no_numeric_values" if not tokens else None,
        "unavailable_by_field": {name: dict(sorted(Counter(
            state for item in records
            for value, state in (values(item),) if value is None
        ).items()))},
    }


def obligation_summary(records: tuple[CanonicalFinancialRecord, ...]) -> dict:
    return _measure(
        records,
        values=lambda item: (item.amount, item.amount_status),
    )


def obligation_by_dimension(
    records: tuple[CanonicalFinancialRecord, ...], *, dimension: str,
    exclude_missing: bool, granularity: str | None = None,
) -> dict:
    if dimension not in {"supplier", "customer", "due_date"}:
        raise ValueError("Unrecognized obligation dimension")
    if granularity not in {None, "MONTH", "YEAR"}:
        raise ValueError("Unsupported period granularity")
    groups = defaultdict(list)
    dimension_unavailable = Counter()
    participation, top_reasons = {}, []
    for item in records:
        value = getattr(item, dimension)
        state = getattr(item, dimension + "_status")
        if value is None:
            dimension_unavailable[state] += 1
            if exclude_missing:
                reason = f"dimension:{dimension}:{state}"
                participation[item.canonical_record_id] = ("EXCLUDED", reason)
                top_reasons.append(reason)
                continue
        key = value
        if key is not None and dimension == "due_date":
            key = key[:7] if granularity == "MONTH" else key[:4]
        groups[key].append(item)
        if item.amount is None:
            reason = f"measure:amount:{item.amount_status}"
            participation[item.canonical_record_id] = ("EXCLUDED", reason)
            top_reasons.append(reason)
        else:
            participation[item.canonical_record_id] = ("USED", None)
    output = []
    for key in ordered_group_keys(groups):
        members = groups[key]
        tokens = [item.amount for item in members if item.amount is not None]
        reasons = [
            f"measure:amount:{item.amount_status}" for item in members
            if item.amount is None
        ]
        measure = canonical_statistics(tokens, SUMMARY_STATISTICS)
        measure.update(unit="monetary", coverage=coverage(len(members), len(tokens), reasons))
        output.append({
            "key": {"value": key, "kind": "unavailable" if key is None else "source_value"},
            "record_count": len(members),
            "measures": {"amount": measure},
            "canonical_record_ids": [item.canonical_record_id for item in members],
        })
    available = len(records) - sum(dimension_unavailable.values())
    result = {
        "groups": output,
        "dimension_coverage": {
            "candidates": len(records), "available": available,
            "unavailable": len(records) - available,
            "unavailable_by_status": dict(sorted(dimension_unavailable.items())),
            "percentage": coverage(len(records), available, [
                f"dimension:{dimension}:{state}"
                for state, count in dimension_unavailable.items() for _ in range(count)
            ])["percentage"],
            "policy": "exclude" if exclude_missing else "bucket",
        },
        "measure_coverage": {"amount": coverage(
            len(records), sum(item.amount is not None for item in records), [
                f"measure:amount:{item.amount_status}" for item in records if item.amount is None
            ],
        )},
    }
    eligible = len(records) - sum(dimension_unavailable.values()) if exclude_missing else len(records)
    used = sum(state == "USED" for state, _ in participation.values())
    status = "NO_DATA" if not eligible or not used else "PARTIAL" if top_reasons or dimension_unavailable else "SUCCESS"
    return {
        "status": status, "result": result,
        "records": unfiltered_record_accounting(len(records), top_reasons),
        "participation": participation,
        "no_data_reason": "no_group_eligible_records" if not eligible else "no_numeric_values" if not used else None,
        "unavailable_by_field": {
            dimension: dict(sorted(dimension_unavailable.items())),
            "amount": dict(sorted(Counter(
                item.amount_status for item in records if item.amount is None
            ).items())),
        },
    }


def _aging_bucket(due_date: str, reference: date) -> str:
    days = (reference - date.fromisoformat(due_date)).days
    if days <= 0:
        return "NOT_DUE"
    if days <= 30:
        return "OVERDUE_1_30"
    if days <= 60:
        return "OVERDUE_31_60"
    if days <= 90:
        return "OVERDUE_61_90"
    return "OVERDUE_91_PLUS"


def _aging_eligibility(item: CanonicalFinancialRecord):
    if item.settlement_status in {"SETTLED", "CANCELLED"}:
        return None, item.settlement_status.casefold()
    if item.settlement_status != "OPEN":
        return None, f"status_{item.settlement_status_status}"
    if item.amount is None:
        return None, f"amount_{item.amount_status}"
    if canonical_decimal(item.amount) <= 0:
        return None, "non_positive_open_balance"
    if item.due_date is None:
        return None, f"due_date_{item.due_date_status}"
    return item, None


def obligation_aging(records: tuple[CanonicalFinancialRecord, ...], *, as_of_date: str) -> dict:
    reference = date.fromisoformat(as_of_date)
    grouped = {name: [] for name in AGING_BUCKETS}
    exclusions, participation = Counter(), {}
    for item in records:
        eligible, reason = _aging_eligibility(item)
        if eligible is None:
            exclusions[reason] += 1
            participation[item.canonical_record_id] = ("EXCLUDED", reason)
            continue
        bucket = _aging_bucket(item.due_date, reference)
        grouped[bucket].append(item)
        participation[item.canonical_record_id] = ("USED", None)
    buckets = []
    for name in AGING_BUCKETS:
        members = grouped[name]
        total = exact_sum(canonical_decimal(item.amount) for item in members)
        buckets.append({
            "bucket": name,
            "open_record_count": len(members),
            "balance_sum": "0" if total is None else format(total, "f"),
            "coverage": coverage(len(members), len(members), []),
            "canonical_record_ids": [item.canonical_record_id for item in members],
        })
    groups = [{
        "key": {"value": item["bucket"], "kind": "source_value"},
        "record_count": item["open_record_count"],
        "measures": {"balance": {
            "count": item["open_record_count"], "sum": item["balance_sum"],
            "unit": "monetary",
            "coverage": item["coverage"],
        }},
        "canonical_record_ids": item["canonical_record_ids"],
    } for item in buckets]
    used = sum(len(items) for items in grouped.values())
    return {
        "status": "NO_DATA" if not used else "PARTIAL" if exclusions else "SUCCESS",
        "result": {
            "as_of_date": as_of_date, "buckets": buckets, "groups": groups,
            "eligible_open_record_count": used,
            "excluded": dict(sorted(exclusions.items())),
            "coverage": coverage(len(records), used, [
                reason for reason, count in exclusions.items() for _ in range(count)
            ]),
        },
        "records": unfiltered_record_accounting(len(records), [
            reason for reason, count in exclusions.items() for _ in range(count)
        ]),
        "participation": participation,
        "no_data_reason": "no_eligible_positive_open_balance" if not used else None,
        "unavailable_by_field": {},
    }


def overdue_obligation_summary(
    records: tuple[CanonicalFinancialRecord, ...], *, as_of_date: str,
) -> dict:
    reference = date.fromisoformat(as_of_date)
    eligible_open, overdue, exclusions, participation = [], [], Counter(), {}
    for item in records:
        eligible, reason = _aging_eligibility(item)
        if eligible is None:
            exclusions[reason] += 1
            participation[item.canonical_record_id] = ("EXCLUDED", reason)
            continue
        eligible_open.append(item)
        if date.fromisoformat(item.due_date) < reference:
            overdue.append(item)
            participation[item.canonical_record_id] = ("USED", None)
        else:
            participation[item.canonical_record_id] = ("EXCLUDED", "not_overdue")
    tokens = [item.amount for item in overdue]
    measure = canonical_statistics(tokens, SUMMARY_STATISTICS)
    measure.update(unit="monetary", coverage=coverage(
        len(records), len(overdue), [
            reason for reason, count in exclusions.items() for _ in range(count)
        ] + ["not_overdue"] * (len(eligible_open) - len(overdue)),
    ))
    reasons = [reason for reason, count in exclusions.items() for _ in range(count)]
    reasons.extend(["not_overdue"] * (len(eligible_open) - len(overdue)))
    return {
        "status": "NO_DATA" if not overdue else "PARTIAL" if reasons else "SUCCESS",
        "result": {
            "as_of_date": as_of_date,
            "open_record_count": len(eligible_open),
            "overdue_record_count": len(overdue),
            "overdue_balance": measure,
            "measures": {"overdue_balance": measure},
            "excluded": dict(sorted(exclusions.items())),
        },
        "records": unfiltered_record_accounting(len(records), reasons),
        "participation": participation,
        "no_data_reason": "no_overdue_open_balance" if not overdue else None,
        "unavailable_by_field": {},
    }


def cash_magnitude(item: CanonicalFinancialRecord, convention: str):
    if item.amount is None:
        return None, f"amount_{item.amount_status}"
    if item.cash_direction not in {"INFLOW", "OUTFLOW"}:
        return None, f"cash_direction_{item.cash_direction_status}"
    value = canonical_decimal(item.amount)
    if convention == "MAGNITUDE_WITH_DIRECTION":
        if value < 0:
            return None, "amount_convention_inconsistent"
        return value, None
    if convention == "SIGNED_WITH_DIRECTION":
        if item.cash_direction == "INFLOW" and value < 0:
            return None, "amount_convention_inconsistent"
        if item.cash_direction == "OUTFLOW" and value > 0:
            return None, "amount_convention_inconsistent"
        return abs(value), None
    raise ValueError("Unsupported cash amount convention")


def cash_summary(
    records: tuple[CanonicalFinancialRecord, ...], *, direction: str,
    amount_convention: str = "MAGNITUDE_WITH_DIRECTION",
) -> dict:
    if direction not in {"INFLOW", "OUTFLOW"}:
        raise ValueError("Unsupported cash direction")

    def selected(item):
        magnitude, reason = cash_magnitude(item, amount_convention)
        if magnitude is None:
            return None, reason
        if item.cash_direction != direction:
            return None, "other_cash_direction"
        return format(magnitude, "f"), "parsed"

    result = _measure(
        records, values=selected, name=direction.casefold(),
    )
    if result["status"] == "PARTIAL" and not any(
        selected(item)[0] is None and selected(item)[1] != "other_cash_direction"
        for item in records
    ):
        result["status"] = "SUCCESS"
    return result


def cash_by_period(
    records: tuple[CanonicalFinancialRecord, ...], *, granularity: str,
    exclude_missing: bool = False,
    amount_convention: str = "MAGNITUDE_WITH_DIRECTION",
) -> dict:
    return _cash_grouped(
        records, dimension="transaction_date", granularity=granularity,
        exclude_missing=exclude_missing, amount_convention=amount_convention,
    )


def cash_by_dimension(
    records: tuple[CanonicalFinancialRecord, ...], *, dimension: str,
    exclude_missing: bool, amount_convention: str,
) -> dict:
    if dimension not in {"category", "account"}:
        raise ValueError("Unrecognized cash dimension")
    return _cash_grouped(
        records, dimension=dimension, granularity=None,
        exclude_missing=exclude_missing, amount_convention=amount_convention,
    )


def _cash_grouped(records, *, dimension, granularity, exclude_missing, amount_convention):
    if granularity not in {None, "MONTH", "YEAR"}:
        raise ValueError("Unsupported period granularity")
    groups, dimension_unavailable, participation, reasons = defaultdict(list), Counter(), {}, []
    for item in records:
        value = getattr(item, dimension)
        state = getattr(item, dimension + "_status")
        if value is None:
            dimension_unavailable[state] += 1
            if exclude_missing:
                reason = f"dimension:{dimension}:{state}"
                reasons.append(reason)
                participation[item.canonical_record_id] = ("EXCLUDED", reason)
                continue
        key = value
        if key is not None and dimension == "transaction_date":
            key = key[:7] if granularity == "MONTH" else key[:4]
        magnitude, invalid = cash_magnitude(item, amount_convention)
        groups[key].append((item, magnitude, invalid))
        if invalid:
            reasons.append(invalid)
            participation[item.canonical_record_id] = ("EXCLUDED", invalid)
        else:
            participation[item.canonical_record_id] = ("USED", None)
    output = []
    for key in ordered_group_keys(groups):
        members = groups[key]
        inflows = [m for item, m, reason in members if reason is None and item.cash_direction == "INFLOW"]
        outflows = [m for item, m, reason in members if reason is None and item.cash_direction == "OUTFLOW"]
        inflow = exact_sum(inflows) or Decimal(0)
        outflow = exact_sum(outflows) or Decimal(0)
        invalid_reasons = [reason for _, _, reason in members if reason is not None]
        inflow_reasons = [
            reason if reason is not None else "other_cash_direction"
            for item, _, reason in members
            if reason is not None or item.cash_direction != "INFLOW"
        ]
        outflow_reasons = [
            reason if reason is not None else "other_cash_direction"
            for item, _, reason in members
            if reason is not None or item.cash_direction != "OUTFLOW"
        ]
        group_coverage = coverage(len(members), len(members) - len(invalid_reasons), invalid_reasons)
        output.append({
            "key": {"value": key, "kind": "unavailable" if key is None else "source_value"},
            "record_count": len(members),
            "inflow_count": len(inflows), "outflow_count": len(outflows),
            "inflow_sum": format(inflow, "f"), "outflow_sum": format(outflow, "f"),
            "net_cash": format(inflow - outflow, "f"),
            "coverage": group_coverage,
            "measures": {
                "inflow": {"count": len(inflows), "sum": format(inflow, "f"), "unit": "monetary",
                           "coverage": coverage(len(members), len(inflows), inflow_reasons)},
                "outflow": {"count": len(outflows), "sum": format(outflow, "f"), "unit": "monetary",
                            "coverage": coverage(len(members), len(outflows), outflow_reasons)},
                "net_cash": {"sum": format(inflow - outflow, "f"), "unit": "monetary",
                             "coverage": group_coverage},
            },
            "canonical_record_ids": [item.canonical_record_id for item, _, _ in members],
        })
    used = sum(state == "USED" for state, _ in participation.values())
    eligible = len(records) - sum(dimension_unavailable.values()) if exclude_missing else len(records)
    return {
        "status": "NO_DATA" if not eligible or not used else "PARTIAL" if reasons or dimension_unavailable else "SUCCESS",
        "result": {
            "groups": output,
            "dimension": dimension,
            "granularity": granularity,
            "coverage": coverage(len(records), used, reasons),
            "dimension_coverage": {
                "candidates": len(records),
                "available": len(records) - sum(dimension_unavailable.values()),
                "unavailable": sum(dimension_unavailable.values()),
                "unavailable_by_status": dict(sorted(dimension_unavailable.items())),
                "policy": "exclude" if exclude_missing else "bucket",
            },
        },
        "records": unfiltered_record_accounting(len(records), reasons),
        "participation": participation,
        "no_data_reason": "no_group_eligible_records" if not eligible else "no_consistent_cash_values" if not used else None,
        "unavailable_by_field": {dimension: dict(sorted(dimension_unavailable.items()))},
    }
