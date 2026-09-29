"""Exact Tukey fences over documented source-record cohorts, without model fitting."""

from collections import Counter, defaultdict
from decimal import Decimal, DecimalException

from src.financial.arithmetic import decimal, exact_context
from src.financial.contracts import CF, RG, FIELDS
from src.financial.models import blocker
from src.financial.quality import coverage, dimension_coverage


MINIMUM_SIZE = 30
PEERS = {RG: {"debit_credit": "credit_debit_code", "voucher_type": "journal_voucher_type_code"},
         CF: {"segment": "segment", "sale_price": "sale_price"}}
PRESENT = ("kept", "parsed", "standardized")
ABSENT = ("source_missing", "unresolved_placeholder", "parsing_failed")


def value(row, column, *, numeric=False):
    token, status = row[column], row[column + "_status"]
    if token is None and status in ABSENT:
        return None
    if token is None or status not in PRESENT:
        blocker("inconsistent_value_status", "An assessment dependency has inconsistent value/status evidence.")
    if numeric:
        return decimal(token)
    if not isinstance(token, str) or not token:
        blocker("invalid_peer_label", "A peer label is not a populated source string.")
    return token


def reference(values, identity, definition, keys, *, both_tails):
    """Linear quartiles at (n-1)*p; precision-60 traps prevent rounded fences."""
    out = {"reference_id": identity, "peer_definition": list(definition), "peer_values": keys,
           "numeric_size": len(values), "eligibility": "NOT_ASSESSED", "reason": None,
           "q1": None, "q3": None, "iqr": None, "lower_fence": None, "upper_fence": None}
    if len(values) < MINIMUM_SIZE:
        out["reason"] = "insufficient_numeric_records"
        return out
    ordered = sorted(values)

    def quartile(numerator):
        index, remainder = divmod((len(ordered) - 1) * numerator, 4)
        lo = ordered[index]
        if not remainder:
            return +lo
        return lo + (ordered[index + 1] - lo) * Decimal(remainder) / Decimal(4)

    with exact_context():
        q1, q3 = quartile(1), quartile(3)
        iqr = q3 - q1
        out.update(q1=format(q1, "f"), q3=format(q3, "f"), iqr=format(iqr, "f"))
        if iqr == 0:
            out["reason"] = "zero_iqr"
            return out
        out.update(eligibility="ELIGIBLE", upper_fence=format(q3 + Decimal("1.5") * iqr, "f"),
                   lower_fence=format(q1 - Decimal("1.5") * iqr, "f") if both_tails else None)
    return out


def assessment(number, ref, reason=None):
    output = {"status": "NOT_ASSESSED", "reason": reason, "reference_id": ref["reference_id"] if ref else None,
              "numeric_peer_size": ref["numeric_size"] if ref else None, "tail": None}
    if reason:
        return output
    if ref["eligibility"] != "ELIGIBLE":
        output["reason"] = ref["reason"]
        return output
    if number > Decimal(ref["upper_fence"]):
        output.update(status="CANDIDATE", tail="upper")
    elif ref["lower_fence"] is not None and number < Decimal(ref["lower_fence"]):
        output.update(status="CANDIDATE", tail="lower")
    else:
        output["status"] = "NOT_SELECTED"
    return output


def screen(rows, dataset, measure):
    """Pure internal computation; rows supplied only by the verified snapshot service."""
    rows = sorted(rows, key=lambda row: (row["source_row_number"], row["record_id"]))
    column, peers = FIELDS[dataset][measure], PEERS[dataset]
    prepared, groups, group_values = [], defaultdict(list), {}
    try:
        for row in rows:
            number = value(row, column, numeric=True)
            # Check every numeric input, not only operands used by quartiles.
            with exact_context():
                if number is not None:
                    checked = +number
                    if dataset == RG and checked < 0:
                        blocker("unsupported_accounting_sign", "This upper-tail accounting baseline requires nonnegative source amounts.")
            key, missing = [], []
            for field, source in peers.items():
                v = value(row, source, numeric=field == "sale_price")
                if v is None:
                    missing.append(f"dimension:{field}:{row[source + '_status']}")
                if field == "sale_price" and v is not None:
                    with exact_context():
                        v = +v
                key.append(v)
            key = tuple(key)
            if not missing:
                groups[key]  # Keep complete peers even with no numeric target values.
                group_values.setdefault(key, {f: row[c] for f, c in peers.items()})
                if number is not None:
                    groups[key].append(number)
            prepared.append((row, number, key, missing))
        global_ref = reference([n for _, n, _, _ in prepared if n is not None], "global", (), {}, both_tails=dataset == CF)
        references, peer_refs = [global_ref], {}
        for index, key in enumerate(sorted(groups), 1):
            ref = reference(groups[key], f"peer:{index}", peers, group_values[key], both_tails=dataset == CF)
            references.append(ref)
            peer_refs[key] = ref
    except DecimalException:
        blocker("exact_arithmetic_limit", "Exact statistical arithmetic exceeded precision 60; no assessments returned.")

    items, exclusions = [], []
    for row, number, key, missing in prepared:
        measure_reason = f"measure:{measure}:{row[column + '_status']}" if number is None else None
        if measure_reason:
            exclusions.append(measure_reason)
        peer_ref = None if missing else peer_refs[key]
        # Dimension before measure is the disjoint peer abstention reason;
        # all missing dependencies remain independently visible below.
        peer_reason = missing[0] if missing else measure_reason
        items.append({
            "lineage": {k: row[k] for k in ("record_id", "run_id", "source_id", "source_row_number", "processed_row_number")},
            "dataset": dataset, "measure": measure, "observed_value": row[column],
            "observed_raw": row[column + "_raw"], "observed_status": row[column + "_status"],
            "peer_values": {f: {"value": row[c], "status": row[c + "_status"]} for f, c in peers.items()},
            "assessments": {"global": assessment(number, global_ref, measure_reason),
                            "peer": assessment(number, peer_ref, peer_reason)},
            "unavailable_dependencies": missing + ([measure_reason] if measure_reason else []),
        })
    summaries = {}
    for mode in ("global", "peer"):
        statuses = Counter(item["assessments"][mode]["status"] for item in items)
        reasons = Counter(item["assessments"][mode]["reason"] for item in items
                          if item["assessments"][mode]["status"] == "NOT_ASSESSED")
        summaries[mode] = {"candidate": statuses["CANDIDATE"], "not_selected": statuses["NOT_SELECTED"],
                           "not_assessed": statuses["NOT_ASSESSED"], "not_assessed_reasons": dict(sorted(reasons.items()))}
    comparison = dict.fromkeys(("both_assessed", "both_candidate", "global_only_candidate", "peer_only_candidate", "neither_candidate"), 0)
    for item in items:
        a, b = (item["assessments"][mode]["status"] for mode in ("global", "peer"))
        if "NOT_ASSESSED" not in (a, b):
            comparison["both_assessed"] += 1
            key = "both_candidate" if a == b == "CANDIDATE" else "global_only_candidate" if a == "CANDIDATE" else "peer_only_candidate" if b == "CANDIDATE" else "neither_candidate"
            comparison[key] += 1
    return {
        "references": references, "items": items, "summary": summaries, "comparison": comparison,
        "measure_coverage": coverage(len(rows), len(rows) - len(exclusions), exclusions),
        "dimension_coverage": {f: dimension_coverage(rows, f, c, "not_assessed") for f, c in peers.items()},
    }
