"""Deterministic, source-preserving structural preparation and quality evidence."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, replace
from enum import Enum
import hashlib
import json
import re
import unicodedata
from typing import Any

from .models import IngestedDataset, IngestionLimits, OnboardingError
from .profiling import DatasetProfile, _decimal_value, _iso_date


PREPARATION_VERSION = "1.0"
QUALITY_REPORT_VERSION = "1.0"
_AMBIGUOUS_DATE = re.compile(r"^\d{1,2}/\d{1,2}/\d{4}$")
_NULL_LIKE = frozenset({"na", "n/a", "null", "none"})
_CURRENCY_STATES = frozenset({"UNKNOWN", "CONFIRMED", "CONFIRMED_MULTIPLE"})
_REFUSED_IDENTIFIERS = frozenset({
    "NON_UTF8_ENCODING_GUESS", "FINANCIAL_IMPUTATION", "ROW_DELETION",
    "DUPLICATE_MERGE", "OUTLIER_MODIFICATION", "SIGN_MUTATION",
    "CURRENCY_INFERENCE", "FX_CONVERSION", "CASH_DIRECTION_INFERENCE",
    "DEBIT_CREDIT_INTERPRETATION", "PROFIT_RECONSTRUCTION",
    "OUTSTANDING_BALANCE_INFERENCE", "SEMANTIC_CONFIRMATION",
    "DOMAIN_CONFIRMATION", "AMBIGUOUS_DATE_ORDER", "NULL_TOKEN_INTERPRETATION",
})
_REFUSAL_CLASSES = {
    identifier: (
        "SUGGEST_ONLY"
        if identifier in {"AMBIGUOUS_DATE_ORDER", "NULL_TOKEN_INTERPRETATION"}
        else "PROHIBITED_AUTOMATION"
    )
    for identifier in _REFUSED_IDENTIFIERS
}
_FINDING_CONTRACTS = {
    "STRUCTURAL_PROFILE_COMPLETE": ("INFORMATION", "NONE"),
    "HEADER_KEY_COLLISION": ("WARNING", "NONE"),
    "MISSING_VALUES_OBSERVED": ("WARNING", "LIMITS_COVERAGE"),
    "NULL_LIKE_TOKEN_PRESERVED": ("WARNING", "NONE"),
    "DECIMAL_PARSE_FAILURE": ("WARNING", "LIMITS_COVERAGE"),
    "DATE_PARSE_FAILURE": ("WARNING", "LIMITS_COVERAGE"),
    "AMBIGUOUS_DATE_REQUIRES_CONFIRMATION": (
        "REQUIRES_CONFIRMATION", "BLOCKS_OPERATION",
    ),
    "EXACT_DUPLICATE_CANDIDATE": ("WARNING", "NONE"),
    "KEY_BASED_DUPLICATE_CANDIDATE": ("WARNING", "NONE"),
}


class FindingLevel(str, Enum):
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFORMATION = "INFORMATION"
    REQUIRES_CONFIRMATION = "REQUIRES_CONFIRMATION"


_TRANSFORMATION_CONTRACTS = {
    "UTF8_DECODE": ("SOURCE_BYTES", "UNICODE_PARSE_VIEW", ("UTF8_VALID",), "BLOCKS_DATASET"),
    "UTF8_BOM_REMOVE_FOR_PARSE": ("UNICODE_PARSE_VIEW", "UNICODE_PARSE_VIEW", ("UTF8_BOM_PRESENT",), "NONE"),
    "CSV_DELIMITER_SELECT": ("CSV_TEXT", "RECTANGULAR_ROWS", ("ONE_ALLOWLISTED_DELIMITER_VALID",), "BLOCKS_DATASET"),
    "XLSX_DATA_CELL_EXTRACT": ("SAFE_XLSX_XML", "SOURCE_TOKEN", ("XLSX_SECURITY_VALIDATED",), "BLOCKS_DATASET"),
    "HEADER_COMPARISON_KEY": ("SOURCE_HEADER", "HEADER_COMPARISON_KEY", ("HEADER_PRESERVED",), "NONE"),
    "BLANK_CLASSIFY": ("RAW_TOKEN", "BLANK_EVIDENCE", ("TOKEN_AVAILABLE",), "NONE"),
    "TRIM_FOR_PARSE": ("RAW_TOKEN", "TRIMMED_PARSE_VIEW", ("RAW_TOKEN_PRESERVED",), "NONE"),
    "PARSE_DECIMAL_EXACT": ("TRIMMED_PARSE_VIEW", "EXACT_DECIMAL_OR_FAILURE", ("FULL_TOKEN_MATCH",), "LIMITS_COVERAGE"),
    "PARSE_ISO_DATE": ("TRIMMED_PARSE_VIEW", "ISO_DATE_OR_FAILURE", ("YYYY_MM_DD_FULL_TOKEN",), "LIMITS_COVERAGE"),
    "PRESERVE_TEXT": ("RAW_TOKEN", "PRESERVED_TEXT", ("RAW_TOKEN_PRESERVED",), "NONE"),
}


def _header_key(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).strip().casefold()
    return re.sub(r"[^a-z0-9]+", "_", normalized).strip("_")


@dataclass(frozen=True)
class PreparedColumn:
    column_id: str
    source_name: str
    header_key: str
    header_collision: bool
    source_representation: str
    structural_type: str
    structural_confidence: str
    total_count: int
    blank_count: int
    nonblank_count: int
    decimal_parse_success: int
    decimal_parse_failure: int
    decimal_parse_failure_rows: tuple[int, ...]
    date_parse_success: int
    date_parse_failure: int
    date_parse_failure_rows: tuple[int, ...]
    ambiguous_date_count: int
    ambiguous_date_rows: tuple[int, ...]
    null_like_token_count: int
    null_like_token_rows: tuple[int, ...]
    distinct_count: int
    repeated_value_candidates: tuple[DuplicateCandidate, ...]
    repeated_value_groups_truncated: bool

    def to_dict(self) -> dict[str, Any]:
        payload = self.__dict__.copy()
        payload["decimal_parse_failure_rows"] = list(self.decimal_parse_failure_rows)
        payload["date_parse_failure_rows"] = list(self.date_parse_failure_rows)
        payload["ambiguous_date_rows"] = list(self.ambiguous_date_rows)
        payload["null_like_token_rows"] = list(self.null_like_token_rows)
        payload["repeated_value_candidates"] = [
            item.to_dict() for item in self.repeated_value_candidates
        ]
        return payload


@dataclass(frozen=True)
class DuplicateCandidate:
    candidate_id: str
    comparison: str
    comparison_version: str
    occurrence_count: int
    source_row_numbers: tuple[int, ...]
    source_row_references_truncated: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "comparison": self.comparison,
            "comparison_version": self.comparison_version,
            "occurrence_count": self.occurrence_count,
            "source_row_numbers": list(self.source_row_numbers),
            "source_row_references_truncated": self.source_row_references_truncated,
        }


@dataclass(frozen=True)
class TransformationSummary:
    identifier: str
    version: str
    status: str
    attempts: int
    successes: int
    failures: int
    source_values_preserved: bool = True
    input_representation: str = ""
    output_representation: str = ""
    preconditions: tuple[str, ...] = ()
    failure_status: str = "REPORTED_NOT_REPAIRED"
    failure_readiness_effect: str = "NONE"
    automation_class: str = "SAFE_AUTOMATIC"

    def to_dict(self) -> dict[str, Any]:
        payload = self.__dict__.copy()
        payload["preconditions"] = list(self.preconditions)
        return payload


@dataclass(frozen=True)
class TransformationRefusal:
    identifier: str
    automation_class: str
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


@dataclass(frozen=True)
class QualityFinding:
    code: str
    level: str
    scope: str
    message: str
    count: int
    source_row_numbers: tuple[int, ...]
    source_row_references_truncated: bool
    readiness_effect: str
    remediation: str | None = None
    details: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "level": self.level,
            "scope": self.scope,
            "message": self.message,
            "count": self.count,
            "source_row_numbers": list(self.source_row_numbers),
            "source_row_references_truncated": self.source_row_references_truncated,
            "readiness_effect": self.readiness_effect,
            "remediation": self.remediation,
            "details": None if self.details is None else dict(self.details),
        }


@dataclass(frozen=True)
class DataQualityReport:
    quality_report_version: str
    quality_report_digest: str
    dataset_id: str
    source_fingerprint: str
    source_sheet: str | None
    preparation_version: str
    preparation_digest: str
    profile_version: str
    profile_digest: str
    mapping_digest: str | None
    total_rows: int
    structurally_accepted_rows: int
    column_count: int
    columns: tuple[PreparedColumn, ...]
    performed_transformations: tuple[TransformationSummary, ...]
    refused_transformations: tuple[TransformationRefusal, ...]
    exact_duplicate_candidate_count: int
    exact_duplicate_group_count: int
    key_duplicate_candidates: tuple[DuplicateCandidate, ...]
    unresolved_decisions: tuple[str, ...]
    currency_state: str
    findings: tuple[QualityFinding, ...]
    readiness_references: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "quality_report_version": self.quality_report_version,
            "quality_report_digest": self.quality_report_digest,
            "dataset_id": self.dataset_id,
            "source_fingerprint": self.source_fingerprint,
            "source_sheet": self.source_sheet,
            "preparation_version": self.preparation_version,
            "preparation_digest": self.preparation_digest,
            "profile_version": self.profile_version,
            "profile_digest": self.profile_digest,
            "mapping_digest": self.mapping_digest,
            "total_rows": self.total_rows,
            "structurally_accepted_rows": self.structurally_accepted_rows,
            "column_count": self.column_count,
            "columns": [column.to_dict() for column in self.columns],
            "performed_transformations": [
                item.to_dict() for item in self.performed_transformations
            ],
            "refused_transformations": [
                item.to_dict() for item in self.refused_transformations
            ],
            "exact_duplicate_candidate_count": self.exact_duplicate_candidate_count,
            "exact_duplicate_group_count": self.exact_duplicate_group_count,
            "key_duplicate_candidates": [
                item.to_dict() for item in self.key_duplicate_candidates
            ],
            "unresolved_decisions": list(self.unresolved_decisions),
            "currency_state": self.currency_state,
            "findings": [finding.to_dict() for finding in self.findings],
            "readiness_references": list(self.readiness_references),
        }


@dataclass(frozen=True)
class PreparationManifest:
    preparation_version: str
    preparation_digest: str
    dataset_id: str
    source_fingerprint: str
    source_sheet: str | None
    source_format: str
    ingestion_contract_version: str
    profile_version: str
    profile_digest: str
    structural_configuration: dict[str, Any]
    total_rows: int
    structurally_accepted_rows: int
    column_count: int
    columns: tuple[PreparedColumn, ...]
    performed_transformations: tuple[TransformationSummary, ...]
    refused_transformations: tuple[TransformationRefusal, ...]
    exact_duplicate_candidate_count: int
    exact_duplicate_group_count: int
    exact_duplicate_candidates: tuple[DuplicateCandidate, ...]
    duplicate_groups_truncated: bool

    def column(self, source_name: str) -> PreparedColumn:
        for column in self.columns:
            if column.source_name == source_name:
                return column
        raise KeyError(source_name)

    def to_dict(self) -> dict[str, Any]:
        return {
            "preparation_version": self.preparation_version,
            "preparation_digest": self.preparation_digest,
            "dataset_id": self.dataset_id,
            "source_fingerprint": self.source_fingerprint,
            "source_sheet": self.source_sheet,
            "source_format": self.source_format,
            "ingestion_contract_version": self.ingestion_contract_version,
            "profile_version": self.profile_version,
            "profile_digest": self.profile_digest,
            "structural_configuration": dict(self.structural_configuration),
            "total_rows": self.total_rows,
            "structurally_accepted_rows": self.structurally_accepted_rows,
            "column_count": self.column_count,
            "columns": [column.to_dict() for column in self.columns],
            "performed_transformations": [
                item.to_dict() for item in self.performed_transformations
            ],
            "refused_transformations": [
                item.to_dict() for item in self.refused_transformations
            ],
            "exact_duplicate_candidate_count": self.exact_duplicate_candidate_count,
            "exact_duplicate_group_count": self.exact_duplicate_group_count,
            "exact_duplicate_candidates": [
                item.to_dict() for item in self.exact_duplicate_candidates
            ],
            "duplicate_groups_truncated": self.duplicate_groups_truncated,
        }


class PreparationEngine:
    """Prepare deterministic structural evidence without assigning financial meaning."""

    def __init__(
        self, *, limits: IngestionLimits | None = None,
        max_failure_row_references: int = 20,
        max_duplicate_groups: int = 100,
        max_duplicate_row_references: int = 20,
    ):
        if (max_failure_row_references < 0 or max_duplicate_groups < 0
                or max_duplicate_row_references < 0):
            raise ValueError("Preparation bounds cannot be negative.")
        self._limits = limits or IngestionLimits()
        self._max_failure_row_references = max_failure_row_references
        self._max_duplicate_groups = max_duplicate_groups
        self._max_duplicate_row_references = max_duplicate_row_references

    def prepare(
        self, dataset: IngestedDataset, profile: DatasetProfile,
    ) -> PreparationManifest:
        if (dataset.dataset_id != profile.dataset_id
                or dataset.source_sha256 != profile.source_sha256
                or dataset.row_count != profile.row_count
                or dataset.column_count != profile.column_count
                or dataset.columns != tuple(column.name for column in profile.columns)
                or len(dataset.source_row_numbers) != dataset.row_count):
            raise OnboardingError("preparation_artifact_mismatch")

        header_keys = tuple(_header_key(name) for name in dataset.columns)
        key_counts = Counter(header_keys)
        columns = []
        for index, profile_column in enumerate(profile.columns):
            values = tuple(row[index] for row in dataset.rows)
            observed = tuple(
                (source_row, value)
                for source_row, value in zip(dataset.source_row_numbers, values)
                if value.strip() != ""
            )
            nonblank = tuple(value for _, value in observed)
            decimal_failures = tuple(
                source_row for source_row, value in observed
                if _decimal_value(value) is None
            )
            date_failures = tuple(
                source_row for source_row, value in observed
                if _iso_date(value) is None
            )
            ambiguous_rows = tuple(
                source_row for source_row, value in observed
                if _AMBIGUOUS_DATE.fullmatch(value.strip())
            )
            null_like_rows = tuple(
                source_row for source_row, value in observed
                if value.strip().casefold() in _NULL_LIKE
            )
            repeated_values: dict[str, list[int]] = {}
            for source_row, value in observed:
                repeated_values.setdefault(value, []).append(source_row)
            repeated_groups = [
                (value, tuple(source_rows))
                for value, source_rows in repeated_values.items()
                if len(source_rows) > 1
            ]
            repeated_candidates = tuple(DuplicateCandidate(
                candidate_id="key_" + hashlib.sha256(
                    f"{profile_column.column_id}:{value}".encode("utf-8")
                ).hexdigest()[:20],
                comparison=f"SOURCE_COLUMN_VALUE:{profile_column.column_id}",
                comparison_version="1.0",
                occurrence_count=len(source_rows),
                source_row_numbers=source_rows[:self._max_duplicate_row_references],
                source_row_references_truncated=(
                    len(source_rows) > self._max_duplicate_row_references
                ),
            ) for value, source_rows in repeated_groups[:self._max_duplicate_groups])
            columns.append(PreparedColumn(
                column_id=profile_column.column_id,
                source_name=profile_column.name,
                header_key=header_keys[index],
                header_collision=key_counts[header_keys[index]] > 1,
                source_representation=profile_column.source_representation,
                structural_type=profile_column.structural_type,
                structural_confidence=(
                    "NO_EVIDENCE" if profile_column.structural_type == "EMPTY"
                    else "MIXED" if profile_column.structural_type == "OTHER"
                    else "HIGH"
                ),
                total_count=len(values),
                blank_count=len(values) - len(nonblank),
                nonblank_count=len(nonblank),
                decimal_parse_success=len(nonblank) - len(decimal_failures),
                decimal_parse_failure=len(decimal_failures),
                decimal_parse_failure_rows=decimal_failures[:self._max_failure_row_references],
                date_parse_success=len(nonblank) - len(date_failures),
                date_parse_failure=len(date_failures),
                date_parse_failure_rows=date_failures[:self._max_failure_row_references],
                ambiguous_date_count=len(ambiguous_rows),
                ambiguous_date_rows=ambiguous_rows[:self._max_failure_row_references],
                null_like_token_count=len(null_like_rows),
                null_like_token_rows=null_like_rows[:self._max_failure_row_references],
                distinct_count=len(set(nonblank)),
                repeated_value_candidates=repeated_candidates,
                repeated_value_groups_truncated=(
                    len(repeated_groups) > self._max_duplicate_groups
                ),
            ))
        duplicate_rows: dict[tuple[str, ...], list[int]] = {}
        for source_row, row in zip(dataset.source_row_numbers, dataset.rows):
            duplicate_rows.setdefault(row, []).append(source_row)
        complete_groups = [
            (row, tuple(row_numbers))
            for row, row_numbers in duplicate_rows.items()
            if len(row_numbers) > 1
        ]
        duplicate_candidates = tuple(
            DuplicateCandidate(
                candidate_id="dup_" + hashlib.sha256(json.dumps(
                    row, ensure_ascii=False, separators=(",", ":"),
                ).encode("utf-8")).hexdigest()[:20],
                comparison="EXACT_SOURCE_ROW_TOKENS",
                comparison_version="1.0",
                occurrence_count=len(row_numbers),
                source_row_numbers=row_numbers[:self._max_duplicate_row_references],
                source_row_references_truncated=(
                    len(row_numbers) > self._max_duplicate_row_references
                ),
            )
            for row, row_numbers in complete_groups[:self._max_duplicate_groups]
        )
        cell_count = dataset.row_count * dataset.column_count
        nonblank_count = sum(column.nonblank_count for column in columns)
        decimal_success = sum(column.decimal_parse_success for column in columns)
        date_success = sum(column.date_parse_success for column in columns)
        transformations = [_transformation_summary(
            "XLSX_DATA_CELL_EXTRACT" if dataset.detected_format == "XLSX" else "UTF8_DECODE",
            1, 1, 0,
        )]
        if dataset.detected_format == "CSV":
            if dataset.encoding == "UTF-8-SIG":
                transformations.append(_transformation_summary(
                    "UTF8_BOM_REMOVE_FOR_PARSE", 1, 1, 0,
                ))
            transformations.append(_transformation_summary(
                "CSV_DELIMITER_SELECT", 1, 1, 0,
            ))
        transformations.extend((
            _transformation_summary(
                "HEADER_COMPARISON_KEY", dataset.column_count,
                sum(not column.header_collision for column in columns),
                sum(column.header_collision for column in columns),
            ),
            _transformation_summary(
                "BLANK_CLASSIFY", cell_count,
                sum(column.blank_count for column in columns), 0,
            ),
            _transformation_summary(
                "TRIM_FOR_PARSE", nonblank_count,
                nonblank_count, 0,
            ),
            _transformation_summary(
                "PARSE_DECIMAL_EXACT", nonblank_count,
                decimal_success, nonblank_count - decimal_success,
            ),
            _transformation_summary(
                "PARSE_ISO_DATE", nonblank_count,
                date_success, nonblank_count - date_success,
            ),
            _transformation_summary(
                "PRESERVE_TEXT", cell_count, cell_count, 0,
            ),
        ))
        refused_identifiers = (
            "NON_UTF8_ENCODING_GUESS", "FINANCIAL_IMPUTATION", "ROW_DELETION",
            "DUPLICATE_MERGE", "OUTLIER_MODIFICATION", "SIGN_MUTATION",
            "CURRENCY_INFERENCE", "FX_CONVERSION", "CASH_DIRECTION_INFERENCE",
            "DEBIT_CREDIT_INTERPRETATION", "PROFIT_RECONSTRUCTION",
            "OUTSTANDING_BALANCE_INFERENCE", "SEMANTIC_CONFIRMATION",
            "DOMAIN_CONFIRMATION",
        ) + (("AMBIGUOUS_DATE_ORDER",) if any(
            column.ambiguous_date_count for column in columns
        ) else ())
        suggest_only = {"AMBIGUOUS_DATE_ORDER", "NULL_TOKEN_INTERPRETATION"}
        if any(column.null_like_token_count for column in columns):
            refused_identifiers += ("NULL_TOKEN_INTERPRETATION",)
        refusals = tuple(TransformationRefusal(
            identifier, ("SUGGEST_ONLY" if identifier in suggest_only
                         else "PROHIBITED_AUTOMATION"),
            "The V2.1 preparation contract does not authorize this transformation.",
        ) for identifier in refused_identifiers)
        manifest = PreparationManifest(
            preparation_version=PREPARATION_VERSION,
            preparation_digest="",
            dataset_id=dataset.dataset_id,
            source_fingerprint=dataset.source_sha256,
            source_sheet=dataset.source_sheet,
            source_format=dataset.detected_format,
            ingestion_contract_version=dataset.ingestion_contract_version,
            profile_version=profile.profile_version,
            profile_digest=profile.profile_digest,
            structural_configuration={
                "ingestion_limits": self._limits.to_dict(),
                "max_failure_row_references": self._max_failure_row_references,
                "max_duplicate_groups": self._max_duplicate_groups,
                "max_duplicate_row_references": self._max_duplicate_row_references,
            },
            total_rows=dataset.row_count,
            structurally_accepted_rows=dataset.row_count,
            column_count=dataset.column_count,
            columns=tuple(columns),
            performed_transformations=tuple(transformations),
            refused_transformations=refusals,
            exact_duplicate_candidate_count=sum(
                len(row_numbers) - 1 for _, row_numbers in complete_groups
            ),
            exact_duplicate_group_count=len(complete_groups),
            exact_duplicate_candidates=duplicate_candidates,
            duplicate_groups_truncated=len(complete_groups) > self._max_duplicate_groups,
        )
        return replace(manifest, preparation_digest=preparation_digest(manifest.to_dict()))

    def assess(
        self, preparation: PreparationManifest, profile: DatasetProfile, mapping=None,
        readiness_report=None,
    ) -> DataQualityReport:
        if (preparation_digest(preparation.to_dict()) != preparation.preparation_digest
                or preparation.dataset_id != profile.dataset_id
                or preparation.source_fingerprint != profile.source_sha256
                or preparation.profile_digest != profile.profile_digest
                or preparation.total_rows != profile.row_count
                or preparation.column_count != profile.column_count):
            raise OnboardingError("preparation_artifact_mismatch")
        if mapping is not None and (
            mapping.dataset_id != profile.dataset_id
            or mapping.profile_digest != profile.profile_digest
        ):
            raise OnboardingError("preparation_artifact_mismatch")
        if readiness_report is not None and (
            mapping is None
            or readiness_report.dataset_id != profile.dataset_id
            or readiness_report.mapping_digest != mapping.mapping_digest
            or readiness_report.currency_state != mapping.currency_state
        ):
            raise OnboardingError("preparation_artifact_mismatch")

        findings = [QualityFinding(
            code="STRUCTURAL_PROFILE_COMPLETE",
            level=FindingLevel.INFORMATION.value,
            scope="DATASET",
            message="Deterministic structural preparation completed.",
            count=preparation.total_rows,
            source_row_numbers=(),
            source_row_references_truncated=False,
            readiness_effect="NONE",
        )]
        unresolved = []
        for column in preparation.columns:
            scope = f"COLUMN:{column.column_id}"
            if column.header_collision:
                findings.append(QualityFinding(
                    "HEADER_KEY_COLLISION", FindingLevel.WARNING.value, scope,
                    "Derived header comparison keys collide; original columns remain distinct.",
                    1, (), False, "NONE",
                    "Review columns by their original names and stable column IDs.",
                    {"header_key": column.header_key},
                ))
            if column.blank_count:
                findings.append(QualityFinding(
                    "MISSING_VALUES_OBSERVED", FindingLevel.WARNING.value, scope,
                    "Blank source cells were observed and remain missing.",
                    column.blank_count, (), False, "LIMITS_COVERAGE",
                ))
            if column.null_like_token_count:
                findings.append(QualityFinding(
                    "NULL_LIKE_TOKEN_PRESERVED", FindingLevel.WARNING.value, scope,
                    "Nonblank null-like tokens remain source values or parse failures.",
                    column.null_like_token_count, column.null_like_token_rows,
                    column.null_like_token_count > len(column.null_like_token_rows),
                    "NONE", "Correct and re-upload the source if these tokens mean missing.",
                ))
            if column.decimal_parse_success and column.decimal_parse_failure:
                findings.append(QualityFinding(
                    "DECIMAL_PARSE_FAILURE", FindingLevel.WARNING.value, scope,
                    "Some nonblank values did not parse as exact decimals.",
                    column.decimal_parse_failure, column.decimal_parse_failure_rows,
                    column.decimal_parse_failure > len(column.decimal_parse_failure_rows),
                    "LIMITS_COVERAGE",
                ))
            if column.date_parse_success and column.date_parse_failure:
                findings.append(QualityFinding(
                    "DATE_PARSE_FAILURE", FindingLevel.WARNING.value, scope,
                    "Some nonblank values did not parse as allowlisted ISO dates.",
                    column.date_parse_failure, column.date_parse_failure_rows,
                    column.date_parse_failure > len(column.date_parse_failure_rows),
                    "LIMITS_COVERAGE",
                ))
            if column.ambiguous_date_count:
                decision = f"date_format:{column.column_id}"
                unresolved.append(decision)
                findings.append(QualityFinding(
                    "AMBIGUOUS_DATE_REQUIRES_CONFIRMATION",
                    FindingLevel.REQUIRES_CONFIRMATION.value, scope,
                    "Ambiguous date order was preserved without choosing a locale.",
                    column.ambiguous_date_count, column.ambiguous_date_rows,
                    column.ambiguous_date_count > len(column.ambiguous_date_rows),
                    "BLOCKS_OPERATION", "Confirm a date format through semantic authority.",
                ))
        if preparation.exact_duplicate_candidate_count:
            row_numbers = tuple(
                row
                for candidate in preparation.exact_duplicate_candidates
                for row in candidate.source_row_numbers
            )[:self._max_failure_row_references]
            findings.append(QualityFinding(
                "EXACT_DUPLICATE_CANDIDATE", FindingLevel.WARNING.value, "DATASET",
                "Exact source-row duplicate candidates were retained for review.",
                preparation.exact_duplicate_candidate_count, row_numbers,
                preparation.duplicate_groups_truncated,
                "NONE", "Review candidates; V2.1 does not delete or merge them.",
            ))

        key_duplicate_candidates = ()
        if mapping is not None:
            if mapping.approved_domain is None:
                unresolved.append("canonical_domain")
            unresolved.extend(
                f"semantic_role:{proposal.column_id}"
                for proposal in mapping.proposals
                if proposal.confirmation_required or proposal.status == "CONFLICT"
            )
            invoice_columns = tuple(
                proposal for proposal in mapping.proposals
                if (proposal.status == "CONFIRMED"
                    and proposal.proposed_role == "INVOICE_ID")
            )
            if len(invoice_columns) == 1:
                prepared_column = next((
                    column for column in preparation.columns
                    if column.column_id == invoice_columns[0].column_id
                ), None)
                if prepared_column is None:
                    raise OnboardingError("preparation_artifact_mismatch")
                key_duplicate_candidates = tuple(replace(
                    candidate, comparison="KEY_ROLE:INVOICE_ID",
                ) for candidate in prepared_column.repeated_value_candidates)
                if key_duplicate_candidates:
                    rows = tuple(
                        row for candidate in key_duplicate_candidates
                        for row in candidate.source_row_numbers
                    )[:self._max_failure_row_references]
                    findings.append(QualityFinding(
                        "KEY_BASED_DUPLICATE_CANDIDATE",
                        FindingLevel.WARNING.value,
                        f"COLUMN:{prepared_column.column_id}",
                        "Rows share a confirmed invoice identity and remain candidates for review.",
                        sum(
                            candidate.occurrence_count - 1
                            for candidate in key_duplicate_candidates
                        ),
                        rows,
                        prepared_column.repeated_value_groups_truncated,
                        "NONE",
                        "Review repeated invoice identities; no rows are deleted or merged.",
                        {"comparison_key": "INVOICE_ID"},
                    ))
        readiness_references = tuple(dict.fromkeys(
            finding.code for finding in findings
            if finding.readiness_effect != "NONE"
        ))
        if readiness_report is not None:
            readiness_references += tuple(
                f"CAPABILITY:{capability.identifier}:{capability.state}"
                for capability in readiness_report.capabilities
            )
        report = DataQualityReport(
            quality_report_version=QUALITY_REPORT_VERSION,
            quality_report_digest="",
            dataset_id=preparation.dataset_id,
            source_fingerprint=preparation.source_fingerprint,
            source_sheet=preparation.source_sheet,
            preparation_version=preparation.preparation_version,
            preparation_digest=preparation.preparation_digest,
            profile_version=profile.profile_version,
            profile_digest=profile.profile_digest,
            mapping_digest=None if mapping is None else mapping.mapping_digest,
            total_rows=preparation.total_rows,
            structurally_accepted_rows=preparation.structurally_accepted_rows,
            column_count=preparation.column_count,
            columns=preparation.columns,
            performed_transformations=preparation.performed_transformations,
            refused_transformations=preparation.refused_transformations,
            exact_duplicate_candidate_count=preparation.exact_duplicate_candidate_count,
            exact_duplicate_group_count=preparation.exact_duplicate_group_count,
            key_duplicate_candidates=key_duplicate_candidates,
            unresolved_decisions=tuple(dict.fromkeys(unresolved)),
            currency_state="UNKNOWN" if mapping is None else mapping.currency_state,
            findings=tuple(findings),
            readiness_references=readiness_references,
        )
        return replace(
            report, quality_report_digest=quality_report_digest(report.to_dict()),
        )


def preparation_digest(payload: dict[str, Any]) -> str:
    return _content_digest(payload, "preparation_digest")


def _transformation_summary(
    identifier: str, attempts: int, successes: int, failures: int,
) -> TransformationSummary:
    input_representation, output_representation, preconditions, effect = (
        _TRANSFORMATION_CONTRACTS[identifier]
    )
    return TransformationSummary(
        identifier=identifier,
        version="1.0",
        status="APPLIED",
        attempts=attempts,
        successes=successes,
        failures=failures,
        input_representation=input_representation,
        output_representation=output_representation,
        preconditions=preconditions,
        failure_readiness_effect=effect,
    )


def quality_report_digest(payload: dict[str, Any]) -> str:
    return _content_digest(payload, "quality_report_digest")


def _content_digest(payload: dict[str, Any], field: str) -> str:
    canonical = dict(payload)
    canonical[field] = ""
    return hashlib.sha256(json.dumps(
        canonical, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")).hexdigest()


def _candidate_from_dict(payload: dict[str, Any]) -> DuplicateCandidate:
    return DuplicateCandidate(
        candidate_id=payload["candidate_id"],
        comparison=payload["comparison"],
        comparison_version=payload["comparison_version"],
        occurrence_count=payload["occurrence_count"],
        source_row_numbers=tuple(payload["source_row_numbers"]),
        source_row_references_truncated=payload["source_row_references_truncated"],
    )


def _column_from_dict(payload: dict[str, Any]) -> PreparedColumn:
    return PreparedColumn(
        **(payload | {
            "decimal_parse_failure_rows": tuple(payload["decimal_parse_failure_rows"]),
            "date_parse_failure_rows": tuple(payload["date_parse_failure_rows"]),
            "ambiguous_date_rows": tuple(payload["ambiguous_date_rows"]),
            "null_like_token_rows": tuple(payload["null_like_token_rows"]),
            "repeated_value_candidates": tuple(
                _candidate_from_dict(item)
                for item in payload["repeated_value_candidates"]
            ),
        })
    )


def _transformation_from_dict(payload: dict[str, Any]) -> TransformationSummary:
    return TransformationSummary(**(payload | {
        "preconditions": tuple(payload["preconditions"]),
    }))


def _refusal_from_dict(payload: dict[str, Any]) -> TransformationRefusal:
    return TransformationRefusal(**payload)


def _validate_closed_vocabulary(
    transformations: tuple[TransformationSummary, ...],
    refusals: tuple[TransformationRefusal, ...],
    findings: tuple[QualityFinding, ...] = (),
    *, currency_state: str | None = None,
) -> None:
    for item in transformations:
        contract = _TRANSFORMATION_CONTRACTS.get(item.identifier)
        if contract is None:
            raise OnboardingError("unsupported_transformation")
        input_representation, output_representation, preconditions, effect = contract
        if (
            item.version != "1.0"
            or item.status != "APPLIED"
            or not item.source_values_preserved
            or item.input_representation != input_representation
            or item.output_representation != output_representation
            or item.preconditions != preconditions
            or item.failure_status != "REPORTED_NOT_REPAIRED"
            or item.failure_readiness_effect != effect
            or item.automation_class != "SAFE_AUTOMATIC"
        ):
            raise OnboardingError("unsupported_transformation")
    if any(
        item.identifier not in _REFUSAL_CLASSES
        or item.automation_class != _REFUSAL_CLASSES.get(item.identifier)
        for item in refusals
    ):
        raise OnboardingError("preparation_corrupt")
    if any(
        item.code not in _FINDING_CONTRACTS
        or (item.level, item.readiness_effect) != _FINDING_CONTRACTS.get(item.code)
        for item in findings
    ):
        raise OnboardingError("quality_report_corrupt")
    if currency_state is not None and currency_state not in _CURRENCY_STATES:
        raise OnboardingError("quality_report_corrupt")


def preparation_from_dict(payload: dict[str, Any]) -> PreparationManifest:
    """Rehydrate and authenticate a persisted preparation manifest."""
    if (type(payload) is not dict
            or payload.get("preparation_version") != PREPARATION_VERSION
            or preparation_digest(payload) != payload.get("preparation_digest")):
        raise OnboardingError("preparation_digest_mismatch")
    try:
        preparation = PreparationManifest(
            **(payload | {
                "columns": tuple(_column_from_dict(item) for item in payload["columns"]),
                "performed_transformations": tuple(
                    _transformation_from_dict(item)
                    for item in payload["performed_transformations"]
                ),
                "refused_transformations": tuple(
                    _refusal_from_dict(item)
                    for item in payload["refused_transformations"]
                ),
                "exact_duplicate_candidates": tuple(
                    _candidate_from_dict(item)
                    for item in payload["exact_duplicate_candidates"]
                ),
            })
        )
        _validate_closed_vocabulary(
            preparation.performed_transformations,
            preparation.refused_transformations,
        )
        return preparation
    except (KeyError, TypeError, ValueError):
        raise OnboardingError("preparation_corrupt") from None


def quality_report_from_dict(payload: dict[str, Any]) -> DataQualityReport:
    """Rehydrate and authenticate a persisted data-quality report."""
    if (type(payload) is not dict
            or payload.get("quality_report_version") != QUALITY_REPORT_VERSION
            or quality_report_digest(payload) != payload.get("quality_report_digest")):
        raise OnboardingError("quality_report_digest_mismatch")
    try:
        report = DataQualityReport(
            **(payload | {
                "columns": tuple(_column_from_dict(item) for item in payload["columns"]),
                "performed_transformations": tuple(
                    _transformation_from_dict(item)
                    for item in payload["performed_transformations"]
                ),
                "refused_transformations": tuple(
                    _refusal_from_dict(item)
                    for item in payload["refused_transformations"]
                ),
                "key_duplicate_candidates": tuple(
                    _candidate_from_dict(item)
                    for item in payload["key_duplicate_candidates"]
                ),
                "unresolved_decisions": tuple(payload["unresolved_decisions"]),
                "findings": tuple(QualityFinding(
                    **(item | {
                        "source_row_numbers": tuple(item["source_row_numbers"]),
                    })
                ) for item in payload["findings"]),
                "readiness_references": tuple(payload["readiness_references"]),
            })
        )
        _validate_closed_vocabulary(
            report.performed_transformations,
            report.refused_transformations,
            report.findings,
            currency_state=report.currency_state,
        )
        return report
    except (KeyError, TypeError, ValueError):
        raise OnboardingError("quality_report_corrupt") from None
