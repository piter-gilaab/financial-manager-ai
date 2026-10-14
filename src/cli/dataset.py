"""Human presentation for the data-only onboarding facade."""


_NAMES = {
    "FINANCIAL_ANALYSIS": "Financial Analysis",
    "ANOMALY_DETECTION": "Anomaly Detection",
    "CASH_FLOW_FORECASTING": "Cash Flow Forecasting",
    "DOCUMENT_RETRIEVAL": "Document Retrieval",
}


def _render_operations(
    lines: list[str], capability: dict, *, supported_heading: str,
    unavailable_heading: str, limitations_heading: str,
) -> None:
    supported = [item for item in capability.get("operations", ())
                 if item["state"] == "SUPPORTED"]
    blocked = [item for item in capability.get("operations", ())
               if item["state"] != "SUPPORTED"]
    lines.append(supported_heading)
    lines.extend(f"- {item['identifier']}: {item['state']}" for item in supported)
    if blocked:
        lines.append(unavailable_heading)
        lines.extend(
            f"- {item['identifier']}: {item['state']}"
            + (f" ({'; '.join(item.get('reasons', ()))})"
               if item.get("reasons") else "")
            for item in blocked
        )
    disclosures = capability.get("limitations") or capability.get("reasons", ())
    if disclosures:
        lines.append(limitations_heading)
        lines.extend(f"- {limitation}" for limitation in disclosures)


def render_dataset(operation: str, payload: dict) -> str:
    if operation == "add":
        return "\n".join((
            "Dataset accepted.",
            f"Dataset ID: {payload['dataset_id']}",
            f"Rows: {payload['row_count']}",
            f"Columns: {payload['column_count']}",
            "Profiling complete.",
            f"{payload['confirmation_required_count']} semantic mappings require confirmation.",
            f"Status: {payload['lifecycle_state']}",
        ))
    if operation in {"status", "confirm", "confirm-domain", "reject", "stop"}:
        return "\n".join((
            f"Dataset ID: {payload['dataset_id']}",
            f"Status: {payload['lifecycle_state']}",
            f"Mapping version: {payload['mapping_version']}",
            f"Currency: {payload['currency_state']}",
        ))
    if operation == "profile":
        return "\n".join((
            f"Dataset ID: {payload['dataset_id']}",
            f"Rows: {payload['row_count']}",
            f"Columns: {payload['column_count']}",
            f"Duplicate row candidates: {payload['duplicate_row_candidates']}",
            f"Currency: {payload['currency_state']}",
        ))
    if operation == "mappings":
        lines = [f"Dataset ID: {payload['dataset_id']}", f"Status: {payload['status']}"]
        lines.extend(
            f"{item['source_column']}: {item['proposed_role'] or 'UNKNOWN'} ({item['status']})"
            for item in payload["proposals"]
        )
        return "\n".join(lines)
    if operation == "capabilities":
        lines = [f"Dataset ID: {payload['dataset_id']}"]
        lines.extend(f"{_NAMES[item['identifier']]}: {item['state']}" for item in payload["capabilities"])
        lines.extend((
            f"Canonical domain: {payload['canonical_domain'] or 'UNAPPROVED'}",
            f"Currency: {payload['currency']['state']}",
        ))
        financial = next(
            (item for item in payload["capabilities"]
             if item["identifier"] == "FINANCIAL_ANALYSIS"),
            None,
        )
        if financial is not None:
            _render_operations(
                lines, financial,
                supported_heading="Executable operations:",
                unavailable_heading="Unavailable operations:",
                limitations_heading="Limitations:",
            )
        anomaly = next(
            (item for item in payload["capabilities"]
             if item["identifier"] == "ANOMALY_DETECTION"),
            None,
        )
        if anomaly is not None and anomaly.get("operations"):
            _render_operations(
                lines, anomaly,
                supported_heading="Supported anomaly operations:",
                unavailable_heading="Unavailable anomaly operations:",
                limitations_heading="Anomaly limitations:",
            )
        return "\n".join(lines)
    raise ValueError("Unsupported dataset presentation.")
