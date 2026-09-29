"""Read-only statistical investigation interface over Phase 4 snapshot and quality logic."""

from collections import defaultdict
from pathlib import Path

from src.financial.contracts import CF, RG
from src.financial.currency import query_currency
from src.financial.filters import normalize
from src.financial.models import ContractError, arithmetic_metadata, invalid
from src.financial.quality import assess, observed_period, select_rows
from src.financial.snapshot import ApprovedSnapshot

from .baseline import MINIMUM_SIZE, PEERS, screen


def normalize_analysis(request):
    allowed = {"analysis_version", "dataset", "measure", "filters", "period", "quality_detail"}
    if not isinstance(request, dict) or set(request) - allowed:
        invalid(None, "Use only the documented anomaly-analysis request properties.")
    if request.get("analysis_version") != "1.0":
        invalid("analysis_version", "Only statistical analysis version 1.0 is accepted.")
    dataset = request.get("dataset")
    if dataset not in (RG, CF):
        invalid("dataset", "Select receiver_general or company_financials.")
    measure = request.get("measure")
    if not isinstance(measure, str):
        invalid("measure", "Specify the supported source measure explicitly.")
    if measure not in (("accounting_amount",) if dataset == RG else ("sales", "profit")):
        raise ContractError("UNSUPPORTED", "unsupported_measure", "This dataset/measure has no approved Step 14 baseline.", "measure")
    payload = {"contract_version": "1.0", "dataset": dataset,
               "query_name": "receiver_general_amount_summary" if dataset == RG else "company_financials_sales_summary",
               **{key: request[key] for key in ("filters", "period", "quality_detail") if key in request}}
    if dataset == CF:
        payload["measures"] = [measure]
    return normalize(payload)


def screening_warnings(result):
    warnings = [{"code": "descriptive_screening", "field": None, "scope": "dataset", "affected_records": None,
                 "message": "Investigation candidates describe source-number distributions only. Peer labels do not establish independent or currency-comparable observations; NOT_SELECTED is not a validity finding.",
                 "flag_row_numbers": []}]
    for mode, summary in result["summary"].items():
        for reason, count in summary["not_assessed_reasons"].items():
            warnings.append({"code": "assessment_unavailable", "field": mode, "scope": "assessment",
                             "affected_records": count, "reason": reason,
                             "message": f"{mode} assessment unavailable for {count} records: {reason}.", "flag_row_numbers": []})
    return warnings


def attach_quality(result, quality, flags):
    """Resolve per-record warning references without multiplying dataset flags."""
    flags_by_number = {f["flag_row_number"]: f for f in flags}
    shared, per_record = [], defaultdict(list)
    for index, warning in enumerate(quality["warnings"]):
        if warning["scope"] == "dataset":
            shared.append(index)
        elif warning["scope"] != "assessment":
            ids = {flags_by_number[n]["record_id"] for n in warning["flag_row_numbers"]}
            for record_id in ids:
                per_record[record_id].append(index)
    assessment_warnings = [(i, w) for i, w in enumerate(quality["warnings"]) if w["scope"] == "assessment"]
    for item in result["items"]:
        indices = shared + per_record[item["lineage"]["record_id"]]
        for index, warning in assessment_warnings:
            if item["assessments"][warning["field"]]["reason"] == warning["reason"]:
                indices.append(index)
        item["quality_warning_indices"] = sorted(indices)


class AnomalyService:
    """No agent, network, mutable database, arbitrary group/SQL or production fixture input."""

    def __init__(self, project_root=None):
        root = Path(project_root) if project_root is not None else Path(__file__).resolve().parents[2]
        self._snapshot = ApprovedSnapshot(root)

    def analyze(self, request):
        response = {"analysis_version": "1.0", "service": "financial_anomaly_detection",
                    "status": None, "dataset": None, "measure": None, "result": None,
                    "currency": None, "records": None, "filter_diagnostics": [],
                    "quality": {"warnings": [], "flags": [], "detail": "summary"}, "errors": [], "metadata": {}}
        try:
            normalized = normalize_analysis(request)
            dataset, measure = normalized.dataset, normalized.measures[0]
            response.update(dataset=dataset, measure=measure)
            with self._snapshot.open() as connection:
                population, flags, snapshot, fields = self._snapshot.read(connection, normalized)
            candidates, unavailable, records, diagnostics = select_rows(population, fields, dataset)
            result = screen(candidates, dataset, measure)
            cov = result["measure_coverage"]
            records.update(used=cov["used"], excluded=cov["excluded"], exclusion_reasons=cov["exclusion_reasons"])
            missing_dimensions = any(c["unavailable"] for c in result["dimension_coverage"].values())
            quality = assess(normalized, flags, population, candidates, unavailable, [], {measure: cov},
                             {"unavailable": missing_dimensions}, additional_fields=tuple(PEERS[dataset].values()))
            disclosure = quality.disclosure
            disclosure["warnings"].extend(screening_warnings(result))
            attach_quality(result, disclosure, flags)
            incomplete = any(s["not_assessed"] for s in result["summary"].values())
            status = "NO_DATA" if not candidates else "PARTIAL" if incomplete or quality.partial else "SUCCESS"
            response.update(status=status, result=result, currency=query_currency(True), records=records,
                            filter_diagnostics=diagnostics, quality=disclosure)
            response["metadata"] = {
                "snapshot": snapshot, "filters": normalized.filters, "period": normalized.period,
                "observed_period": observed_period(candidates, dataset), "quality_detail": normalized.detail,
                "method": {"name": "tukey_iqr", "version": "1.0", "quantiles": "linear_(n-1)*p",
                           "multiplier": "1.5", "minimum_numeric_records": MINIMUM_SIZE,
                           "tails": "upper" if dataset == RG else "both", "comparison": "strict",
                           "reference_population": "selected_cohort_including_assessed_record"},
                "peer_definition": list(PEERS[dataset]), "arithmetic": arithmetic_metadata(),
                "value_basis": "imported_source_records", "reference_rounding": "none_exact_decimal",
            }
            if not candidates:
                response["metadata"]["no_data_reason"] = "no_matching_records"
        except ContractError as error:
            response.update(status=error.status, errors=[error.error])
        return response
