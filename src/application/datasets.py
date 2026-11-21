"""Dataset use cases delegated to the existing onboarding authority."""

from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryDirectory

from src.onboarding import OnboardingError

from .models import (
    CapabilityReadinessProjection,
    ColumnProfileProjection,
    CurrencyReadinessProjection,
    DatasetProfileProjection,
    DatasetSummary,
    DatasetUpload,
    OperationReadinessProjection,
    ReadinessProjection,
    SemanticMappingProjection,
    StagedDatasetUpload,
)


class DatasetApplication:
    def __init__(self, onboarding, *, max_upload_bytes: int = 10 * 1024 * 1024):
        self._onboarding = onboarding
        self._max_upload_bytes = max_upload_bytes

    def list_datasets(self) -> tuple[DatasetSummary, ...]:
        return tuple(self.detail(dataset_id) for dataset_id in self._onboarding.dataset_ids())

    def detail(self, dataset_id: str) -> DatasetSummary:
        state = self._onboarding.status(dataset_id)
        readiness = self._onboarding.capabilities(dataset_id)
        financial = next(
            item for item in readiness["capabilities"]
            if item["identifier"] == "FINANCIAL_ANALYSIS"
        )
        return DatasetSummary(
            dataset_id=state["dataset_id"],
            source_filename=state["source_filename"],
            source_type=state["source_type"],
            row_count=state["row_count"],
            column_count=state["column_count"],
            lifecycle_state=state["lifecycle_state"],
            readiness_state=state["readiness_state"],
            approved_domain=state["approved_domain"],
            currency_state=state["currency_state"],
            supported_operations=tuple(
                operation["identifier"] for operation in financial["operations"]
                if operation["state"] not in {"BLOCKED", "UNSUPPORTED"}
            ),
            limitations=tuple(financial["limitations"]),
        )

    def upload(self, command: DatasetUpload) -> DatasetSummary:
        extension = command.extension()
        if extension not in {".csv", ".xlsx"}:
            raise OnboardingError("unsupported_format")
        if type(command.content) is not bytes or len(command.content) > self._max_upload_bytes:
            raise OnboardingError("file_too_large")
        with TemporaryDirectory(prefix="financial-manager-upload-") as temporary_root:
            temporary_path = None
            try:
                with NamedTemporaryFile(
                    mode="wb", suffix=extension, prefix="upload-",
                    dir=temporary_root, delete=False,
                ) as temporary:
                    temporary.write(command.content)
                    temporary_path = Path(temporary.name)
                return self.upload_staged(StagedDatasetUpload(
                    filename=command.filename,
                    staged_path=temporary_path,
                    sheet=command.sheet,
                    provenance_note=command.provenance_note,
                ))
            finally:
                if temporary_path is not None:
                    temporary_path.unlink(missing_ok=True)

    def upload_staged(self, command: StagedDatasetUpload) -> DatasetSummary:
        """Ingest an HTTP/server-owned artifact without buffering it again."""
        extension = command.extension()
        path = command.staged_path
        if extension not in {".csv", ".xlsx"} or path.suffix.lower() != extension:
            raise OnboardingError("unsupported_format")
        try:
            size = path.stat().st_size
        except (OSError, ValueError):
            raise OnboardingError("invalid_upload_artifact") from None
        if not path.is_file() or size > self._max_upload_bytes:
            raise OnboardingError("file_too_large")
        state = self._onboarding.add(
            path, sheet=command.sheet, provenance_note=command.provenance_note,
        )
        return self.detail(state["dataset_id"])

    def profile(self, dataset_id: str) -> DatasetProfileProjection:
        profile = self._onboarding.profile(dataset_id)
        return DatasetProfileProjection(
            dataset_id=profile["dataset_id"], status=profile["status"],
            profile_version=profile["profile_version"], profile_digest=profile["profile_digest"],
            row_count=profile["row_count"], column_count=profile["column_count"],
            duplicate_row_candidates=profile["duplicate_row_candidates"],
            currency_state=profile["currency_state"],
            columns=tuple(ColumnProfileProjection(
                column_id=column["column_id"], name=column["name"],
                source_representation=column["source_representation"],
                structural_type=column["structural_type"],
                missing_count=column["missing_count"],
                missing_percentage=column["missing_percentage"],
                unique_count=column["unique_count"],
                decimal_parse_success=column["decimal_parse_success"],
                date_parse_success=column["date_parse_success"],
                ambiguous_date_count=column["ambiguous_date_count"],
                numeric_min=column["numeric_min"], numeric_max=column["numeric_max"],
                decimal_scales=tuple(column["decimal_scales"]),
                date_min=column["date_min"], date_max=column["date_max"],
                categorical_cardinality=column["categorical_cardinality"],
                examples=tuple(column["examples"]),
                frequencies=tuple(tuple(item) for item in column["frequencies"]),
                possible_identifier=column["possible_identifier"],
                likely_sensitive=column["likely_sensitive"],
                patterns=tuple(column["patterns"]),
                formatting_observations=tuple(column["formatting_observations"]),
                confirmation_values=tuple(column["confirmation_values"]),
            ) for column in profile["columns"]), bounds=profile["bounds"],
        )

    def mappings(self, dataset_id: str) -> SemanticMappingProjection:
        mapping = self._onboarding.mappings(dataset_id)
        return SemanticMappingProjection(
            dataset_id=mapping["dataset_id"], status=mapping["status"],
            mapping_version=mapping["mapping_version"], mapping_digest=mapping["mapping_digest"],
            approved_domain=mapping["approved_domain"],
            domain_suggestions=tuple(mapping["domain_suggestions"]),
            currency_state=mapping["currency_state"], confirmed_currency=mapping["confirmed_currency"],
            proposals=tuple(mapping["proposals"]), decisions=tuple(mapping["decisions"]),
            qualifiers=mapping["qualifiers"],
            unresolved_requirements=tuple(
                proposal["source_column"] for proposal in mapping["proposals"]
                if proposal["confirmation_required"]
            ),
        )

    def confirm_role(self, dataset_id: str, *, column: str, role: str, evidence: str,
                     value_mapping: dict[str, str] | None = None,
                     date_format: str | None = None) -> DatasetSummary:
        self._onboarding.confirm(
            dataset_id, column, role, evidence=evidence,
            value_mapping=value_mapping, date_format=date_format,
        )
        return self.detail(dataset_id)

    def decide_semantic(self, dataset_id: str, *, column: str, decision: str,
                        evidence: str, role: str | None = None,
                        value_mapping: dict[str, str] | None = None,
                        date_format: str | None = None) -> DatasetSummary:
        self._onboarding.decide(
            dataset_id, column, decision, evidence=evidence, role=role,
            value_mapping=value_mapping, date_format=date_format,
        )
        return self.detail(dataset_id)

    def reject_role(self, dataset_id: str, *, column: str, evidence: str) -> DatasetSummary:
        self._onboarding.reject(dataset_id, column, evidence=evidence)
        return self.detail(dataset_id)

    def confirm_domain(self, dataset_id: str, *, domain: str, evidence: str) -> DatasetSummary:
        self._onboarding.confirm_domain(dataset_id, domain, evidence=evidence)
        return self.detail(dataset_id)

    def confirm_qualifiers(self, dataset_id: str, *, evidence: str,
                           amount_basis: str | None = None,
                           dataset_reference_date: str | None = None,
                           cash_amount_convention: str | None = None) -> DatasetSummary:
        self._onboarding.confirm_qualifiers(
            dataset_id, evidence=evidence, amount_basis=amount_basis,
            dataset_reference_date=dataset_reference_date,
            cash_amount_convention=cash_amount_convention,
        )
        return self.detail(dataset_id)

    def stop(self, dataset_id: str, *, reject: bool, evidence: str) -> DatasetSummary:
        self._onboarding.stop(dataset_id, reject=reject, evidence=evidence)
        return self.detail(dataset_id)

    def readiness(self, dataset_id: str) -> ReadinessProjection:
        readiness = self._onboarding.capabilities(dataset_id)
        return ReadinessProjection(
            version=readiness["version"], dataset_id=readiness["dataset_id"],
            canonical_domain=readiness["canonical_domain"],
            mapping_digest=readiness["mapping_digest"],
            currency=CurrencyReadinessProjection(**readiness["currency"]),
            capabilities=tuple(CapabilityReadinessProjection(
                identifier=capability["identifier"], state=capability["state"],
                semantic_readiness=capability["semantic_readiness"],
                policy_readiness=capability["policy_readiness"],
                execution_readiness=capability["execution_readiness"],
                reasons=tuple(capability["reasons"]),
                limitations=tuple(capability["limitations"]),
                operations=tuple(OperationReadinessProjection(
                    identifier=operation["identifier"], state=operation["state"],
                    required_semantics=tuple(operation["required_semantics"]),
                    reasons=tuple(operation["reasons"]),
                ) for operation in capability["operations"]),
            ) for capability in readiness["capabilities"]),
        )
