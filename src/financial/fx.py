"""Offline exact-date FX lookup and eligibility only. No conversion or HTTP client."""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from types import MappingProxyType
from typing import Protocol

from .currency import CurrencyStatus, MonetaryValue, validate_code


@dataclass(frozen=True, slots=True)
class FXRateRequest:
    """The entire provider request: public pair/date, no monetary amount or identity."""

    from_currency: str
    to_currency: str
    rate_date: date

    def __post_init__(self):
        validate_code(self.from_currency)
        validate_code(self.to_currency)
        if self.from_currency == self.to_currency:
            raise ValueError("FX lookup requires two distinct currencies.")
        if type(self.rate_date) is not date:
            raise ValueError("An exact rate date is required; timestamps/latest are not accepted.")


@dataclass(frozen=True, slots=True)
class FXRate:
    """Quote convention: units of target currency per one unit of source currency."""

    from_currency: str
    to_currency: str
    rate: Decimal
    rate_date: date
    source: str
    provenance: str
    imported_at: datetime | None = None
    rate_type: str | None = None

    def __post_init__(self):
        FXRateRequest(self.from_currency, self.to_currency, self.rate_date)
        if not isinstance(self.rate, Decimal) or not self.rate.is_finite() or self.rate <= 0:
            raise ValueError("Rate must be a positive finite Decimal, never a float.")
        if any(not isinstance(value, str) or not value.strip() for value in (self.source, self.provenance)):
            raise ValueError("A rate requires source and provenance.")
        if self.imported_at is not None and (not isinstance(self.imported_at, datetime) or self.imported_at.utcoffset() is None):
            raise ValueError("Import timestamp must be timezone-aware.")
        if self.rate_type is not None and (not isinstance(self.rate_type, str) or not self.rate_type.strip()):
            raise ValueError("Rate type must be explicit nonempty text when provided.")

    @property
    def request(self):
        return FXRateRequest(self.from_currency, self.to_currency, self.rate_date)

    def to_dict(self):
        return {"from_currency": self.from_currency, "to_currency": self.to_currency,
                "rate": format(self.rate, "f"), "rate_date": self.rate_date.isoformat(),
                "source": self.source, "provenance": self.provenance,
                "imported_at": self.imported_at.isoformat() if self.imported_at else None,
                "rate_type": self.rate_type}


class FXRateProvider(Protocol):
    """A future adapter can retrieve public rates without receiving sensitive data."""

    def get_rate(self, request: FXRateRequest) -> FXRate | None:
        """Return the exact pair/date or None. No latest, inversion or fallback."""
        ...


class LocalFXRateProvider:
    """Explicitly supplied approved rates; empty by default; never performs I/O."""

    def __init__(self, rates=()):
        index = {}
        for rate in rates:
            if not isinstance(rate, FXRate):
                raise ValueError("Local rates must be validated FXRate objects.")
            if rate.request in index:
                raise ValueError("Duplicate pair/date: select one approved rate before lookup.")
            index[rate.request] = rate
        self._rates = MappingProxyType(index)

    def get_rate(self, request: FXRateRequest) -> FXRate | None:
        if not isinstance(request, FXRateRequest):
            raise ValueError("Provider accepts only a public FXRateRequest.")
        return self._rates.get(request)


class FXLookupStatus(str, Enum):
    SOURCE_CURRENCY_UNCONFIRMED = "SOURCE_CURRENCY_UNCONFIRMED"
    INVALID_REQUEST = "INVALID_REQUEST"
    RATE_UNAVAILABLE = "RATE_UNAVAILABLE"
    RATE_AVAILABLE = "RATE_AVAILABLE"


@dataclass(frozen=True, slots=True)
class FXEligibility:
    status: FXLookupStatus
    original: MonetaryValue
    target_currency: str | None
    requested_date: date | None
    rate: FXRate | None = None
    reason: str | None = None

    def to_dict(self):
        return {"status": self.status.value, "original": self.original.to_dict(),
                "target_currency": self.target_currency,
                "requested_date": self.requested_date.isoformat() if self.requested_date else None,
                "rate": self.rate.to_dict() if self.rate else None,
                "converted_amount": None, "conversion_applied": False, "reason": self.reason}


def assess_fx_eligibility(original, target_currency, rate_date, *, provider: FXRateProvider,
                          approved_codes: frozenset[str]):
    """Check eligibility using locally approved codes; never multiply or send amounts.

    This is an internal typed interface, separate from the 17 analytical requests.
    RATE_AVAILABLE means a future approved conversion could use this quote, not
    that conversion has been authorized or performed.
    """
    if not isinstance(original, MonetaryValue):
        raise TypeError("Expected an original MonetaryValue.")
    if not isinstance(approved_codes, frozenset):
        raise ValueError("Approved currency codes must be an immutable, explicitly configured set.")
    for code in approved_codes:
        validate_code(code)
    target = target_currency if isinstance(target_currency, str) else None
    requested_date = rate_date if type(rate_date) is date else None

    def result(status, reason=None, rate=None):
        return FXEligibility(status, original, target, requested_date, rate, reason)

    # Fail closed before consulting the provider, including for INFERRED currency.
    if original.currency.status != CurrencyStatus.CONFIRMED:
        return result(FXLookupStatus.SOURCE_CURRENCY_UNCONFIRMED, "Original denomination must be confirmed; no provider was called.")
    try:
        request = FXRateRequest(original.currency.code, target_currency, rate_date)
    except ValueError as error:
        return result(FXLookupStatus.INVALID_REQUEST, str(error))
    # A syntax check does not certify an ISO code or authorize a currency pair.
    if request.from_currency not in approved_codes or request.to_currency not in approved_codes:
        return result(FXLookupStatus.INVALID_REQUEST, "Currency pair is not in the locally approved code set.")
    rate = provider.get_rate(request)
    if rate is None:
        return result(FXLookupStatus.RATE_UNAVAILABLE, "No approved exact-date local rate; no network fallback.")
    if not isinstance(rate, FXRate) or rate.request != request:
        raise ValueError("FX provider violated the exact pair/date contract.")
    return result(FXLookupStatus.RATE_AVAILABLE, rate=rate)
