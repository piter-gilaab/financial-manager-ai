"""Data-only application messages, not a sandbox for trusted Python adapters."""

from decimal import Decimal
from math import isfinite


def is_data_only(value, *, allow_decimal=False):
    """Accept plain containers/scalars without invoking user object protocols.

    Reject cycles, excessive nesting, live handles and custom container types.
    Decimal is allowed only in trusted result evidence, never cast to float.
    No strings are redacted or interpreted: source values remain authoritative.
    """
    ancestors = set()

    def visit(item, depth):
        if depth > 64:
            return False
        kind = type(item)
        if kind in (str, int, bool, type(None)):
            return True
        if kind is float:
            return isfinite(item)
        if allow_decimal and kind is Decimal:
            return item.is_finite()
        if kind not in (dict, list, tuple) or id(item) in ancestors:
            return False
        ancestors.add(id(item))
        try:
            if kind is dict:
                return all(type(key) is str and visit(child, depth + 1) for key, child in item.items())
            return all(visit(child, depth + 1) for child in item)
        finally:
            ancestors.remove(id(item))

    return visit(value, 0)


def require_data_result(value):
    if type(value) is not dict or not is_data_only(value, allow_decimal=True):
        # Do not include repr(value), a field value or the rejected object's type.
        raise ValueError("Delegated responses must contain data-only values.")
