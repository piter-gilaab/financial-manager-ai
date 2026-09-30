"""Evidence-bearing currency metadata and immutable original monetary values."""

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
import re


class CurrencyStatus(str, Enum):
    UNKNOWN = "UNKNOWN"
    INFERRED = "INFERRED"
    CONFIRMED = "CONFIRMED"


def validate_code(code):
    """Lexical validation only; approved code membership is an offline policy."""
    if not isinstance(code, str) or re.fullmatch(r"[A-Z]{3}", code) is None:
        raise ValueError("Currency code must have three uppercase ASCII letters.")
    return code


@dataclass(frozen=True, slots=True)
class CurrencyMetadata:
    status: CurrencyStatus = CurrencyStatus.UNKNOWN
    code: str | None = None
    source: str | None = None

    def __post_init__(self):
        if not isinstance(self.status, CurrencyStatus):
            raise ValueError("Use a supported CurrencyStatus; MIXED is not a scalar currency.")
        if self.status == CurrencyStatus.UNKNOWN:
            if self.code is not None or self.source is not None:
                raise ValueError("UNKNOWN currency cannot carry an assigned code or evidence.")
        else:
            validate_code(self.code)
            if not isinstance(self.source, str) or not self.source.strip():
                raise ValueError("Known or inferred currency requires explicit source evidence.")

    def to_dict(self):
        return {"code": self.code, "status": self.status.value, "source": self.source}


@dataclass(frozen=True, slots=True)
class MonetaryValue:
    amount: Decimal
    currency: CurrencyMetadata

    def __post_init__(self):
        if not isinstance(self.amount, Decimal) or not self.amount.is_finite():
            raise ValueError("Original amount must be a finite Decimal, never a float.")
        if not isinstance(self.currency, CurrencyMetadata):
            raise ValueError("Original amount requires explicit currency metadata.")

    def to_dict(self):
        return {"amount": format(self.amount, "f"), "currency": self.currency.to_dict()}

UNKNOWN_DISCLOSURE = (
    "Currency denomination is unknown; values summarize source records and are not "
    "verified comparable monetary totals."
)


def query_currency(monetary):
    if not monetary:
        return None
    return CurrencyMetadata().to_dict() | {
        "basis": "unverified_source_denomination", "conversion_applied": False}
