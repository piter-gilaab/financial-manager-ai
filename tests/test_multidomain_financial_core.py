"""Phase 2 Financial Core behavior at the approved multi-domain seam."""

import unittest

from src.financial.multidomain import (
    CanonicalFinancialRecord,
    cash_by_period,
    cash_summary,
    obligation_aging,
    obligation_summary,
    overdue_obligation_summary,
)


def record(identifier, **values):
    defaults = {
        "canonical_record_id": identifier,
        "source_row_number": int(identifier[1:]),
        "source_sheet": None,
    }
    defaults.update(values)
    return CanonicalFinancialRecord(**defaults)


class MultiDomainFinancialCoreTests(unittest.TestCase):
    def test_obligation_summary_uses_exact_decimal_and_accounts_for_parse_failures(self):
        result = obligation_summary((
            record("r1", amount="0.1", amount_raw="0.1"),
            record("r2", amount="0.2", amount_raw="0.2"),
            record("r3", amount=None, amount_status="parsing_failed", amount_raw="oops"),
            record("r4", amount="-1.00", amount_raw="-1.00"),
        ))

        self.assertEqual(result["status"], "PARTIAL")
        self.assertEqual(result["result"]["measures"]["amount"], {
            "count": 3,
            "sum": "-0.70",
            "mean": "-0.233333",
            "median": "0.1",
            "min": "-1.00",
            "max": "0.2",
            "unit": "monetary",
            "coverage": {
                "candidates": 4, "used": 3, "excluded": 1,
                "exclusion_reasons": {"measure:amount:parsing_failed": 1},
                "percentage": "75.000000",
            },
        })

    def test_aging_boundaries_and_state_exclusions_are_frozen(self):
        records = (
            record("r1", amount="10", due_date="2026-11-01", settlement_status="OPEN"),
            record("r2", amount="1", due_date="2026-10-31", settlement_status="OPEN"),
            record("r3", amount="30", due_date="2026-10-02", settlement_status="OPEN"),
            record("r4", amount="31", due_date="2026-10-01", settlement_status="OPEN"),
            record("r5", amount="60", due_date="2026-09-02", settlement_status="OPEN"),
            record("r6", amount="61", due_date="2026-09-01", settlement_status="OPEN"),
            record("r7", amount="90", due_date="2026-08-03", settlement_status="OPEN"),
            record("r8", amount="91", due_date="2026-08-02", settlement_status="OPEN"),
            record("r9", amount="99", due_date="2026-01-01", settlement_status="SETTLED"),
            record("r10", amount="99", due_date="2026-01-01", settlement_status="CANCELLED"),
            record("r11", amount="0", due_date="2026-01-01", settlement_status="OPEN"),
        )

        result = obligation_aging(records, as_of_date="2026-11-01")

        self.assertEqual(
            [(item["bucket"], item["balance_sum"]) for item in result["result"]["buckets"]],
            [
                ("NOT_DUE", "10"),
                ("OVERDUE_1_30", "31"),
                ("OVERDUE_31_60", "91"),
                ("OVERDUE_61_90", "151"),
                ("OVERDUE_91_PLUS", "91"),
            ],
        )
        self.assertEqual(result["result"]["excluded"], {
            "cancelled": 1,
            "non_positive_open_balance": 1,
            "settled": 1,
        })
        self.assertTrue(all("coverage" in item for item in result["result"]["buckets"]))

    def test_overdue_requires_open_positive_balance_and_strictly_earlier_due_date(self):
        result = overdue_obligation_summary((
            record("r1", amount="5", due_date="2026-10-31", settlement_status="OPEN"),
            record("r2", amount="7", due_date="2026-11-01", settlement_status="OPEN"),
            record("r3", amount="11", due_date="2026-10-01", settlement_status="SETTLED"),
            record("r4", amount="-2", due_date="2026-10-01", settlement_status="OPEN"),
        ), as_of_date="2026-11-01")

        self.assertEqual(result["result"]["open_record_count"], 2)
        self.assertEqual(result["result"]["overdue_record_count"], 1)
        self.assertEqual(result["result"]["overdue_balance"]["sum"], "5")

    def test_cash_direction_is_explicit_and_net_is_core_owned(self):
        records = (
            record("r1", amount="100", transaction_date="2026-01-01", cash_direction="INFLOW"),
            record("r2", amount="40", transaction_date="2026-01-02", cash_direction="OUTFLOW"),
            record("r3", amount="10", transaction_date="2026-02-01", cash_direction="INFLOW"),
        )

        inflow = cash_summary(records, direction="INFLOW")
        outflow = cash_summary(records, direction="OUTFLOW")
        periods = cash_by_period(records, granularity="MONTH")

        self.assertEqual(inflow["result"]["measures"]["inflow"]["sum"], "110")
        self.assertEqual(outflow["result"]["measures"]["outflow"]["sum"], "40")
        self.assertEqual(
            [(g["key"]["value"], g["inflow_sum"], g["outflow_sum"], g["net_cash"])
             for g in periods["result"]["groups"]],
            [("2026-01", "100", "40", "60"), ("2026-02", "10", "0", "10")],
        )


if __name__ == "__main__":
    unittest.main()
