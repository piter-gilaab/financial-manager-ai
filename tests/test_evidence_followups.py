"""Phase 10 bounded evidence-reference follow-ups through the session API."""

from dataclasses import replace
from datetime import datetime, timedelta, timezone
from copy import deepcopy
from hashlib import sha256
import unittest
from unittest.mock import patch

from src.manager import FinancialManagerAgent, FinancialManagerSession


class FakeClock:
    def __init__(self):
        self.current = datetime(2026, 10, 1, 12, 0, tzinfo=timezone.utc)

    def __call__(self):
        return self.current

    def advance(self, **values):
        self.current += timedelta(**values)


class ReferenceIds:
    def __init__(self):
        self.index = 0

    def __call__(self):
        self.index += 1
        return f"evidence-{self.index}"


class RecordingManager:
    def __init__(self):
        self.manager = FinancialManagerAgent()
        self.questions = []

    def ask(self, question):
        self.questions.append(question)
        return self.manager.ask(question)


class SequenceManager:
    def __init__(self, *results):
        self.results = list(results)
        self.questions = []

    def ask(self, question):
        self.questions.append(question)
        return deepcopy(self.results.pop(0))


def hex_digest(value):
    return sha256(value.encode()).hexdigest()


def anomaly_result(*, database_sha="database-a", source_sha="source-a", record_id=None):
    record_id = hex_digest("record-a") if record_id is None else record_id
    evidence = {
        "analysis_version": "1.0",
        "service": "financial_anomaly_detection",
        "status": "SUCCESS",
        "dataset": "company_financials",
        "measure": "profit",
        "result": {
            "references": [{
                "reference_id": "global", "peer_definition": [], "peer_values": {},
                "numeric_size": 40, "eligibility": "ELIGIBLE", "reason": None,
                "q1": "1", "q3": "2", "iqr": "1", "lower_fence": "-0.5",
                "upper_fence": "3.5",
            }],
            "items": [{
                "lineage": {
                    "record_id": record_id,
                    "run_id": "20261001T120000000000Z_abcdef12",
                    "source_id": "company_financials",
                    "source_row_number": 1,
                    "processed_row_number": 1,
                },
                "dataset": "company_financials",
                "measure": "profit",
                "observed_value": "10.00",
                "observed_raw": "10",
                "observed_status": "parsed",
                "peer_values": {},
                "assessments": {
                    "global": {"status": "CANDIDATE", "reason": None,
                               "reference_id": "global", "numeric_peer_size": 40,
                               "tail": "upper"},
                    "peer": {"status": "NOT_ASSESSED", "reason": "fixture",
                             "reference_id": None, "numeric_peer_size": None,
                             "tail": None},
                },
                "unavailable_dependencies": [],
                "quality_warning_indices": [0],
            }],
            "summary": {}, "comparison": {}, "measure_coverage": {},
            "dimension_coverage": {},
        },
        "currency": {"status": "UNKNOWN", "code": None},
        "records": {"total": 1, "used": 1, "excluded": 0},
        "filter_diagnostics": [],
        "quality": {"warnings": [{"code": "screening", "message": "Investigate."}],
                    "flags": [], "detail": "summary"},
        "errors": [],
        "metadata": {"snapshot": {
            "database_sha256": database_sha,
            "schema_sha256": hex_digest("schema"),
            "manifest_sha256": hex_digest("manifest"),
            "validation_sha256": hex_digest("validation"),
            "flags_sha256": hex_digest("flags"),
            "source_sha256": hex_digest(source_sha),
            "processed_sha256": hex_digest("processed"),
        }},
    }
    return {
        "execution_status": "SUCCESS",
        "results": [{
            "step_id": 1,
            "capability": "ANOMALY_DETECTION",
            "response": {"delegated_result": evidence},
        }],
    }


class EvidenceFollowupTests(unittest.TestCase):
    def test_malformed_stored_handle_member_fails_closed_on_read(self):
        session = FinancialManagerSession(
            manager=SequenceManager(anomaly_result()), clock=FakeClock(),
            session_id_factory=lambda: "session-a", reference_id_factory=ReferenceIds(),
        )
        session.new_request("Screen profit")
        context = session._state.active_context
        session._state = replace(
            session._state,
            active_context=replace(context, handles=(object(),)),
        )

        status = session.status()

        self.assertEqual(status["status"], "INCOMPATIBLE_STATE")
        self.assertIsNone(status["active_context"])

    def test_malformed_snapshot_and_lineage_metadata_never_enter_state(self):
        malformed = anomaly_result()
        evidence = malformed["results"][0]["response"]["delegated_result"]
        evidence["metadata"]["snapshot"]["schema_sha256"] = "not-a-digest"
        evidence["result"]["items"][0]["lineage"]["record_id"] = "x" * 10_000
        session = FinancialManagerSession(
            manager=SequenceManager(malformed), clock=FakeClock(),
            session_id_factory=lambda: "session-a", reference_id_factory=ReferenceIds(),
        )

        outcome = session.new_request("Screen profit")

        self.assertEqual(outcome["references"], [])
        self.assertIsNone(session.status()["active_context"])

    def test_unresolvable_candidate_reference_and_malformed_item_never_issue_handles(self):
        for mutation in ("missing_reference", "non_mapping_item"):
            with self.subTest(mutation=mutation):
                malformed = anomaly_result()
                evidence = malformed["results"][0]["response"]["delegated_result"]
                if mutation == "missing_reference":
                    evidence["result"]["references"] = []
                else:
                    evidence["result"]["items"].append(None)
                session = FinancialManagerSession(
                    manager=SequenceManager(malformed), clock=FakeClock(),
                    session_id_factory=lambda: "session-a", reference_id_factory=ReferenceIds(),
                )

                outcome = session.new_request("Screen profit")

                self.assertEqual(outcome["references"], [])
                self.assertIsNone(session.status()["active_context"])

    def test_malformed_nested_evidence_and_item_scope_never_issue_handles(self):
        mutations = {
            "metadata_container": lambda evidence: evidence.update(metadata=[]),
            "quality_container": lambda evidence: evidence.update(quality=[]),
            "warning_container": lambda evidence: evidence["quality"].update(warnings={}),
            "warning_indices": lambda evidence: evidence["result"]["items"][0].update(
                quality_warning_indices={}
            ),
            "item_dataset": lambda evidence: evidence["result"]["items"][0].update(
                dataset="receiver_general"
            ),
            "item_measure": lambda evidence: evidence["result"]["items"][0].update(
                measure="sales"
            ),
            "assessment_status": lambda evidence: evidence["result"]["items"][0][
                "assessments"
            ]["peer"].update(status="EXECUTE_TOOL"),
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name):
                malformed = anomaly_result()
                evidence = malformed["results"][0]["response"]["delegated_result"]
                mutate(evidence)
                session = FinancialManagerSession(
                    manager=SequenceManager(malformed), clock=FakeClock(),
                    session_id_factory=lambda: "session-a", reference_id_factory=ReferenceIds(),
                )

                outcome = session.new_request("Screen profit")

                self.assertEqual(outcome["references"], [])
                self.assertIsNone(session.status()["active_context"])

    def test_malformed_fresh_nested_evidence_returns_controlled_stale_reference(self):
        malformed = anomaly_result()
        malformed["results"][0]["response"]["delegated_result"]["metadata"] = []
        manager = SequenceManager(anomaly_result(), malformed)
        session = FinancialManagerSession(
            manager=manager, clock=FakeClock(), session_id_factory=lambda: "session-a",
            reference_id_factory=ReferenceIds(),
        )
        handle = session.new_request("Screen profit")["references"][0]["handle"]

        outcome = session.follow_up(reference=handle, intent="why_selected")

        self.assertEqual(outcome["status"], "STALE_REFERENCE")
        self.assertEqual(outcome["error"]["code"], "stale_reference")

    def test_anomaly_request_issues_bounded_opaque_candidate_handles(self):
        session = FinancialManagerSession(
            manager=FinancialManagerAgent(), clock=FakeClock(),
            session_id_factory=lambda: "session-a",
            reference_id_factory=ReferenceIds(),
        )

        outcome = session.new_request("Screen profit")

        self.assertEqual(outcome["status"], "PARTIAL")
        self.assertGreater(len(outcome["references"]), 0)
        self.assertLessEqual(len(outcome["references"]), 10)
        self.assertEqual(outcome["references"][0], {
            "handle": "evidence-1",
            "kind": "ANOMALY_RECORD",
        })
        inspected = session.status()["active_context"]
        self.assertEqual(inspected["kind"], "ANOMALY_EVIDENCE")
        self.assertEqual(inspected["reference_count"], len(outcome["references"]))
        self.assertNotIn("handles", inspected)
        self.assertNotIn(outcome["references"][0]["handle"], repr(inspected))
        for forbidden in ("observed_value", "assessments", "record_id", "upper_fence"):
            self.assertNotIn(forbidden, repr(inspected))

    def test_anomaly_followup_reexecutes_and_returns_fresh_authoritative_detail(self):
        manager = RecordingManager()
        session = FinancialManagerSession(
            manager=manager, clock=FakeClock(), session_id_factory=lambda: "session-a",
            reference_id_factory=ReferenceIds(),
        )
        first = session.new_request("Screen profit")
        handle = first["references"][0]["handle"]
        initial_evidence = first["result"]["results"][0]["response"]["delegated_result"]
        expected_item = deepcopy(next(
            item for item in initial_evidence["result"]["items"]
            if any(assessment["status"] == "CANDIDATE"
                   for assessment in item["assessments"].values())
        ))
        expected_references = {
            item["reference_id"]: deepcopy(item)
            for item in initial_evidence["result"]["references"]
        }
        expected_warnings = [
            deepcopy(initial_evidence["quality"]["warnings"][index])
            for index in expected_item["quality_warning_indices"]
        ]
        first["result"]["results"][0]["response"]["summary"] = "POISONED PRIOR EXPLANATION"

        followup = session.follow_up(reference=handle, intent="why_selected")

        self.assertEqual(manager.questions, ["Screen profit", "Screen profit"])
        self.assertEqual(followup["operation"], "follow_up")
        self.assertEqual(followup["status"], "SUCCESS")
        detail = followup["result"]
        self.assertEqual(detail["reference_type"], "ANOMALY_RECORD")
        self.assertEqual(detail["capability"], "ANOMALY_DETECTION")
        self.assertEqual(detail["dataset"], "company_financials")
        self.assertEqual(detail["measure"], "profit")
        self.assertEqual(detail["lineage"], expected_item["lineage"])
        self.assertEqual(detail["observed_value"], expected_item["observed_value"])
        self.assertEqual(detail["observed_raw"], expected_item["observed_raw"])
        self.assertEqual(detail["observed_status"], expected_item["observed_status"])
        self.assertEqual(detail["peer_values"], expected_item["peer_values"])
        for mode, assessment in expected_item["assessments"].items():
            self.assertEqual(detail["assessments"][mode]["assessment"], assessment)
            reference_id = assessment["reference_id"]
            expected_reference = (expected_references[reference_id]
                                  if reference_id is not None else None)
            self.assertEqual(detail["assessments"][mode]["reference"], expected_reference)
        self.assertEqual(detail["quality_warnings"], expected_warnings)
        self.assertNotIn("POISONED", repr(followup))
        self.assertNotIn("fraud", repr(followup).casefold())
        self.assertNotIn("misconduct", repr(followup).casefold())

    def test_answer_never_treats_evidence_context_as_a_clarification(self):
        manager = RecordingManager()
        session = FinancialManagerSession(
            manager=manager, clock=FakeClock(), session_id_factory=lambda: "session-a",
            reference_id_factory=ReferenceIds(),
        )
        session.new_request("Screen profit")

        outcome = session.answer("ANOMALY_DETECTION")

        self.assertEqual(outcome["status"], "NO_PENDING_CLARIFICATION")
        self.assertEqual(manager.questions, ["Screen profit"])

    def test_logically_equivalent_rebuilt_database_resolves_despite_byte_hash_change(self):
        manager = SequenceManager(
            anomaly_result(database_sha="first-bytes"),
            anomaly_result(database_sha="rebuilt-bytes"),
        )
        session = FinancialManagerSession(
            manager=manager, clock=FakeClock(), session_id_factory=lambda: "session-a",
            reference_id_factory=ReferenceIds(),
        )
        handle = session.new_request("Screen profit")["references"][0]["handle"]

        outcome = session.follow_up(reference=handle, intent="record_detail")

        self.assertEqual(outcome["status"], "SUCCESS")
        self.assertNotIn("database_sha256", outcome["result"]["snapshot"])

    def test_changed_logical_snapshot_returns_controlled_stale_reference(self):
        manager = SequenceManager(
            anomaly_result(source_sha="source-a"),
            anomaly_result(source_sha="source-b"),
        )
        session = FinancialManagerSession(
            manager=manager, clock=FakeClock(), session_id_factory=lambda: "session-a",
            reference_id_factory=ReferenceIds(),
        )
        handle = session.new_request("Screen profit")["references"][0]["handle"]

        outcome = session.follow_up(reference=handle, intent="why_selected")

        self.assertEqual(outcome["status"], "STALE_REFERENCE")
        self.assertEqual(outcome["error"]["code"], "stale_reference")
        self.assertIsNone(outcome["result"])

    def test_unavailable_capability_during_reexecution_is_a_stale_reference(self):
        manager = SequenceManager(
            anomaly_result(),
            {"execution_status": "CAPABILITY_UNAVAILABLE", "results": []},
        )
        session = FinancialManagerSession(
            manager=manager, clock=FakeClock(), session_id_factory=lambda: "session-a",
            reference_id_factory=ReferenceIds(),
        )
        handle = session.new_request("Screen profit")["references"][0]["handle"]

        outcome = session.follow_up(reference=handle, intent="why_selected")

        self.assertEqual(outcome["status"], "STALE_REFERENCE")
        self.assertEqual(manager.questions, ["Screen profit", "Screen profit"])

    def test_unknown_modified_and_cross_session_handles_are_rejected_without_execution(self):
        first_manager = SequenceManager(anomaly_result())
        first = FinancialManagerSession(
            manager=first_manager, clock=FakeClock(), session_id_factory=lambda: "session-a",
            reference_id_factory=ReferenceIds(),
        )
        handle = first.new_request("Screen profit")["references"][0]["handle"]
        second_manager = SequenceManager(anomaly_result())
        second = FinancialManagerSession(
            manager=second_manager, clock=FakeClock(), session_id_factory=lambda: "session-b",
            reference_id_factory=lambda: "other-handle",
        )
        second.new_request("Screen profit")

        for session, reference in ((first, handle + "-changed"),
                                   (first, "invented"),
                                   (second, handle)):
            with self.subTest(reference=reference):
                outcome = session.follow_up(reference=reference, intent="why_selected")
                self.assertEqual(outcome["status"], "UNKNOWN_REFERENCE")
        self.assertEqual(first_manager.questions, ["Screen profit"])
        self.assertEqual(second_manager.questions, ["Screen profit"])

    def test_expiry_and_reset_invalidate_handles_without_reexecution(self):
        for transition in ("expire", "reset"):
            with self.subTest(transition=transition):
                clock, manager = FakeClock(), SequenceManager(anomaly_result())
                session = FinancialManagerSession(
                    manager=manager, clock=clock, session_id_factory=lambda: "session-a",
                    reference_id_factory=ReferenceIds(),
                )
                handle = session.new_request("Screen profit")["references"][0]["handle"]
                if transition == "expire":
                    clock.advance(minutes=30)
                else:
                    session.reset()

                outcome = session.follow_up(reference=handle, intent="why_selected")

                expected = "SESSION_EXPIRED" if transition == "expire" else "NO_EVIDENCE_CONTEXT"
                self.assertEqual(outcome["status"], expected)
                self.assertEqual(manager.questions, ["Screen profit"])

    def test_absolute_expiry_invalidates_handle_without_reexecution(self):
        clock = FakeClock()
        manager = SequenceManager(*(anomaly_result() for _ in range(9)))
        session = FinancialManagerSession(
            manager=manager, clock=clock, session_id_factory=lambda: "session-a",
            reference_id_factory=ReferenceIds(),
        )
        handle = session.new_request("Screen profit")["references"][0]["handle"]
        for _ in range(8):
            clock.advance(minutes=29)
            self.assertEqual(
                session.follow_up(reference=handle, intent="why_selected")["status"],
                "SUCCESS",
            )
        clock.advance(minutes=8)

        outcome = session.follow_up(reference=handle, intent="why_selected")

        self.assertEqual(outcome["status"], "SESSION_EXPIRED")
        self.assertEqual(len(manager.questions), 9)

    def test_unsupported_intent_and_non_string_reference_never_execute(self):
        manager = SequenceManager(anomaly_result())
        session = FinancialManagerSession(
            manager=manager, clock=FakeClock(), session_id_factory=lambda: "session-a",
            reference_id_factory=ReferenceIds(),
        )
        handle = session.new_request("Screen profit")["references"][0]["handle"]

        unsupported = session.follow_up(reference=handle, intent="run SQL")
        malformed = session.follow_up(reference=object(), intent="why_selected")

        self.assertEqual(unsupported["status"], "UNSUPPORTED_FOLLOW_UP")
        self.assertEqual(malformed["status"], "UNKNOWN_REFERENCE")
        self.assertEqual(manager.questions, ["Screen profit"])

    def test_followup_is_offline_and_blocked_new_request_removes_reference_context(self):
        session = FinancialManagerSession(
            manager=FinancialManagerAgent(), clock=FakeClock(),
            session_id_factory=lambda: "session-a", reference_id_factory=ReferenceIds(),
        )
        with patch("socket.socket", side_effect=AssertionError("No network")), \
             patch("socket.create_connection", side_effect=AssertionError("No network")):
            first = session.new_request("Screen profit")
            handle = first["references"][0]["handle"]
            detail = session.follow_up(reference=handle, intent="why_selected")
            blocked = session.new_request("Forecast cash flow.")
            old = session.follow_up(reference=handle, intent="why_selected")

        self.assertEqual(detail["status"], "SUCCESS")
        self.assertEqual(blocked["status"], "CAPABILITY_UNAVAILABLE")
        self.assertEqual(old["status"], "NO_EVIDENCE_CONTEXT")


if __name__ == "__main__":
    unittest.main()
