"""Closed canonical mapping specifications and source-row lineage."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
import hashlib
import json
from typing import Any

from .decisions import CANONICAL_DOMAINS
from .models import IngestedDataset, OnboardingError
from .preparation import PreparationManifest, preparation_digest
from .profiling import DatasetProfile, _decimal_value, _iso_date, is_missing_value
from .semantics import SEMANTIC_ROLES, SemanticMapping


CANONICAL_MAPPING_VERSION = "1.0"
PREPARED_CANONICAL_MAPPING_VERSION = "1.1"
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
    preparation_digest: str | None = None
    source_fingerprint: str | None = None
    canonical_view_digest: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "version": self.version,
            "dataset_id": self.dataset_id,
            "profile_digest": self.profile_digest,
            "semantic_mapping_digest": self.semantic_mapping_digest,
            "canonical_domain": self.canonical_domain,
            "fields": {role: dict(rule) for role, rule in self.fields.items()},
            "lineage_policy": dict(self.lineage_policy),
            "spec_digest": self.spec_digest,
        }
        if self.preparation_digest is not None:
            payload.update({
                "preparation_digest": self.preparation_digest,
                "source_fingerprint": self.source_fingerprint,
                "canonical_view_digest": self.canonical_view_digest,
            })
        return payload


class CanonicalMapper:
    def build_spec(self, profile: DatasetProfile, mapping: SemanticMapping,
                   *, roles: frozenset[str] | None = None,
                   preparation: PreparationManifest | None = None) -> CanonicalMappingSpec:
        if mapping.dataset_id != profile.dataset_id or mapping.profile_digest != profile.profile_digest:
            raise OnboardingError("artifact_mismatch")
        if mapping.status != "SEMANTICALLY_APPROVED" or mapping.approved_domain is None:
            raise OnboardingError("mapping_not_approved")
        if preparation is not None and (
            preparation_digest(preparation.to_dict()) != preparation.preparation_digest
            or preparation.dataset_id != profile.dataset_id
            or preparation.source_fingerprint != profile.source_sha256
            or preparation.profile_digest != profile.profile_digest
        ):
            raise OnboardingError("artifact_mismatch")
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
        lineage_policy = {
            "source_row_reference": "preserved CSV record or XLSX worksheet row number",
            "record_id_algorithm": "SHA256(dataset_id:sheet:source_row_number)[:20]",
            "source_values_preserved": True,
        }
        if preparation is not None:
            lineage_policy["cell_lineage"] = (
                "source column ID, raw token, and transformation identifiers"
            )
        spec = CanonicalMappingSpec(
            version=(PREPARED_CANONICAL_MAPPING_VERSION
                     if preparation is not None else CANONICAL_MAPPING_VERSION),
            dataset_id=profile.dataset_id,
            profile_digest=profile.profile_digest,
            semantic_mapping_digest=mapping.mapping_digest,
            canonical_domain=mapping.approved_domain,
            fields=fields,
            lineage_policy=lineage_policy,
            spec_digest="",
            preparation_digest=(None if preparation is None
                                else preparation.preparation_digest),
            source_fingerprint=(None if preparation is None
                                else preparation.source_fingerprint),
            canonical_view_digest=None,
        )
        payload = spec.to_dict()
        payload["spec_digest"] = ""
        if preparation is not None:
            payload["canonical_view_digest"] = None
        digest = hashlib.sha256(json.dumps(
            payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        ).encode("utf-8")).hexdigest()
        if preparation is not None:
            payload["canonical_view_digest"] = digest
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
        if (dataset.dataset_id != spec.dataset_id
                or (spec.source_fingerprint is not None
                    and dataset.source_sha256 != spec.source_fingerprint)):
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
                    if self._is_missing(raw, spec):
                        normalized, status = None, "source_missing"
                    else:
                        try:
                            normalized = self._normalize(
                                raw, rule["normalization"],
                                blank_only_missing=spec.preparation_digest is not None,
                            )
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
                    if spec.preparation_digest is not None:
                        fields[role].update({
                            "source_column_id": rule["column_id"],
                            "transformations": self._transformations(
                                rule["normalization"],
                                missing=status == "source_missing",
                                failed=status == "parsing_failed",
                            ),
                        })
                else:
                    normalized = self._normalize(
                        raw, rule["normalization"],
                        blank_only_missing=spec.preparation_digest is not None,
                    )
                    fields[role] = {
                        "source_value": raw,
                        "normalized_value": normalized,
                    }
                    if spec.preparation_digest is not None:
                        fields[role].update({
                            "source_column_id": rule["column_id"],
                            "transformations": self._transformations(
                                rule["normalization"], missing=normalized is None,
                                failed=False,
                            ),
                        })
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
            if spec.preparation_digest is not None:
                records[-1]["lineage"]["source_fingerprint"] = dataset.source_sha256
        return tuple(records)

    @staticmethod
    def _is_missing(raw: str, spec: CanonicalMappingSpec) -> bool:
        return raw.strip() == "" if spec.preparation_digest is not None else is_missing_value(raw)

    @staticmethod
    def _transformations(
        rule: str, *, missing: bool, failed: bool,
    ) -> list[dict[str, str]]:
        if missing:
            identifiers = ("BLANK_CLASSIFY", "CANONICAL_ROLE_BIND")
        elif rule == "PRESERVE_TEXT":
            identifiers = ("PRESERVE_TEXT", "CANONICAL_ROLE_BIND")
        else:
            identifiers = ("TRIM_FOR_PARSE", rule, "CANONICAL_ROLE_BIND")
        steps = []
        for identifier in identifiers:
            status = "APPLIED"
            if failed and identifier == rule:
                status = "FAILED"
            elif failed and identifier == "CANONICAL_ROLE_BIND":
                status = "NOT_APPLIED"
            steps.append({"id": identifier, "version": "1.0", "status": status})
        return steps

    @staticmethod
    def _normalize(
        raw: str, rule: str, *, blank_only_missing: bool = False,
    ) -> str | None:
        missing = raw.strip() == "" if blank_only_missing else is_missing_value(raw)
        if missing:
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


def canonical_spec_from_dict(payload: dict[str, Any]) -> CanonicalMappingSpec:
    if type(payload) is not dict or payload.get("version") not in {
        CANONICAL_MAPPING_VERSION, PREPARED_CANONICAL_MAPPING_VERSION,
    }:
        raise OnboardingError("canonical_spec_corrupt")
    canonical = dict(payload)
    expected = canonical.get("spec_digest")
    canonical["spec_digest"] = ""
    if canonical.get("version") == PREPARED_CANONICAL_MAPPING_VERSION:
        canonical["canonical_view_digest"] = None
    actual = hashlib.sha256(json.dumps(
        canonical, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")).hexdigest()
    if expected != actual:
        raise OnboardingError("canonical_spec_digest_mismatch")
    if (payload.get("version") == PREPARED_CANONICAL_MAPPING_VERSION
            and payload.get("canonical_view_digest") != expected):
        raise OnboardingError("canonical_spec_digest_mismatch")
    try:
        allowed_normalizations = {
            "PRESERVE_TEXT", "PARSE_DECIMAL_EXACT", "PARSE_ISO_DATE",
            "PARSE_DATE_DD_MM_YYYY", "PARSE_DATE_MM_DD_YYYY",
        }
        fields = payload["fields"]
        if (
            payload["canonical_domain"] not in CANONICAL_DOMAINS
            or type(fields) is not dict
            or any(
                role not in SEMANTIC_ROLES
                or type(rule) is not dict
                or set(rule) != {"source_column", "column_id", "normalization"}
                or type(rule["source_column"]) is not str
                or type(rule["column_id"]) is not str
                or rule["normalization"] not in allowed_normalizations
                for role, rule in fields.items()
            )
        ):
            raise OnboardingError("canonical_spec_corrupt")
        if payload["version"] == PREPARED_CANONICAL_MAPPING_VERSION and (
            type(payload.get("preparation_digest")) is not str
            or len(payload["preparation_digest"]) != 64
            or type(payload.get("source_fingerprint")) is not str
            or len(payload["source_fingerprint"]) != 64
        ):
            raise OnboardingError("canonical_spec_corrupt")
        return CanonicalMappingSpec(**payload)
    except (KeyError, TypeError, ValueError):
        raise OnboardingError("canonical_spec_corrupt") from None
