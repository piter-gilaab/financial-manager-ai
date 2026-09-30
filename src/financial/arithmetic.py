"""Exact source decimals; one-rounding rational means/coverage percentages."""

from decimal import Context, Decimal, DecimalException, Inexact, Rounded, localcontext
import re

from .models import blocker


def decimal(token):
    if not isinstance(token, str) or re.fullmatch(r"-?(?:0|[1-9][0-9]*)\.[0-9]+", token) is None:
        blocker("invalid_decimal", "A source amount is not canonical decimal TEXT.")
    return Decimal(token)


def exact_context():
    # Independent of the process-global Decimal context, including traps/rounding.
    ctx = Context(prec=60)
    ctx.traps[Inexact] = ctx.traps[Rounded] = True
    return localcontext(ctx)


def exact_sum(values):
    if not values:
        return None
    try:
        with exact_context():
            total = +values[0]  # Check precision even for a single operand.
            for value in values[1:]:
                total += value
            return total
    except DecimalException:
        blocker("exact_arithmetic_limit", "Exact arithmetic exceeded precision 60; no subtotal returned.")


def rounded_ratio(numerator, denominator):
    """Round an exact integer rational once, to six places, half-even."""
    if denominator == 0:
        return None
    negative = (numerator < 0) != (denominator < 0)
    quotient, remainder = divmod(abs(numerator) * 1_000_000, abs(denominator))
    if remainder * 2 > abs(denominator) or (remainder * 2 == abs(denominator) and quotient % 2):
        quotient += 1
    whole, fraction = divmod(quotient, 1_000_000)
    return f"{'-' if negative else ''}{whole}.{fraction:06d}"


def percentage(used, candidates):
    return rounded_ratio(100 * used, candidates)


def statistics(tokens, requested):
    """Tokens arrive in source-row order; stable numeric sorting resolves ties."""
    values = [decimal(token) for token in tokens]
    result = {}
    total = exact_sum(values) if "sum" in requested or "mean" in requested else None
    ordered = sorted(zip(values, tokens), key=lambda pair: pair[0])
    for operation in requested:
        if operation == "count":
            result[operation] = len(tokens)
        elif not values:
            result[operation] = None
        elif operation == "sum":
            result[operation] = format(total, "f")
        elif operation == "mean":
            numerator, denominator = total.as_integer_ratio()
            result[operation] = rounded_ratio(numerator, denominator * len(values))
        elif operation in ("min", "max"):
            target = min(values) if operation == "min" else max(values)
            result[operation] = next(t for v, t in zip(values, tokens) if v == target)
        elif operation == "median":
            middle = len(ordered) // 2
            if len(ordered) % 2:
                result[operation] = ordered[middle][1]
            else:
                try:
                    with exact_context():
                        value = ordered[middle - 1][0] / 2 + ordered[middle][0] / 2
                    result[operation] = format(value, "f")
                except DecimalException:
                    blocker("exact_arithmetic_limit", "Exact median exceeded precision 60.")
        else:
            raise ValueError("Unvalidated statistic")
    return result
