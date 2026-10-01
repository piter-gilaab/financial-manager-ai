"""Presentation only; amounts and statuses come from the manager."""

import json
from decimal import Decimal

from src.manager.security import is_data_only


PREVIEW_SIZE = 10
EXPLANATION_PREVIEW_CHARACTERS = 2_000
DEFAULT_USAGE_HINTS = (
    "Use --full for expanded human output.",
    "Use --json for complete structured evidence.",
)


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


def _preview(value):
    """Build a bounded display copy, preserving collection order and values."""
    if isinstance(value, dict):
        linked_references = None
        items = value.get("items")
        references = value.get("references")
        if isinstance(items, list) and isinstance(references, list):
            reference_ids = {
                assessment.get("reference_id")
                for item in items[:PREVIEW_SIZE] if isinstance(item, dict)
                for assessment in item.get("assessments", {}).values() if isinstance(assessment, dict)
                if assessment.get("reference_id") is not None
            }
            if reference_ids:
                linked_references = [
                    reference for reference in references
                    if isinstance(reference, dict) and reference.get("reference_id") in reference_ids
                ]
        return {
            key: (_linked_reference_preview(linked_references, len(item))
                  if key == "references" and linked_references is not None
                  else f"{len(item)} warning entries; presented once below."
                  if key == "warnings" and isinstance(item, list)
                  else _preview(item))
            for key, item in value.items()
        }
    if isinstance(value, list):
        total = len(value)
        if total > PREVIEW_SIZE:
            returned = PREVIEW_SIZE
            return {
                "presentation": f"Showing {returned} of {total} items; {total - returned} omitted.",
                "returned_item_count": returned,
                "total_item_count": total,
                "omitted_item_count": total - returned,
                "preview_items": [_preview(item) for item in value[:returned]],
            }
        return [_preview(item) for item in value]
    return value


def _linked_reference_preview(references, total):
    returned = len(references)
    if returned == total and total <= PREVIEW_SIZE:
        return [_preview(item) for item in references]
    return {
        "presentation": f"Showing {returned} of {total} linked items; {total - returned} omitted.",
        "returned_item_count": returned,
        "total_item_count": total,
        "omitted_item_count": total - returned,
        "preview_items": [_preview(item) for item in references],
    }


def _collect_warnings(value, found, step_id):
    if isinstance(value, dict):
        for key, item in value.items():
            if key == "warnings" and isinstance(item, list):
                for warning in item:
                    nested = warning.get("items") if isinstance(warning, dict) and "code" not in warning else None
                    nested_step = warning.get("step_id", step_id) if isinstance(warning, dict) else step_id
                    entries = nested if isinstance(nested, list) else (warning,)
                    for entry in entries:
                        match = next((item for item in found if item["warning"] == entry), None)
                        if match is None:
                            match = {"warning": entry, "step_ids": []}
                            found.append(match)
                        if nested_step is not None and nested_step not in match["step_ids"]:
                            match["step_ids"].append(nested_step)
            else:
                _collect_warnings(item, found, step_id)
    elif isinstance(value, list):
        for item in value:
            _collect_warnings(item, found, step_id)


def _warnings(result):
    """Collect exact warning entries once while retaining application step scope."""
    found = []
    for step in result["results"]:
        _collect_warnings(step["response"], found, step["step_id"])
    _collect_warnings({"warnings": result["warnings"]}, found, None)
    output = []
    for item in found:
        warning = item["warning"]
        if isinstance(warning, dict):
            output.append({**warning, "applies_to_steps": item["step_ids"]})
        else:
            output.append({"warning": warning, "applies_to_steps": item["step_ids"]})
    return output


def _explanation(text):
    text = "\n".join(line for line in text.splitlines()
                     if not line.startswith(("Quality warning:", "Quality flags:")))
    if len(text) <= EXPLANATION_PREVIEW_CHARACTERS:
        return text
    omitted = len(text) - EXPLANATION_PREVIEW_CHARACTERS
    return (text[:EXPLANATION_PREVIEW_CHARACTERS]
            + f"\n[{omitted} characters omitted from explanation; use --full for expanded human output.]")


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


def answer(result, *, full=False, usage_hints=DEFAULT_USAGE_HINTS):
    lines = [f"Status: {result['execution_status']}", f"Execution: {result['execution_state']}",
             plan(result["routing"])]
    unknown_currency = False
    screening_evidence = False
    coverage_evidence = False
    if result["clarification"]:
        lines.extend(("Clarification required:", details(result["clarification"])))
    for step in result["results"]:
        response = step["response"]
        lines.extend((f"\nStep {step['step_id']} — {step['capability']}: {response['execution_status']}",
                      response["summary"] if full else _explanation(response["summary"])))
        evidence = response["delegated_result"]
        if evidence is not None:
            # Unwrap only the existing analysis envelope for display; the full
            # unchanged application response remains available in JSON mode.
            evidence = evidence.get("tool_result", evidence)
            if evidence is not None:
                currency = evidence.get("currency") if isinstance(evidence, dict) else None
                unknown_currency |= isinstance(currency, dict) and currency.get("status") == "UNKNOWN"
                records = evidence.get("records") if isinstance(evidence, dict) else None
                evidence_result = evidence.get("result") if isinstance(evidence, dict) else None
                result_items = evidence_result.get("items") if isinstance(evidence_result, dict) else None
                screening_evidence |= (step["capability"] == "ANOMALY_DETECTION"
                                       and evidence_result is not None)
                screening_evidence |= (isinstance(result_items, list)
                                       and any(isinstance(item, dict) and "assessments" in item
                                               for item in result_items))
                coverage_evidence |= (isinstance(records, dict)
                                      and any(key in records for key in ("excluded", "exclusion_reasons")))
                coverage_evidence |= (isinstance(evidence_result, dict)
                                      and any("coverage" in key for key in evidence_result))
                lines.extend(("Structured evidence:", details(evidence if full else _preview(evidence))))
        for key in ("warnings", "limitations", "errors"):
            if response[key] and (full or key != "warnings"):
                lines.extend((key.capitalize() + ":", details(response[key])))
    for key in ("warnings", "limitations", "errors", "not_performed"):
        if result[key] and (full or key != "warnings"):
            lines.extend((key.replace("_", " ").capitalize() + ":", details(result[key])))
    if not full:
        warnings = _warnings(result)
        if warnings:
            lines.extend(("Warnings (identical entries shown once):",
                          details([_preview(warning) for warning in warnings])))
        notes = []
        if unknown_currency:
            notes.append("UNKNOWN currency means the denomination is not established by authoritative evidence.")
        if screening_evidence:
            notes.extend((
                "CANDIDATE = statistical screening candidate for investigation; it is not fraud, error, misconduct, probability, or certainty.",
                "NOT_ASSESSED means the stated screening assessment could not be performed for that record.",
            ))
        if coverage_evidence:
            notes.append("Coverage and exclusions describe which source records participated and which did not.")
        if notes:
            lines.extend(("Terminology:", *notes))
        lines.extend(usage_hints)
    return "\n".join(lines)
