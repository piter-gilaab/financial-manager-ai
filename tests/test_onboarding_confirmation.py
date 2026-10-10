from datetime import datetime, timezone
import unittest

from src.onboarding.decisions import SemanticDecisionService
from src.onboarding.models import OnboardingError
from src.onboarding.profiling import DeterministicProfiler
from src.onboarding.semantics import SemanticMapper


FIXED_TIME = datetime(2026, 10, 3, 15, 30, tzinfo=timezone.utc)


class SemanticConfirmationTests(unittest.TestCase):
    def setUp(self):
        self.service = SemanticDecisionService(clock=lambda: FIXED_TIME)
        self.profiler = DeterministicProfiler()

    def _mapping(self, columns, rows):
        profile = self.profiler.profile_from_rows(
            dataset_id="ds_fixture", source_sha256="a" * 64,
            columns=tuple(columns), rows=tuple(tuple(row) for row in rows),
        )
        return SemanticMapper().suggest(profile)

    def test_user_confirms_suggestion_as_new_immutable_mapping_version(self):
        original = self._mapping(("Sales",), (("10.00",),))

        updated = self.service.decide(
            original, column="Sales", decision="CONFIRM",
            evidence="User confirms this source field is the sales measure.",
        )

        self.assertEqual(original.mapping_version, 1)
        self.assertEqual(original.proposal("Sales").status, "SUGGESTED")
        self.assertEqual(updated.mapping_version, 2)
        self.assertEqual(updated.proposal("Sales").status, "CONFIRMED")
        self.assertEqual(updated.proposal("Sales").authority_source, "USER")
        self.assertNotEqual(updated.mapping_digest, original.mapping_digest)
        decision = updated.decisions[-1]
        self.assertEqual(decision["decision"], "CONFIRM")
        self.assertEqual(decision["timestamp"], "2026-10-03T15:30:00Z")
        self.assertEqual(decision["previous_proposal"]["status"], "SUGGESTED")

    def test_unknown_column_can_be_corrected_manually_and_rejected_without_approval(self):
        original = self._mapping(("mystery",), (("office",),))
        corrected = self.service.decide(
            original, column="mystery", decision="CORRECT", role="CATEGORY",
            evidence="The data owner identifies this as the reporting category.",
        )
        rejected = self.service.decide(
            corrected, column="mystery", decision="REJECT",
            evidence="The data owner withdraws this mapping.",
        )

        self.assertEqual(corrected.proposal("mystery").status, "CONFIRMED")
        self.assertEqual(corrected.proposal("mystery").proposed_role, "CATEGORY")
        self.assertEqual(rejected.proposal("mystery").status, "REJECTED")
        self.assertIsNone(rejected.proposal("mystery").proposed_role)
        self.assertEqual(rejected.mapping_version, 3)
        self.assertEqual(len(rejected.decisions), 2)

    def test_empty_evidence_and_invalid_role_fail_closed(self):
        mapping = self._mapping(("mystery",), (("x",),))
        for kwargs, code in (
            ({"column": "mystery", "decision": "CORRECT", "role": "CATEGORY", "evidence": ""},
             "decision_evidence_required"),
            ({"column": "mystery", "decision": "CORRECT", "role": "RUN_SQL", "evidence": "owner"},
             "invalid_semantic_role"),
            ({"column": "missing", "decision": "REJECT", "evidence": "owner"},
             "column_not_found"),
        ):
            with self.subTest(code=code):
                with self.assertRaises(OnboardingError) as raised:
                    self.service.decide(mapping, **kwargs)
                self.assertEqual(raised.exception.code, code)

    def test_debit_credit_requires_explicit_closed_value_meaning(self):
        mapping = self._mapping(("dr_cr",), (("D",), ("C",)))
        with self.assertRaises(OnboardingError) as raised:
            self.service.decide(
                mapping, column="dr_cr", decision="CONFIRM",
                evidence="Owner confirms the indicator.",
            )
        self.assertEqual(raised.exception.code, "critical_value_mapping_required")

        with self.assertRaises(OnboardingError) as raised:
            self.service.decide(
                mapping, column="dr_cr", decision="CONFIRM",
                evidence="Owner supplies only one meaning.", value_mapping={"D": "DEBIT"},
            )
        self.assertEqual(raised.exception.code, "incomplete_value_mapping")

        confirmed = self.service.decide(
            mapping, column="dr_cr", decision="CONFIRM",
            evidence="Owner confirms the source convention.",
            value_mapping={"D": "DEBIT", "C": "CREDIT"},
        )
        self.assertEqual(confirmed.proposal("dr_cr").status, "CONFIRMED")
        self.assertEqual(confirmed.decisions[-1]["value_mapping"], {"C": "CREDIT", "D": "DEBIT"})

    def test_currency_role_does_not_assign_currency_without_explicit_iso_mapping(self):
        mapping = self._mapping(("currency",), (("USD",),))
        role_only = self.service.decide(
            mapping, column="currency", decision="CONFIRM",
            evidence="Owner confirms that this column stores currency codes.",
        )
        self.assertEqual(role_only.currency_state, "UNKNOWN")
        self.assertIsNone(role_only.confirmed_currency)

        verified = self.service.decide(
            role_only, column="currency", decision="CONFIRM",
            evidence="Data owner verifies the ISO denomination.",
            value_mapping={"USD": "USD"},
        )
        self.assertEqual(verified.currency_state, "CONFIRMED")
        self.assertEqual(verified.confirmed_currency, "USD")

        with self.assertRaises(OnboardingError) as raised:
            self.service.decide(
                mapping, column="currency", decision="CONFIRM", evidence="symbol only",
                value_mapping={"$": "USD"},
            )
        self.assertEqual(raised.exception.code, "invalid_currency_evidence")

        multiple = self._mapping(("currency",), (("USD",), ("EUR",)))
        with self.assertRaises(OnboardingError) as raised:
            self.service.decide(
                multiple, column="currency", decision="CONFIRM", evidence="partial evidence",
                value_mapping={"USD": "USD"},
            )
        self.assertEqual(raised.exception.code, "incomplete_value_mapping")

    def test_ambiguous_date_requires_explicit_format_contract(self):
        mapping = self._mapping(("Date", "Sales"), (("01/02/2026", "10"),))
        with self.assertRaises(OnboardingError) as raised:
            self.service.decide(mapping, column="Date", decision="CONFIRM", evidence="owner")
        self.assertEqual(raised.exception.code, "date_format_required")

        confirmed = self.service.decide(
            mapping, column="Date", decision="CONFIRM", evidence="owner",
            date_format="DD/MM/YYYY",
        )
        self.assertEqual(confirmed.proposal("Date").approved_format, "DD/MM/YYYY")
        self.assertEqual(confirmed.decisions[-1]["date_format"], "DD/MM/YYYY")

    def test_domain_approval_and_required_roles_control_semantic_state(self):
        mapping = self._mapping(
            ("Date", "Sales"), (("2026-01-01", "10.00"),),
        )
        mapping = self.service.approve_domain(
            mapping, domain="SALES_RECORD",
            evidence="Owner identifies each row as a sales record.",
        )
        self.assertEqual(mapping.status, "NEEDS_CONFIRMATION")
        mapping = self.service.decide(mapping, column="Date", decision="CONFIRM", evidence="owner")
        mapping = self.service.decide(mapping, column="Sales", decision="CONFIRM", evidence="owner")
        self.assertEqual(mapping.status, "SEMANTICALLY_APPROVED")
        self.assertEqual(mapping.approved_domain, "SALES_RECORD")

    def test_revising_confirmation_invalidates_previous_semantic_approval(self):
        mapping = self._mapping(("Date", "Sales"), (("2026-01-01", "10.00"),))
        mapping = self.service.approve_domain(mapping, domain="SALES_RECORD", evidence="owner")
        mapping = self.service.decide(mapping, column="Date", decision="CONFIRM", evidence="owner")
        mapping = self.service.decide(mapping, column="Sales", decision="CONFIRM", evidence="owner")
        self.assertEqual(mapping.status, "SEMANTICALLY_APPROVED")

        revised = self.service.decide(mapping, column="Sales", decision="REJECT", evidence="correction")

        self.assertEqual(revised.status, "NEEDS_CONFIRMATION")
        self.assertEqual(revised.mapping_version, mapping.mapping_version + 1)
        self.assertEqual(mapping.proposal("Sales").status, "CONFIRMED")

    def test_user_can_stop_or_reject_onboarding(self):
        mapping = self._mapping(("mystery",), (("x",),))
        blocked = self.service.stop(mapping, reject=False, evidence="User cancelled for now.")
        rejected = self.service.stop(mapping, reject=True, evidence="User rejects the source.")
        self.assertEqual(blocked.status, "BLOCKED")
        self.assertEqual(rejected.status, "REJECTED")
        self.assertEqual(blocked.decisions[-1]["decision"], "STOP")
        self.assertEqual(rejected.decisions[-1]["decision"], "REJECT_DATASET")


if __name__ == "__main__":
    unittest.main()
