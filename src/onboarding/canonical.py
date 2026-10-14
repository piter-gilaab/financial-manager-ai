"""Closed canonical mapping specifications and source-row lineage."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
import hashlib
import json
from typing import Any

from .models import IngestedDataset, OnboardingError
from .profiling import DatasetProfile, _decimal_value, _iso_date, is_missing_value
from .semantics import SemanticMapping


CANONICAL_MAPPING_VERSION = "1.0"
_DECIMAL_ROLES = {
    "AMOUNT", "UNITS_SOLD", "SALES", "PROFIT", "DISCOUNT", "GROSS_SALES", "COGS",
    "SALE_PRICE", "MANUFACTURING_PRICE", "BALANCE",
}
_DATE_ROLES = {"TRANSACTION_DATE", "POSTING_DATE", "DUE_DATE"}


@dataclass(frozen=True)
class CanonicalMappingSpec:
    version: str
    dataset_id: str
    profile_digest: str
    semantic_mapping_digest: str
    canonical_domain: str
    fields: dict[str, dict[str, Any]]
    lineage_policy: dict[str, Any]
    spec_digest: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "dataset_id": self.dataset_id,
            "profile_digest": self.profile_digest,
            "semantic_mapping_digest": self.semantic_mapping_digest,
            "canonical_domain": self.canonical_domain,
            "fields": self.fields,
            "lineage_policy": self.lineage_policy,
            "spec_digest": self.spec_digest,
        }


class CanonicalMapper:
    def build_spec(self, profile: DatasetProfile, mapping: SemanticMapping,
                   *, roles: frozenset[str] | None = None) -> CanonicalMappingSpec:
        if mapping.dataset_id != profile.dataset_id or mapping.profile_digest != profile.profile_digest:
            raise OnboardingError("artifact_mismatch")
        if mapping.status != "SEMANTICALLY_APPROVED" or mapping.approved_domain is None:
            raise OnboardingError("mapping_not_approved")
        fields = {}
        for proposal in mapping.proposals:
            if proposal.status != "CONFIRMED" or proposal.proposed_role is None:
                continue
            role = proposal.proposed_role
            if roles is not None and role not in roles:
                continue
            if role in _DECIMAL_ROLES:
                normalization = "PARSE_DECIMAL_EXACT"
            elif role in _DATE_ROLES:
                normalization = {
                    "YYYY-MM-DD": "PARSE_ISO_DATE",
                    "DD/MM/YYYY": "PARSE_DATE_DD_MM_YYYY",
                    "MM/DD/YYYY": "PARSE_DATE_MM_DD_YYYY",
                }.get(proposal.approved_format)
                if normalization is None:
                    raise OnboardingError("date_format_required")
            else:
                normalization = "PRESERVE_TEXT"
            fields[role] = {
                "source_column": proposal.source_column,
                "column_id": proposal.column_id,
                "normalization": normalization,
            }
        spec = CanonicalMappingSpec(
            version=CANONICAL_MAPPING_VERSION,
            dataset_id=profile.dataset_id,
            profile_digest=profile.profile_digest,
            semantic_mapping_digest=mapping.mapping_digest,
            canonical_domain=mapping.approved_domain,
            fields=fields,
            lineage_policy={
                "source_row_reference": "preserved CSV record or XLSX worksheet row number",
                "record_id_algorithm": "SHA256(dataset_id:sheet:source_row_number)[:20]",
                "source_values_preserved": True,
            },
            spec_digest="",
        )
        payload = spec.to_dict()
        payload["spec_digest"] = ""
        digest = hashlib.sha256(json.dumps(
            payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        ).encode("utf-8")).hexdigest()
        return CanonicalMappingSpec(**(payload | {"spec_digest": digest}))

    def map_records(self, dataset: IngestedDataset, spec: CanonicalMappingSpec) -> tuple[dict, ...]:
        return self._map_records(dataset, spec, preserve_unavailable=False)

    def map_records_with_status(
        self, dataset: IngestedDataset, spec: CanonicalMappingSpec,
    ) -> tuple[dict, ...]:
        """Preserve per-cell unavailability for bounded analytical adapters."""
        return self._map_records(dataset, spec, preserve_unavailable=True)

    def _map_records(
        self, dataset: IngestedDataset, spec: CanonicalMappingSpec, *,
        preserve_unavailable: bool,
    ) -> tuple[dict, ...]:
        if dataset.dataset_id != spec.dataset_id:
            raise OnboardingError("artifact_mismatch")
        indexes = {name: index for index, name in enumerate(dataset.columns)}
        records = []
        if len(dataset.source_row_numbers) != len(dataset.rows):
            raise OnboardingError("artifact_mismatch")
        for source_row_number, row in zip(dataset.source_row_numbers, dataset.rows):
            fields = {}
            for role, rule in spec.fields.items():
                source_column = rule["source_column"]
                try:
                    raw = row[indexes[source_column]]
                except (KeyError, IndexError):
                    raise OnboardingError("artifact_mismatch") from None
                if preserve_unavailable:
                    if is_missing_value(raw):
                        normalized, status = None, "source_missing"
                    else:
                        try:
                            normalized = self._normalize(raw, rule["normalization"])
                        except OnboardingError as error:
                            if error.code != "canonical_parse_failure":
                                raise
                            normalized, status = None, "parsing_failed"
                        else:
                            status = "kept" if rule["normalization"] == "PRESERVE_TEXT" else "parsed"
                    fields[role] = {
                        "source_value": raw,
                        "normalized_value": normalized,
                        "status": status,
                    }
                else:
                    normalized = self._normalize(raw, rule["normalization"])
                    fields[role] = {"source_value": raw, "normalized_value": normalized}
            identity = f"{dataset.dataset_id}:{dataset.source_sheet or ''}:{source_row_number}"
            records.append({
                "canonical_record_id": "rec_" + hashlib.sha256(identity.encode("utf-8")).hexdigest()[:20],
                "canonical_domain": spec.canonical_domain,
                "canonical_fields": fields,
                "lineage": {
                    "dataset_id": dataset.dataset_id,
                    "source_sheet": dataset.source_sheet,
                    "source_row_number": source_row_number,
                },
            })
        return tuple(records)

    @staticmethod
    def _normalize(raw: str, rule: str) -> str | None:
        if is_missing_value(raw):
            return None
        if rule == "PRESERVE_TEXT":
            return raw
        if rule == "PARSE_DECIMAL_EXACT":
            value = _decimal_value(raw)
            if not isinstance(value, Decimal):
                raise OnboardingError("canonical_parse_failure")
            return format(value, "f")
        if rule == "PARSE_ISO_DATE":
            return normalize_date(raw, "YYYY-MM-DD")
        if rule in {"PARSE_DATE_DD_MM_YYYY", "PARSE_DATE_MM_DD_YYYY"}:
            date_format = "DD/MM/YYYY" if rule == "PARSE_DATE_DD_MM_YYYY" else "MM/DD/YYYY"
            return normalize_date(raw, date_format)
        raise OnboardingError("unsupported_normalization")


def normalize_date(raw: str, date_format: str) -> str:
    if date_format == "YYYY-MM-DD":
        value = _iso_date(raw)
        if value is None:
            raise OnboardingError("canonical_parse_failure")
        return value.isoformat()
    patterns = {"DD/MM/YYYY": "%d/%m/%Y", "MM/DD/YYYY": "%m/%d/%Y"}
    try:
        return datetime.strptime(raw.strip(), patterns[date_format]).date().isoformat()
    except (KeyError, ValueError):
        raise OnboardingError("canonical_parse_failure") from None
