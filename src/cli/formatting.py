"""Presentation only; amounts and statuses come from the manager."""

import json
from decimal import Decimal

from src.manager.security import is_data_only


def terminal_text(text):
    """Escape terminal controls in human display, without changing source data."""
    return "".join(char if char.isprintable() or char == "\n" else f"\\u{ord(char):04x}" for char in text)


def details(value):
    if not is_data_only(value, allow_decimal=True):
        raise ValueError("Only data-only results may be displayed.")

    def exact_decimal(item):
        if type(item) is Decimal and item.is_finite():
            return format(item, "f")
        raise ValueError("Unsupported result value.")

    return json.dumps(value, indent=2, ensure_ascii=True, allow_nan=False, default=exact_decimal)


def capabilities(catalog):
    lines = ["Capabilities"]
    for item in catalog:
        lines.append(f"{item['name']}: {item['status']}")
        if item["reason"]:
            lines.append("  " + item["reason"])
        lines.extend("  Limitation: " + value for value in item["limitations"])
    return "\n".join(lines)


def plan(decision):
    lines = [f"Routing: {decision['status']}", decision["message"],
             "Reason: " + decision["reason_code"]]
    for step in decision["steps"]:
        item = step["capability"]
        lines.append(f"Step {step['step_id']} — {item['name']}: {item['status']}")
        if item["reason"]:
            lines.append(item["reason"])
        lines.extend(step["notes"])
        lines.extend(("Request:", details(step["normalized_request"])))
    if decision["clarification"]:
        lines.extend(("Clarification required:", details(decision["clarification"])))
    return "\n".join(lines)


def answer(result):
    lines = [f"Status: {result['execution_status']}", f"Execution: {result['execution_state']}",
             plan(result["routing"])]
    if result["clarification"]:
        lines.extend(("Clarification required:", details(result["clarification"])))
    for step in result["results"]:
        response = step["response"]
        lines.extend((f"\nStep {step['step_id']} — {step['capability']}: {response['execution_status']}",
                      response["summary"]))
        evidence = response["delegated_result"]
        if evidence is not None:
            # Unwrap only the existing analysis envelope for display; the full
            # unchanged application response remains available in JSON mode.
            evidence = evidence.get("tool_result", evidence)
            if evidence is not None:
                lines.extend(("Structured evidence:", details(evidence)))
        for key in ("warnings", "limitations", "errors"):
            if response[key]:
                lines.extend((key.capitalize() + ":", details(response[key])))
    for key in ("warnings", "limitations", "errors", "not_performed"):
        if result[key]:
            lines.extend((key.replace("_", " ").capitalize() + ":", details(result[key])))
    return "\n".join(lines)
