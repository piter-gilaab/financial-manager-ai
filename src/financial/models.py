"""Contract failures and JSON-safe envelopes (no financial float coercion)."""

from copy import deepcopy


class ContractError(Exception):
    def __init__(self, status, code, message, field=None):
        super().__init__(message)
        self.status = status
        self.error = {"code": code, "field": field, "message": message}


def invalid(field, message):
    raise ContractError("INVALID_REQUEST", "invalid_parameter", message, field)


def blocker(code, message):
    raise ContractError("DATA_QUALITY_BLOCKER", code, message)


ARITHMETIC = {
    "decimal_precision": 60,
    "exact_operations_trap_rounding": True,
    "derived_decimal_places": 6,
    "rounding": "ROUND_HALF_EVEN",
    "serialization": "fixed_point_decimal_strings",
}


def envelope(request):
    request = request if isinstance(request, dict) else {}
    # Never echo arbitrary caller objects into the serializable error envelope.
    def identity(key):
        value = request.get(key)
        return value if isinstance(value, str) else None

    return {
        "contract_version": "1.0", "query_name": identity("query_name"),
        "dataset": identity("dataset"), "status": None, "result": None,
        "currency": None, "records": None, "filter_diagnostics": [],
        "quality": {"warnings": [], "flags": [], "detail": "summary"},
        "errors": [], "metadata": {},
    }


def arithmetic_metadata():
    return deepcopy(ARITHMETIC)
