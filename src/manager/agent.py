"""Application facade: explicit delegation plus additive local orchestration."""

from copy import deepcopy
import json

from .models import Availability, Capability, ManagerResponse, response
from .registry import CapabilityRegistry
from .routing import route
from .orchestration import orchestrate
from .security import is_data_only, require_data_result


DOMAIN_STATUSES = {"SUCCESS", "PARTIAL", "NO_DATA", "INVALID_REQUEST", "UNSUPPORTED", "DATA_QUALITY_BLOCKER"}
AGENT_ONLY_STATUSES = {"CLARIFICATION_REQUIRED", "INVALID_REQUEST", "UNSUPPORTED", "PROVIDER_UNAVAILABLE", "PROVIDER_ERROR"}


def validate_payload(capability, payload):
    if type(payload) is not dict or not is_data_only(payload):
        return "Request must be a data-only JSON object with string property names and finite values."
    try:
        # Validation only: never round-trip/coerce the delegated payload or decimals.
        json.dumps(payload, allow_nan=False)
    except (TypeError, ValueError, OverflowError, RecursionError):
        return "Request must contain JSON-serializable finite values."
    if capability == Capability.FINANCIAL_ANALYSIS:
        if "question" not in payload or set(payload) - {"question", "dataset", "parameters"}:
            return "Financial Analysis expects question and optional dataset/parameters."
        if not isinstance(payload["question"], str):
            return "Financial Analysis question must be text."
    # Domain validation, including question/parameter semantics and all anomaly
    # request properties, belongs to the existing selected implementation.
    return None


def wrap_analysis(info, result):
    delegated_status = result["agent_status"]
    tool = result["tool_result"]
    if delegated_status in ("ANSWERED", "TOOL_REJECTED"):
        if not isinstance(tool, dict) or tool.get("status") not in DOMAIN_STATUSES:
            raise ValueError("Financial Analysis returned an incompatible tool status.")
        status = tool["status"]
        errors = tool["errors"]
    elif delegated_status in AGENT_ONLY_STATUSES:
        status = delegated_status
        errors = result["errors"]
    else:
        raise ValueError("Financial Analysis returned an unknown agent status.")
    return response(info, status, result=result, delegated_status=delegated_status,
                    summary=result["explanation"]["text"],
                    warnings=tool["quality"]["warnings"] if tool else [], errors=errors,
                    clarification=result["clarification"])


def wrap_anomaly(info, result):
    status = result["status"]
    if status not in DOMAIN_STATUSES:
        raise ValueError("Anomaly screening returned an unknown status.")
    summary = f"Anomaly screening returned {status}."
    if result["result"] is not None:
        summary += (" CANDIDATE records are screening candidates requiring investigation."
                    " NOT_SELECTED is not a validity finding; NOT_ASSESSED records remain unassessed."
                    " See the preserved global/peer assessments, references and quality disclosures.")
    return response(info, status, result=result, delegated_status=status, summary=summary,
                    warnings=result["quality"]["warnings"], errors=result["errors"])


class FinancialManagerAgent:
    """One explicit facade. No domain arithmetic, DB access or model interpretation."""

    def __init__(self, *, financial_analysis=None, anomaly_detection=None):
        self._registry = CapabilityRegistry(financial_analysis, anomaly_detection)

    def list_capabilities(self):
        return self._registry.list_capabilities()

    def get_capability(self, capability):
        """Return metadata for an exact identifier, or None for an unknown identifier."""
        info = self._registry.get(capability)
        return info.to_dict() if info else None

    def plan(self, question):
        """Preview top-level routing without executing any capability."""
        return route(question, self._registry).to_dict()

    def ask(self, question):
        """Route and execute a bounded natural-language capability request."""
        return orchestrate(self, question)

    def execute(self, *, capability=None, request=None) -> ManagerResponse:
        info = self._registry.get(capability)
        if info is None:
            message = "Explicitly select one of the four registered capability identifiers."
            return response(None, "INVALID_REQUEST", selected=capability if type(capability) is str else None,
                            summary=message, errors=[{"code": "unknown_capability", "field": "capability", "message": message}])
        # Availability precedes payload validation: unavailable operations have no
        # invented request schema and cannot trigger any implementation.
        if info.status != Availability.AVAILABLE:
            return response(info, "CAPABILITY_UNAVAILABLE", summary=info.reason,
                            errors=[{"code": "capability_unavailable", "field": "capability", "message": info.reason}])
        invalid = validate_payload(info.identifier, request)
        if invalid:
            return response(info, "INVALID_REQUEST", summary=invalid,
                            errors=[{"code": "malformed_request", "field": "request", "message": invalid}])
        # Isolate caller-owned requests from trusted adapters. Expected validation
        # outcomes are returned by those adapters; unexpected failures propagate.
        result = self._registry.delegate(info.identifier, deepcopy(request))
        require_data_result(result)
        if info.identifier == Capability.FINANCIAL_ANALYSIS:
            return wrap_analysis(info, result)
        return wrap_anomaly(info, result)
