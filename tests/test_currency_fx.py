"""Currency evidence and FX lookup using explicit test fixtures only."""

from dataclasses import FrozenInstanceError, asdict
from datetime import date, datetime, timezone
from decimal import Decimal, localcontext
import json
import socket
import unittest
from unittest.mock import patch

from src.financial import FinancialCore
from src.financial.currency import CurrencyMetadata, CurrencyStatus, MonetaryValue
from src.financial.fx import FXLookupStatus, FXRate, FXRateRequest, LocalFXRateProvider, assess_fx_eligibility


DAY = date(2024, 1, 31)
CODES = frozenset({"USD", "BRL", "EUR"})  # Test-only approved code set, not source inference.


def quote():
    return FXRate("USD", "BRL", Decimal("4.123456789012345678901234567890"), DAY,
                  "test-fixture", "Explicit synthetic rate for tests only",
                  datetime(2024, 2, 1, tzinfo=timezone.utc), "reference")


def original(status=CurrencyStatus.CONFIRMED):
    metadata = CurrencyMetadata() if status == CurrencyStatus.UNKNOWN else CurrencyMetadata(status, "USD", "private-currency-evidence")
    return MonetaryValue(Decimal("-123.4500"), metadata)


class RecordingProvider:
    def __init__(self, rate=None):
        self.requests = []
        self.rate = rate

    def get_rate(self, request):
        self.requests.append(request)
        return self.rate


class CurrencyTests(unittest.TestCase):
    def test_confirmed_currency_requires_code_and_evidence(self):
        metadata = CurrencyMetadata(CurrencyStatus.CONFIRMED, "USD", "fixture authoritative evidence")
        self.assertEqual(metadata.to_dict(), {"code": "USD", "status": "CONFIRMED", "source": "fixture authoritative evidence"})
        with self.assertRaises(ValueError):
            CurrencyMetadata(CurrencyStatus.CONFIRMED, "USD")

    def test_unknown_cannot_be_assigned_a_code_or_source(self):
        self.assertEqual(CurrencyMetadata().to_dict(), {"code": None, "status": "UNKNOWN", "source": None})
        for kwargs in [{"code": "USD"}, {"source": "Canada"}]:
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                CurrencyMetadata(**kwargs)

    def test_inferred_is_distinct_and_evidence_bearing(self):
        inferred = CurrencyMetadata(CurrencyStatus.INFERRED, "BRL", "approved hypothetical interpretation")
        self.assertEqual(inferred.to_dict()["status"], "INFERRED")
        with self.assertRaises(ValueError):
            CurrencyMetadata(CurrencyStatus.INFERRED, "BRL")

    def test_mixed_cannot_label_a_scalar_amount(self):
        with self.assertRaises(ValueError):
            CurrencyMetadata("MIXED")

    def test_currency_codes_are_not_symbols_or_country_names(self):
        for code in ["$", "usd", "Canada", "US", None, 123]:
            with self.subTest(code=code), self.assertRaises(ValueError):
                CurrencyMetadata(CurrencyStatus.CONFIRMED, code, "fixture")

    def test_original_amount_is_exact_immutable_and_not_quantized(self):
        value = original()
        self.assertEqual(value.to_dict()["amount"], "-123.4500")
        with self.assertRaises(FrozenInstanceError):
            value.amount = Decimal("1.00")
        with self.assertRaises(FrozenInstanceError):
            value.currency.code = "BRL"

    def test_monetary_model_rejects_float_and_nonfinite(self):
        for value in [1.2, "1.20", Decimal("NaN"), Decimal("Infinity")]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                MonetaryValue(value, CurrencyMetadata())


class FXTests(unittest.TestCase):
    def lookup(self, value=None, target="BRL", day=DAY, provider=None, codes=CODES):
        return assess_fx_eligibility(value or original(), target, day,
                                     provider=provider or LocalFXRateProvider([quote()]), approved_codes=codes)

    def test_empty_local_provider_is_rate_unavailable(self):
        result = self.lookup(provider=LocalFXRateProvider())
        self.assertEqual(result.status, FXLookupStatus.RATE_UNAVAILABLE)
        self.assertFalse(result.to_dict()["conversion_applied"])

    def test_exact_local_fixture_lookup(self):
        result = self.lookup()
        self.assertEqual(result.status, FXLookupStatus.RATE_AVAILABLE)
        self.assertEqual(result.rate.rate, Decimal("4.123456789012345678901234567890"))
        self.assertEqual(result.rate.source, "test-fixture")
        self.assertEqual(result.rate.rate_date, DAY)

    def test_unknown_refuses_before_any_provider_call(self):
        provider = RecordingProvider(quote())
        result = self.lookup(value=original(CurrencyStatus.UNKNOWN), provider=provider)
        self.assertEqual(result.status, FXLookupStatus.SOURCE_CURRENCY_UNCONFIRMED)
        self.assertEqual(provider.requests, [])
        self.assertIsNone(result.to_dict()["converted_amount"])

    def test_inferred_currency_is_not_conversion_eligible(self):
        provider = RecordingProvider(quote())
        result = self.lookup(value=original(CurrencyStatus.INFERRED), provider=provider)
        self.assertEqual(result.status, FXLookupStatus.SOURCE_CURRENCY_UNCONFIRMED)
        self.assertEqual(provider.requests, [])

    def test_invalid_target_or_date_never_reaches_provider(self):
        for target, day in [("$", DAY), ("ZZZ", DAY), ("USD", DAY), ("BRL", "latest"), ("BRL", datetime(2024, 1, 31, tzinfo=timezone.utc)), (None, DAY)]:
            with self.subTest(target=target, day=day):
                provider = RecordingProvider()
                result = self.lookup(target=target, day=day, provider=provider)
                self.assertEqual(result.status, FXLookupStatus.INVALID_REQUEST)
                self.assertEqual(provider.requests, [])
                json.dumps(result.to_dict(), allow_nan=False)

    def test_code_shape_does_not_replace_local_approval(self):
        result = self.lookup(codes=frozenset({"BRL"}))
        self.assertEqual(result.status, FXLookupStatus.INVALID_REQUEST)
        with self.assertRaises(ValueError):
            self.lookup(codes="USDBRL")

    def test_no_latest_nearest_inverse_or_triangulated_rate(self):
        provider = LocalFXRateProvider([quote()])
        for query in [FXRateRequest("USD", "BRL", date(2024, 2, 1)),
                      FXRateRequest("BRL", "USD", DAY), FXRateRequest("USD", "EUR", DAY)]:
            self.assertIsNone(provider.get_rate(query))

    def test_rates_preserve_decimal_scale_and_provenance(self):
        with localcontext() as context:
            context.prec = 2
            serialized = quote().to_dict()
        self.assertEqual(serialized["rate"], "4.123456789012345678901234567890")
        self.assertEqual(serialized["rate_type"], "reference")
        self.assertEqual(serialized["imported_at"], "2024-02-01T00:00:00+00:00")
        self.assertIn("synthetic", serialized["provenance"])

    def test_rate_rejects_float_zero_negative_and_nonfinite(self):
        for rate in [1.2, Decimal("0"), Decimal("-1"), Decimal("NaN"), Decimal("Infinity")]:
            with self.subTest(rate=rate), self.assertRaises(ValueError):
                FXRate("USD", "BRL", rate, DAY, "test", "fixture")

    def test_rate_requires_pair_date_provenance_and_aware_timestamp(self):
        cases = [dict(provenance=""), dict(source=""), dict(rate_date="2024-01-31"),
                 dict(imported_at=datetime(2024, 1, 31)), dict(to_currency="USD")]
        base = dict(from_currency="USD", to_currency="BRL", rate=Decimal("1.00"), rate_date=DAY, source="test", provenance="fixture")
        for overrides in cases:
            with self.subTest(overrides=overrides), self.assertRaises(ValueError):
                FXRate(**(base | overrides))

    def test_duplicate_rates_fail_instead_of_selecting_arbitrarily(self):
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            LocalFXRateProvider([quote(), quote()])

    def test_provider_request_contains_only_public_pair_and_date(self):
        provider = RecordingProvider(quote())
        self.lookup(provider=provider)
        self.assertEqual(asdict(provider.requests[0]), {"from_currency": "USD", "to_currency": "BRL", "rate_date": DAY})
        self.assertNotIn("private-currency-evidence", repr(provider.requests))
        self.assertNotIn("123.45", repr(provider.requests))
        self.assertFalse(hasattr(provider.requests[0], "__dict__"))

    def test_provider_cannot_silently_substitute_a_different_pair_or_date(self):
        wrong = FXRate("USD", "BRL", Decimal("1.00"), date(2024, 2, 1), "test", "fixture")
        with self.assertRaisesRegex(ValueError, "violated"):
            self.lookup(provider=RecordingProvider(wrong))

    def test_lookup_preserves_original_and_never_performs_conversion(self):
        value = original()
        result = self.lookup(value=value)
        self.assertIs(result.original, value)
        self.assertEqual(value.amount, Decimal("-123.4500"))
        serialized = result.to_dict()
        self.assertEqual(serialized["original"]["amount"], "-123.4500")
        self.assertIsNone(serialized["converted_amount"])
        self.assertFalse(serialized["conversion_applied"])
        json.dumps(serialized, allow_nan=False)

    def test_offline_operation_requires_no_socket(self):
        with patch.object(socket, "socket", side_effect=AssertionError("Network forbidden")), \
             patch.object(socket, "create_connection", side_effect=AssertionError("Network forbidden")):
            self.assertEqual(self.lookup().status, FXLookupStatus.RATE_AVAILABLE)
            core = FinancialCore()
            response = core.query({"contract_version": "1.0", "query_name": "company_financials_sales_summary", "dataset": "company_financials"})
            self.assertEqual(response["status"], "SUCCESS")
            self.assertEqual(response["currency"], {"code": None, "status": "UNKNOWN", "source": None,
                             "basis": "unverified_source_denomination", "conversion_applied": False})


if __name__ == "__main__":
    unittest.main()
