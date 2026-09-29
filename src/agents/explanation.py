"""Render original evidence without arithmetic, inference, or model rewriting."""

import json


def display(value):
    # Exact decimal strings are never parsed or reformatted as numbers.
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True)


def explain(evidence):
    lines = [f"The {evidence['query_name']} tool returned {evidence['status']} for {evidence['dataset']}."]
    if evidence.get("currency") is not None:
        currency = evidence["currency"]
        lines.append(f"Currency status: {currency['status']}; currency code: {display(currency['code'])}.")
    if evidence.get("records") is not None:
        lines.append("Record accounting reported by the tool: " + display(evidence["records"]) + ".")
    payload = evidence.get("result")
    if payload is not None:
        # Include every result field, including coverage and unavailable buckets.
        # Rendering a large result is intentionally lossless, not an LLM summary.
        for field, value in payload.items():
            if field == "record_count":
                lines.append(f"The tool counted {display(value)} source records.")
            elif field == "measures":
                for measure, facts in value.items():
                    name = measure.replace("_", " ")
                    for statistic, fact in facts.items():
                        lines.append(f"For {name}, the reported {statistic.replace('_', ' ')} is {display(fact)}.")
            else:
                lines.append(field.replace("_", " ").capitalize() + ": " + display(value) + ".")
    quality = evidence.get("quality", {})
    for warning in quality.get("warnings", []):
        lines.append("Quality warning: " + display(warning) + ".")
    if quality.get("flags"):
        lines.append("Quality flags: " + display(quality["flags"]) + ".")
    for error in evidence.get("errors", []):
        lines.append("Tool error: " + display(error) + ".")
    lines.append("Values describe imported source records under the selected contract and filters.")
    return "\n".join(lines)
