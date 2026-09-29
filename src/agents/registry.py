"""Static Step 13 allowlist backed by Phase 4 contract metadata and validation."""

from dataclasses import asdict, dataclass

from src.financial.contracts import CONTRACTS, FILTERS, RG
from src.financial.filters import normalize

from .models import RoutingDecision, ToolIntent


APPROVED_NAMES = (
    "receiver_general_record_count", "receiver_general_amount_summary",
    "receiver_general_amount_by_debit_credit", "receiver_general_amount_by_voucher_type",
    "receiver_general_amount_by_department", "receiver_general_amount_by_period",
    "receiver_general_accounting_dimension_summary", "receiver_general_extreme_amount_records",
    "company_financials_record_count", "company_financials_sales_summary",
    "company_financials_sales_by_period", "company_financials_sales_by_country",
    "company_financials_sales_by_segment", "company_financials_sales_by_product",
    "company_financials_profit_summary", "company_financials_discount_analysis",
    "company_financials_units_sold_summary",
)


@dataclass(frozen=True, slots=True)
class ToolMetadata:
    name: str
    dataset: str
    domain: str
    purpose: str
    monetary: bool
    parameters: tuple
    filters: tuple
    fixed_group: str | None
    fixed_measures: tuple
    contract_reference: str
    limitations: tuple


def tool_metadata():
    entries = []
    for name in APPROVED_NAMES:
        spec = CONTRACTS[name]
        prefix = spec.dataset + "_"
        purpose = name.removeprefix(prefix).replace("_", " ") + " over imported source records"
        limitations = (
            "Unknown denomination; no FX or cross-dataset monetary combination.",
            "Missing values and unresolved placeholders are not zero.",
            "No fraud/anomaly classification, forecasting, RAG or business-identity inference.",
            "See docs/query_contracts.md section 12 for unsupported interpretations.",
            "DR/CR are accounting codes, not expense/revenue." if spec.dataset == RG
            else "Sales records have no verified company identity or financial-statement meaning.",
        )
        entries.append(ToolMetadata(name, spec.dataset, "accounting" if spec.dataset == RG else "sales",
                                    purpose, spec.kind != "count" and spec.measures != ("units_sold",),
                                    ("filters", "period", "quality_detail") + spec.options,
                                    FILTERS[spec.dataset], spec.group, spec.measures,
                                    "docs/query_contracts.md@1.0", limitations))
    return tuple(entries)


class ToolRegistry:
    def __init__(self, core):
        self._core = core
        self.metadata = tool_metadata()

    def catalog(self):
        return [asdict(entry) for entry in self.metadata]

    @staticmethod
    def prepare(intent):
        if not isinstance(intent, ToolIntent) or intent.tool_name not in APPROVED_NAMES:
            raise RoutingDecision("INVALID_REQUEST", "unapproved_tool", "Only the 17 approved Financial Core contracts can be called.")
        try:
            arguments = intent.arguments()
        except (ValueError, TypeError) as error:
            raise RoutingDecision("INVALID_REQUEST", "invalid_arguments", "Provider arguments must be an unambiguous JSON object.") from error
        if {"query_name", "dataset", "contract_version"} & set(arguments):
            raise RoutingDecision("INVALID_REQUEST", "reserved_identity", "Arguments cannot override contract identity.")
        request = {"contract_version": "1.0", "query_name": intent.tool_name,
                   "dataset": CONTRACTS[intent.tool_name].dataset, **arguments}
        # This is Phase 4's validator, not a second copy of its semantic rules.
        normalized = normalize(request)
        return request, normalized

    def execute(self, request):
        # Core.query performs its own final validation, including snapshot checks.
        if request.get("query_name") not in APPROVED_NAMES:
            raise RoutingDecision("INVALID_REQUEST", "unapproved_tool", "Tool is not in the Step 13 registry.")
        return self._core.query(request)
