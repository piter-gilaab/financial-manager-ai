from datetime import datetime, timezone
from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest

from src.onboarding.ingestion import SafeFileIngestor
from src.onboarding.canonical import CanonicalMapper
from src.onboarding.models import OnboardingError
from src.onboarding.decisions import SemanticDecisionService
from src.onboarding.preparation import (
    FindingLevel,
    PreparationEngine,
    preparation_digest,
    preparation_from_dict,
)
from src.onboarding.profiling import DeterministicProfiler
from src.onboarding.readiness import CapabilityDiscovery
from src.onboarding.registry import DatasetRegistry
from src.onboarding.semantics import SemanticMapper
from tests.onboarding_support import write_xlsx


class DeterministicPreparationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)

    def tearDown(self):
        self.temporary.cleanup()

    def _ingest(self, store: str, filename: str, content: bytes, *, hour: int):
        source = self.root / filename
        source.write_bytes(content)
        return SafeFileIngestor(
            self.root / store,
            clock=lambda: datetime(2026, 11, 24, hour, tzinfo=timezone.utc),
        ).ingest(source)

    def test_manifest_identity_depends_on_structural_source_not_runtime_metadata(self):
        content = b" Amount ,Date\n 0.10 ,2026-01-02\n"
        first = self._ingest("first", "first.csv", content, hour=10)
        second = self._ingest("second", "renamed.csv", content, hour=11)
        profiler = DeterministicProfiler()
        engine = PreparationEngine()

        prepared = engine.prepare(first, profiler.profile(first))
        replayed = engine.prepare(second, profiler.profile(second))

        self.assertEqual(prepared.preparation_version, "1.0")
        self.assertEqual(prepared.source_fingerprint, first.source_sha256)
        self.assertEqual(prepared.source_sheet, None)
        self.assertEqual(prepared.total_rows, 1)
        self.assertEqual(prepared.structurally_accepted_rows, 1)
        self.assertEqual(prepared.columns[0].source_name, " Amount ")
        self.assertEqual(prepared.columns[0].header_key, "amount")
        self.assertEqual(prepared.preparation_digest, replayed.preparation_digest)
        self.assertEqual(prepared.to_dict(), replayed.to_dict())
        rendered = str(prepared.to_dict())
        self.assertNotIn(first.ingestion_run_id, rendered)
        self.assertNotIn(first.source_filename, rendered)
        self.assertNotIn(" 0.10 ", rendered)

    def test_bom_delimiter_and_xlsx_extraction_are_recorded_without_source_loss(self):
        csv_dataset = self._ingest(
            "bom", "bom.csv",
            b"\xef\xbb\xbfAmount;Date\n10.50;2026-01-02\n", hour=10,
        )
        profiler = DeterministicProfiler()
        csv_preparation = PreparationEngine().prepare(
            csv_dataset, profiler.profile(csv_dataset),
        )
        csv_steps = {
            item.identifier for item in csv_preparation.performed_transformations
        }
        self.assertEqual(csv_dataset.encoding, "UTF-8-SIG")
        self.assertEqual(csv_dataset.delimiter, ";")
        self.assertTrue({
            "UTF8_DECODE", "UTF8_BOM_REMOVE_FOR_PARSE", "CSV_DELIMITER_SELECT",
        } <= csv_steps)

        source = write_xlsx(
            self.root / "safe.xlsx",
            sheets={"Ledger": [["Amount", "Date"], ["10.50", "2026-01-02"]]},
        )
        xlsx_dataset = SafeFileIngestor(
            self.root / "xlsx", clock=lambda: datetime(
                2026, 11, 24, 10, tzinfo=timezone.utc,
            ),
        ).ingest(source)
        xlsx_preparation = PreparationEngine().prepare(
            xlsx_dataset, profiler.profile(xlsx_dataset),
        )
        xlsx_steps = {
            item.identifier for item in xlsx_preparation.performed_transformations
        }
        self.assertEqual(xlsx_dataset.detected_format, "XLSX")
        self.assertEqual(xlsx_dataset.rows, (("10.50", "2026-01-02"),))
        self.assertIn("XLSX_DATA_CELL_EXTRACT", xlsx_steps)
        self.assertNotIn("CSV_DELIMITER_SELECT", xlsx_steps)

    def test_safe_preparation_reports_parses_failures_and_duplicate_candidates_without_mutation(self):
        content = (
            "Amount,Date,Note\n"
            " 0.1 ,2026-01-02,NA\n"
            "0.10,01/02/2026,\n"
            "10.50,not-date,value\n"
            "-2.5000,2026-02-03,same\n"
            "12345678901234567890.123456789,,same\n"
            "oops,2026-03-04,cmd\n"
            "10.50,not-date,value\n"
        ).encode()
        dataset = self._ingest("evidence", "evidence.csv", content, hour=10)
        before = dataset.rows

        prepared = PreparationEngine().prepare(
            dataset, DeterministicProfiler().profile(dataset),
        )

        amount = prepared.column("Amount")
        date = prepared.column("Date")
        note = prepared.column("Note")
        self.assertEqual(amount.decimal_parse_success, 6)
        self.assertEqual(amount.decimal_parse_failure, 1)
        self.assertEqual(amount.decimal_parse_failure_rows, (7,))
        self.assertEqual(date.date_parse_success, 3)
        self.assertEqual(date.date_parse_failure, 3)
        self.assertEqual(date.ambiguous_date_count, 1)
        self.assertEqual(date.ambiguous_date_rows, (3,))
        self.assertEqual(note.blank_count, 1)
        self.assertIn(amount.structural_confidence, {"HIGH", "MIXED", "NO_EVIDENCE"})
        self.assertEqual(prepared.exact_duplicate_candidate_count, 1)
        self.assertEqual(prepared.exact_duplicate_candidates[0].source_row_numbers, (4, 8))
        self.assertEqual(dataset.rows, before)

        performed = {item.identifier for item in prepared.performed_transformations}
        self.assertTrue({
            "UTF8_DECODE", "CSV_DELIMITER_SELECT", "HEADER_COMPARISON_KEY",
            "BLANK_CLASSIFY", "TRIM_FOR_PARSE", "PARSE_DECIMAL_EXACT",
            "PARSE_ISO_DATE", "PRESERVE_TEXT",
        } <= performed)
        self.assertTrue(all(
            item.automation_class == "SAFE_AUTOMATIC"
            and item.input_representation
            and item.output_representation
            and item.preconditions
            and item.failure_readiness_effect in {
                "NONE", "LIMITS_COVERAGE", "BLOCKS_OPERATION", "BLOCKS_DATASET",
            }
            for item in prepared.performed_transformations
        ))
        refused = {item.identifier for item in prepared.refused_transformations}
        self.assertTrue({
            "FINANCIAL_IMPUTATION", "ROW_DELETION", "DUPLICATE_MERGE",
            "OUTLIER_MODIFICATION", "SIGN_MUTATION", "CURRENCY_INFERENCE",
            "FX_CONVERSION", "CASH_DIRECTION_INFERENCE",
            "DEBIT_CREDIT_INTERPRETATION", "PROFIT_RECONSTRUCTION",
            "OUTSTANDING_BALANCE_INFERENCE", "SEMANTIC_CONFIRMATION",
            "DOMAIN_CONFIRMATION", "AMBIGUOUS_DATE_ORDER",
        } <= refused)
        ambiguous_refusal = next(
            item for item in prepared.refused_transformations
            if item.identifier == "AMBIGUOUS_DATE_ORDER"
        )
        self.assertEqual(ambiguous_refusal.automation_class, "SUGGEST_ONLY")
        rendered = str(prepared.to_dict())
        self.assertNotIn("currency_code", rendered)
        self.assertNotIn("approved_domain", rendered)

    def test_missing_zero_null_like_tokens_and_header_collisions_remain_distinct(self):
        content = (
            "A-B,A B,Amount\n"
            "x,y,\n"
            "x,y,0\n"
            "x,y,-1.25\n"
            "x,y,NA\n"
            "x,y,oops\n"
        ).encode()
        dataset = self._ingest("conservative", "conservative.csv", content, hour=10)
        prepared = PreparationEngine().prepare(
            dataset, DeterministicProfiler().profile(dataset),
        )

        self.assertTrue(prepared.column("A-B").header_collision)
        self.assertTrue(prepared.column("A B").header_collision)
        self.assertNotEqual(
            prepared.column("A-B").column_id, prepared.column("A B").column_id,
        )
        amount = prepared.column("Amount")
        self.assertEqual(amount.blank_count, 1)
        self.assertEqual(amount.nonblank_count, 4)
        self.assertEqual(amount.decimal_parse_success, 2)
        self.assertEqual(amount.decimal_parse_failure, 2)
        self.assertEqual(amount.null_like_token_count, 1)
        self.assertEqual(amount.null_like_token_rows, (5,))
        self.assertEqual(dataset.rows[0][2], "")
        self.assertEqual(dataset.rows[1][2], "0")
        self.assertEqual(dataset.rows[2][2], "-1.25")
        self.assertEqual(dataset.rows[3][2], "NA")
        self.assertEqual(dataset.rows[4][2], "oops")

    def test_quality_report_has_closed_levels_structural_evidence_and_no_readiness_state(self):
        content = (
            "A-B,A B,Amount,Date\n"
            "x,y,10.50,2026-01-02\n"
            "x,y,,01/02/2026\n"
            "x,y,NA,not-date\n"
            "x,y,10.50,2026-01-02\n"
        ).encode()
        first = self._ingest("quality-a", "quality.csv", content, hour=10)
        second = self._ingest("quality-b", "renamed.csv", content, hour=11)
        profiler = DeterministicProfiler()
        engine = PreparationEngine()
        first_profile = profiler.profile(first)
        second_profile = profiler.profile(second)

        report = engine.assess(engine.prepare(first, first_profile), first_profile)
        replay = engine.assess(engine.prepare(second, second_profile), second_profile)

        self.assertEqual({item.value for item in FindingLevel}, {
            "ERROR", "WARNING", "INFORMATION", "REQUIRES_CONFIRMATION",
        })
        self.assertEqual(report.quality_report_version, "1.0")
        self.assertEqual(report.quality_report_digest, replay.quality_report_digest)
        self.assertEqual(report.to_dict(), replay.to_dict())
        self.assertEqual(report.total_rows, 4)
        self.assertEqual(report.structurally_accepted_rows, 4)
        self.assertEqual(report.currency_state, "UNKNOWN")
        self.assertEqual(
            [item.to_dict() for item in report.performed_transformations],
            [item.to_dict() for item in engine.prepare(first, first_profile).performed_transformations],
        )
        codes = {finding.code for finding in report.findings}
        self.assertTrue({
            "STRUCTURAL_PROFILE_COMPLETE", "HEADER_KEY_COLLISION",
            "MISSING_VALUES_OBSERVED", "NULL_LIKE_TOKEN_PRESERVED",
            "DECIMAL_PARSE_FAILURE", "DATE_PARSE_FAILURE",
            "AMBIGUOUS_DATE_REQUIRES_CONFIRMATION",
            "EXACT_DUPLICATE_CANDIDATE",
        } <= codes)
        ambiguous = next(
            finding for finding in report.findings
            if finding.code == "AMBIGUOUS_DATE_REQUIRES_CONFIRMATION"
        )
        self.assertEqual(ambiguous.level, "REQUIRES_CONFIRMATION")
        self.assertEqual(ambiguous.readiness_effect, "BLOCKS_OPERATION")
        rendered = report.to_dict()
        self.assertNotIn("readiness_state", rendered)
        self.assertNotIn("capabilities", rendered)

    def test_key_duplicate_candidates_require_confirmed_invoice_identity(self):
        content = (
            "Invoice_ID,Amount,Currency\n"
            "INV-1,10.00,$\n"
            "INV-1,20.00,$\n"
            "INV-2,10.00,$\n"
        ).encode()
        dataset = self._ingest("keys", "keys.csv", content, hour=10)
        profile = DeterministicProfiler().profile(dataset)
        engine = PreparationEngine()
        prepared = engine.prepare(dataset, profile)
        mapping = SemanticMapper().suggest(profile)

        unconfirmed = engine.assess(prepared, profile, mapping)
        self.assertEqual(unconfirmed.key_duplicate_candidates, ())
        self.assertNotIn(
            "KEY_BASED_DUPLICATE_CANDIDATE",
            {finding.code for finding in unconfirmed.findings},
        )
        self.assertEqual(unconfirmed.currency_state, "UNKNOWN")

        confirmed = SemanticDecisionService().decide(
            mapping, column="Invoice_ID", decision="CONFIRM",
            evidence="Approved invoice export specification.",
        )
        report = engine.assess(prepared, profile, confirmed)

        self.assertEqual(len(report.key_duplicate_candidates), 1)
        candidate = report.key_duplicate_candidates[0]
        self.assertEqual(candidate.comparison, "KEY_ROLE:INVOICE_ID")
        self.assertEqual(candidate.comparison_version, "1.0")
        self.assertEqual(candidate.occurrence_count, 2)
        self.assertEqual(candidate.source_row_numbers, (2, 3))
        finding = next(
            item for item in report.findings
            if item.code == "KEY_BASED_DUPLICATE_CANDIDATE"
        )
        self.assertEqual(finding.level, "WARNING")
        self.assertEqual(finding.readiness_effect, "NONE")
        self.assertEqual(prepared.total_rows, 3)
        self.assertEqual(report.total_rows, 3)

    def test_quality_is_validated_input_but_never_an_alternative_readiness_authority(self):
        dataset = self._ingest(
            "readiness-boundary", "readiness.csv",
            b"Invoice_ID,Amount\nINV-1,10\nINV-1,20\n", hour=10,
        )
        profile = DeterministicProfiler().profile(dataset)
        engine = PreparationEngine()
        preparation = engine.prepare(dataset, profile)
        mapping = SemanticMapper().suggest(profile)
        quality = engine.assess(preparation, profile, mapping)
        discovery = CapabilityDiscovery()

        without_quality = discovery.evaluate(profile, mapping).to_dict()
        readiness = discovery.evaluate(profile, mapping, quality)
        with_quality = readiness.to_dict()
        self.assertEqual(with_quality, without_quality)
        contextual_quality = engine.assess(
            preparation, profile, mapping, readiness_report=readiness,
        )
        self.assertIn(
            "CAPABILITY:FINANCIAL_ANALYSIS:BLOCKED",
            contextual_quality.readiness_references,
        )

        changed = SemanticDecisionService().decide(
            mapping, column="Invoice_ID", decision="CONFIRM", evidence="owner",
        )
        with self.assertRaises(OnboardingError) as raised:
            discovery.evaluate(profile, changed, quality)
        self.assertEqual(raised.exception.code, "artifact_mismatch")
        with self.assertRaises(OnboardingError) as raised:
            engine.assess(
                preparation, profile, changed, readiness_report=readiness,
            )
        self.assertEqual(raised.exception.code, "preparation_artifact_mismatch")

    def test_preparation_and_quality_artifacts_are_content_addressed_and_fail_closed(self):
        dataset = self._ingest(
            "artifacts", "artifacts.csv",
            b"Amount,Date\n10.50,2026-01-02\n,01/02/2026\n", hour=10,
        )
        profile = DeterministicProfiler().profile(dataset)
        engine = PreparationEngine()
        prepared = engine.prepare(dataset, profile)
        report = engine.assess(prepared, profile)
        registry = DatasetRegistry(self.root / "artifacts")

        preparation_path = registry.save_preparation(prepared)
        quality_path = registry.save_quality(report)

        self.assertEqual(
            registry.load_preparation(dataset.dataset_id, prepared.preparation_digest),
            prepared,
        )
        self.assertEqual(
            registry.load_quality(dataset.dataset_id, report.quality_report_digest),
            report,
        )
        self.assertEqual(
            preparation_path.name, f"{prepared.preparation_digest}.json",
        )
        self.assertEqual(quality_path.name, f"{report.quality_report_digest}.json")
        self.assertNotIn("10.50", preparation_path.read_text(encoding="utf-8"))

        payload = json.loads(preparation_path.read_text(encoding="utf-8"))
        payload["total_rows"] = 99
        preparation_path.write_text(json.dumps(payload), encoding="utf-8")
        with self.assertRaises(OnboardingError) as raised:
            registry.load_preparation(dataset.dataset_id, prepared.preparation_digest)
        self.assertEqual(raised.exception.code, "preparation_digest_mismatch")

        with self.assertRaises(OnboardingError) as raised:
            registry.save_preparation(replace(prepared, dataset_id="../../escape"))
        self.assertEqual(raised.exception.code, "invalid_dataset_id")

        unsupported = prepared.to_dict()
        unsupported["performed_transformations"][0]["identifier"] = "EXECUTE_SQL"
        unsupported["preparation_digest"] = preparation_digest(unsupported)
        with self.assertRaises(OnboardingError) as raised:
            preparation_from_dict(unsupported)
        self.assertEqual(raised.exception.code, "unsupported_transformation")

        invalid_refusal = prepared.to_dict()
        refusal = next(
            item for item in invalid_refusal["refused_transformations"]
            if item["identifier"] == "FINANCIAL_IMPUTATION"
        )
        refusal["automation_class"] = "SUGGEST_ONLY"
        invalid_refusal["preparation_digest"] = preparation_digest(invalid_refusal)
        with self.assertRaises(OnboardingError) as raised:
            preparation_from_dict(invalid_refusal)
        self.assertEqual(raised.exception.code, "preparation_corrupt")

    def test_prepared_decimal_view_is_exact_and_never_imputes_or_changes_sign(self):
        dataset = self._ingest(
            "decimal", "decimal.csv",
            (
                "Date,Sales\n"
                "2026-01-01,0.1\n"
                "2026-01-02,0.10\n"
                "2026-01-03,10.50\n"
                "2026-01-04,-2.5000\n"
                "2026-01-05,12345678901234567890.123456789\n"
                "2026-01-06,\n"
                "2026-01-07,malformed\n"
            ).encode(),
            hour=10,
        )
        profile = DeterministicProfiler().profile(dataset)
        preparation = PreparationEngine().prepare(dataset, profile)
        decisions = SemanticDecisionService()
        mapping = decisions.approve_domain(
            SemanticMapper().suggest(profile), domain="SALES_RECORD", evidence="owner",
        )
        mapping = decisions.decide(
            mapping, column="Date", decision="CONFIRM", evidence="owner",
        )
        mapping = decisions.decide(
            mapping, column="Sales", decision="CORRECT", role="SALES",
            evidence="owner",
        )
        spec = CanonicalMapper().build_spec(
            profile, mapping, preparation=preparation,
        )
        records = CanonicalMapper().map_records_with_status(dataset, spec)
        values = [item["canonical_fields"]["SALES"] for item in records]

        self.assertEqual(
            [item["normalized_value"] for item in values[:5]],
            ["0.1", "0.10", "10.50", "-2.5000", "12345678901234567890.123456789"],
        )
        self.assertEqual(values[5]["status"], "source_missing")
        self.assertIsNone(values[5]["normalized_value"])
        self.assertEqual(values[6]["status"], "parsing_failed")
        self.assertIsNone(values[6]["normalized_value"])
        failure_steps = {
            item["id"]: item["status"] for item in values[6]["transformations"]
        }
        self.assertEqual(failure_steps["TRIM_FOR_PARSE"], "APPLIED")
        self.assertEqual(failure_steps["PARSE_DECIMAL_EXACT"], "FAILED")
        self.assertEqual(failure_steps["CANONICAL_ROLE_BIND"], "NOT_APPLIED")
        self.assertNotEqual(values[5]["normalized_value"], "0")
        self.assertNotEqual(values[6]["normalized_value"], "0")

    def test_duplicate_and_failure_evidence_is_bounded_without_changing_rows(self):
        rows = "".join(f"same,{index % 3}\n" for index in range(200))
        dataset = self._ingest(
            "bounds", "bounds.csv", f"Text,Value\n{rows}".encode(), hour=10,
        )
        engine = PreparationEngine(
            max_failure_row_references=3,
            max_duplicate_groups=2,
            max_duplicate_row_references=4,
        )
        prepared = engine.prepare(dataset, DeterministicProfiler().profile(dataset))

        self.assertLessEqual(len(prepared.exact_duplicate_candidates), 2)
        self.assertTrue(prepared.duplicate_groups_truncated)
        self.assertTrue(all(
            len(item.source_row_numbers) <= 4
            for item in prepared.exact_duplicate_candidates
        ))
        self.assertEqual(prepared.total_rows, 200)
        self.assertEqual(len(dataset.rows), 200)


if __name__ == "__main__":
    unittest.main()
