"""Human presentation for the data-only onboarding facade."""


_NAMES = {
    "FINANCIAL_ANALYSIS": "Financial Analysis",
    "ANOMALY_DETECTION": "Anomaly Detection",
    "CASH_FLOW_FORECASTING": "Cash Flow Forecasting",
    "DOCUMENT_RETRIEVAL": "Document Retrieval",
}


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
            supported = [item for item in financial.get("operations", ())
                         if item["state"] == "SUPPORTED"]
            blocked = [item for item in financial.get("operations", ())
                       if item["state"] != "SUPPORTED"]
            lines.append("Executable operations:")
            lines.extend(
                f"- {item['identifier']}: {item['state']}"
                for item in supported
            )
            if blocked:
                lines.append("Unavailable operations:")
                lines.extend(
                    f"- {item['identifier']}: {item['state']}"
                    + (f" ({'; '.join(item.get('reasons', ()))})"
                       if item.get("reasons") else "")
                    for item in blocked
                )
            disclosures = financial.get("limitations") or financial.get("reasons", ())
            if disclosures:
                lines.append("Limitations:")
                lines.extend(f"- {limitation}" for limitation in disclosures)
        return "\n".join(lines)
    raise ValueError("Unsupported dataset presentation.")
