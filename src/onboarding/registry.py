"""Versioned local JSON artifact store and admitted dataset registry."""

from dataclasses import dataclass, replace
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Callable

from .canonical import CanonicalMappingSpec, canonical_spec_from_dict, normalize_date
from .models import IngestedDataset, OnboardingError
from .preparation import (
    DataQualityReport,
    PreparationManifest,
    preparation_from_dict,
    quality_report_from_dict,
)
from .profiling import DatasetProfile, is_missing_value, profile_from_dict
from .semantics import SemanticMapping, mapping_from_dict


REGISTRY_SCHEMA_VERSION = "1.0"
WORKFLOW_SCHEMA_VERSION = "1.0"


def _utc_text(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as temporary:
        json.dump(payload, temporary, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        temporary.write("\n")
        temporary.flush()
        os.fsync(temporary.fileno())
        temporary_path = Path(temporary.name)
    temporary_path.replace(path)


def _digest(payload: dict[str, Any], field: str) -> str:
    canonical = dict(payload)
    canonical[field] = ""
    return hashlib.sha256(json.dumps(
        canonical, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class RegistryEntry:
    dataset_id: str
    registry_schema_version: str
    registry_version: int
    entry_digest: str
    registered_at: str
    source_filename: str
    source_fingerprint: str
    source_type: str
    source_sheet: str | None
    ingestion_run_id: str
    ingestion_contract_version: str
    profile_version: str
    profile_digest: str
    semantic_mapping_version: int
    semantic_mapping_digest: str
    mapping_statuses: dict[str, str]
    unresolved_semantics: tuple[str, ...]
    quality_state: str
    currency_state: str
    confirmed_currency: str | None
    canonical_domain: str
    observed_date_range: tuple[str | None, str | None]
    row_count: int
    lifecycle_state: str
    readiness_state: str
    lineage: dict[str, Any]
    capability_readiness: dict[str, Any]
    preparation_version: str | None = None
    preparation_digest: str | None = None
    quality_report_version: str | None = None
    quality_report_digest: str | None = None
    canonical_view_digest: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = self.__dict__.copy()
        payload["unresolved_semantics"] = list(self.unresolved_semantics)
        payload["observed_date_range"] = list(self.observed_date_range)
        for key in (
            "preparation_version", "preparation_digest",
            "quality_report_version", "quality_report_digest",
            "canonical_view_digest",
        ):
            if payload[key] is None:
                payload.pop(key)
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]):
        return cls(**(payload | {
            "unresolved_semantics": tuple(payload["unresolved_semantics"]),
            "observed_date_range": tuple(payload["observed_date_range"]),
        }))


class DatasetRegistry:
    def __init__(self, onboarding_root: Path | str, *, clock: Callable[[], datetime] | None = None):
        self.root = Path(onboarding_root)
        self.clock = clock or (lambda: datetime.now(timezone.utc))

    def save_profile(self, profile: DatasetProfile) -> Path:
        target = self.root / "artifacts" / profile.dataset_id / "profiles" / f"{profile.profile_digest}.json"
        if not target.exists():
            _atomic_json(target, profile.to_dict())
        return target

    def save_mapping(self, mapping: SemanticMapping) -> Path:
        target = (self.root / "artifacts" / mapping.dataset_id / "mappings"
                  / f"{mapping.mapping_version}-{mapping.mapping_digest}.json")
        if not target.exists():
            _atomic_json(target, mapping.to_dict())
        return target

    def save_preparation(self, preparation: PreparationManifest) -> Path:
        if not re_dataset_id(preparation.dataset_id):
            raise OnboardingError("invalid_dataset_id")
        preparation_from_dict(preparation.to_dict())
        target = (self.root / "artifacts" / preparation.dataset_id / "preparations"
                  / f"{preparation.preparation_digest}.json")
        if not target.exists():
            _atomic_json(target, preparation.to_dict())
        return target

    def save_quality(self, report: DataQualityReport) -> Path:
        if not re_dataset_id(report.dataset_id):
            raise OnboardingError("invalid_dataset_id")
        quality_report_from_dict(report.to_dict())
        target = (self.root / "artifacts" / report.dataset_id / "quality"
                  / f"{report.quality_report_digest}.json")
        if not target.exists():
            _atomic_json(target, report.to_dict())
        return target

    def save_canonical(self, spec: CanonicalMappingSpec) -> Path:
        if not re_dataset_id(spec.dataset_id):
            raise OnboardingError("invalid_dataset_id")
        canonical_spec_from_dict(spec.to_dict())
        digest = spec.canonical_view_digest or spec.spec_digest
        target = (self.root / "artifacts" / spec.dataset_id / "canonical"
                  / f"{digest}.json")
        if not target.exists():
            _atomic_json(target, spec.to_dict())
        return target

    def current_dataset_ids(self) -> tuple[str, ...]:
        """Return only syntactically valid current registry identifiers, in stable order."""
        directory = self.root / "registry"
        try:
            candidates = tuple(directory.iterdir())
        except (FileNotFoundError, OSError):
            return ()
        return tuple(sorted(
            item.name for item in candidates
            if (re_dataset_id(item.name) and not item.is_symlink() and item.is_dir()
                and not (item / "current.json").is_symlink()
                and (item / "current.json").is_file())
        ))

    def current_workflow_ids(self) -> tuple[str, ...]:
        """Return safe exact identifiers for current onboarding workflows."""
        directory = self.root / "workflows"
        try:
            candidates = tuple(directory.iterdir())
        except (FileNotFoundError, OSError):
            return ()
        return tuple(sorted(
            item.name for item in candidates
            if (re_dataset_id(item.name) and not item.is_symlink() and item.is_dir()
                and not (item / "current.json").is_symlink()
                and (item / "current.json").is_file())
        ))

    def save_workflow(self, state: dict[str, Any]) -> None:
        dataset_id = state.get("dataset_id")
        if not re_dataset_id(dataset_id):
            raise OnboardingError("invalid_dataset_id")
        payload = dict(state) | {"workflow_schema_version": WORKFLOW_SCHEMA_VERSION,
                                 "workflow_digest": ""}
        payload["workflow_digest"] = _digest(payload, "workflow_digest")
        _atomic_json(self.root / "workflows" / dataset_id / "current.json", payload)
        return payload

    def workflow(self, dataset_id: str) -> dict[str, Any]:
        if not re_dataset_id(dataset_id):
            raise OnboardingError("invalid_dataset_id")
        target = self.root / "workflows" / dataset_id / "current.json"
        try:
            payload = json.loads(target.read_text(encoding="utf-8"))
            if (type(payload) is not dict or payload.get("dataset_id") != dataset_id
                    or payload.get("workflow_schema_version") != WORKFLOW_SCHEMA_VERSION):
                raise ValueError
            if _digest(payload, "workflow_digest") != payload.get("workflow_digest"):
                raise OnboardingError("workflow_digest_mismatch")
            if payload.get("lifecycle_state") not in {
                    "NEEDS_CONFIRMATION", "SEMANTICALLY_APPROVED", "REGISTERED", "READY",
                    "BLOCKED", "REJECTED"} or payload.get("readiness_state") not in {"READY", "BLOCKED"}:
                raise OnboardingError("workflow_corrupt")
            profile = self.load_profile(dataset_id, payload["profile_digest"])
            mapping = self.load_mapping(
                dataset_id, payload["mapping_version"], payload["mapping_digest"],
            )
            if mapping.profile_digest != profile.profile_digest:
                raise OnboardingError("artifact_mismatch")
            if payload.get("registry_version") is not None:
                current = self.get(dataset_id)
                if (current.registry_version != payload["registry_version"]
                        or current.semantic_mapping_digest != payload["mapping_digest"]
                        or current.lifecycle_state != payload["lifecycle_state"]):
                    raise OnboardingError("artifact_mismatch")
            if payload.get("preparation_digest") is not None:
                preparation = self.load_preparation(
                    dataset_id, payload["preparation_digest"],
                )
                if preparation.preparation_version != payload.get("preparation_version"):
                    raise OnboardingError("artifact_mismatch")
            if payload.get("quality_report_digest") is not None:
                quality = self.load_quality(dataset_id, payload["quality_report_digest"])
                if (quality.quality_report_version != payload.get("quality_report_version")
                        or quality.profile_digest != payload["profile_digest"]
                        or quality.preparation_digest != payload.get("preparation_digest")):
                    raise OnboardingError("artifact_mismatch")
                if quality.mapping_digest != payload["mapping_digest"]:
                    raise OnboardingError("quality_report_stale")
            return payload
        except FileNotFoundError:
            raise OnboardingError("dataset_not_found") from None
        except (OSError, ValueError, TypeError):
            raise OnboardingError("workflow_corrupt") from None

    def load_profile(self, dataset_id: str, digest: str) -> DatasetProfile:
        if not re_dataset_id(dataset_id):
            raise OnboardingError("invalid_dataset_id")
        target = self.root / "artifacts" / dataset_id / "profiles" / f"{digest}.json"
        try:
            profile = profile_from_dict(json.loads(target.read_text(encoding="utf-8")))
        except (FileNotFoundError, OSError, ValueError):
            raise OnboardingError("profile_corrupt") from None
        if profile.dataset_id != dataset_id or profile.profile_digest != digest:
            raise OnboardingError("artifact_mismatch")
        return profile

    def load_mapping(self, dataset_id: str, version: int, digest: str) -> SemanticMapping:
        if not re_dataset_id(dataset_id):
            raise OnboardingError("invalid_dataset_id")
        target = self.root / "artifacts" / dataset_id / "mappings" / f"{version}-{digest}.json"
        try:
            mapping = mapping_from_dict(json.loads(target.read_text(encoding="utf-8")))
        except (FileNotFoundError, OSError, ValueError):
            raise OnboardingError("mapping_corrupt") from None
        if (mapping.dataset_id != dataset_id or mapping.mapping_version != version
                or mapping.mapping_digest != digest):
            raise OnboardingError("artifact_mismatch")
        return mapping

    def load_preparation(self, dataset_id: str, digest: str) -> PreparationManifest:
        if not re_dataset_id(dataset_id):
            raise OnboardingError("invalid_dataset_id")
        target = self.root / "artifacts" / dataset_id / "preparations" / f"{digest}.json"
        try:
            preparation = preparation_from_dict(
                json.loads(target.read_text(encoding="utf-8")),
            )
        except FileNotFoundError:
            raise OnboardingError("preparation_not_found") from None
        except (OSError, ValueError, TypeError):
            raise OnboardingError("preparation_corrupt") from None
        if (preparation.dataset_id != dataset_id
                or preparation.preparation_digest != digest):
            raise OnboardingError("artifact_mismatch")
        return preparation

    def load_quality(self, dataset_id: str, digest: str) -> DataQualityReport:
        if not re_dataset_id(dataset_id):
            raise OnboardingError("invalid_dataset_id")
        target = self.root / "artifacts" / dataset_id / "quality" / f"{digest}.json"
        try:
            report = quality_report_from_dict(
                json.loads(target.read_text(encoding="utf-8")),
            )
        except FileNotFoundError:
            raise OnboardingError("quality_report_not_found") from None
        except (OSError, ValueError, TypeError):
            raise OnboardingError("quality_report_corrupt") from None
        if report.dataset_id != dataset_id or report.quality_report_digest != digest:
            raise OnboardingError("artifact_mismatch")
        return report

    def load_canonical(self, dataset_id: str, digest: str) -> CanonicalMappingSpec:
        if not re_dataset_id(dataset_id):
            raise OnboardingError("invalid_dataset_id")
        target = self.root / "artifacts" / dataset_id / "canonical" / f"{digest}.json"
        try:
            spec = canonical_spec_from_dict(
                json.loads(target.read_text(encoding="utf-8")),
            )
        except FileNotFoundError:
            raise OnboardingError("canonical_spec_not_found") from None
        except (OSError, ValueError, TypeError):
            raise OnboardingError("canonical_spec_corrupt") from None
        if (spec.dataset_id != dataset_id
                or (spec.canonical_view_digest or spec.spec_digest) != digest):
            raise OnboardingError("artifact_mismatch")
        return spec

    def register(self, dataset: IngestedDataset, profile: DatasetProfile,
                 mapping: SemanticMapping, *, preparation: PreparationManifest | None = None,
                 quality: DataQualityReport | None = None,
                 canonical: CanonicalMappingSpec | None = None) -> RegistryEntry:
        if (dataset.dataset_id != profile.dataset_id or dataset.source_sha256 != profile.source_sha256
                or mapping.dataset_id != profile.dataset_id
                or mapping.profile_digest != profile.profile_digest):
            raise OnboardingError("artifact_mismatch")
        if mapping.status != "SEMANTICALLY_APPROVED" or mapping.approved_domain is None:
            raise OnboardingError("mapping_not_approved")
        if preparation is not None and (
            preparation.dataset_id != dataset.dataset_id
            or preparation.source_fingerprint != dataset.source_sha256
            or preparation.profile_digest != profile.profile_digest
        ):
            raise OnboardingError("artifact_mismatch")
        if quality is not None and (
            preparation is None
            or quality.dataset_id != dataset.dataset_id
            or quality.preparation_digest != preparation.preparation_digest
            or quality.profile_digest != profile.profile_digest
            or quality.mapping_digest != mapping.mapping_digest
        ):
            raise OnboardingError("artifact_mismatch")
        if preparation is not None and canonical is None:
            raise OnboardingError("canonical_spec_required")
        if canonical is not None and (
            preparation is None
            or canonical.dataset_id != dataset.dataset_id
            or canonical.profile_digest != profile.profile_digest
            or canonical.semantic_mapping_digest != mapping.mapping_digest
            or canonical.preparation_digest != preparation.preparation_digest
            or canonical.source_fingerprint != dataset.source_sha256
            or canonical.canonical_view_digest != canonical.spec_digest
        ):
            raise OnboardingError("artifact_mismatch")
        self.save_profile(profile)
        self.save_mapping(mapping)
        if preparation is not None:
            self.save_preparation(preparation)
        if quality is not None:
            self.save_quality(quality)
        if canonical is not None:
            self.save_canonical(canonical)
        try:
            previous = self.get(dataset.dataset_id)
        except OnboardingError as error:
            if error.code != "dataset_not_found":
                raise
            version = 1
        else:
            version = previous.registry_version + 1
        date_values = []
        indexes = {name: index for index, name in enumerate(dataset.columns)}
        for proposal in mapping.proposals:
            if (proposal.status != "CONFIRMED"
                    or proposal.proposed_role not in {"TRANSACTION_DATE", "POSTING_DATE", "DUE_DATE"}):
                continue
            if proposal.approved_format is None:
                raise OnboardingError("date_format_required")
            parsed = []
            for row in dataset.rows:
                raw = row[indexes[proposal.source_column]]
                if is_missing_value(raw):
                    continue
                try:
                    parsed.append(normalize_date(raw, proposal.approved_format))
                except OnboardingError as error:
                    if error.code != "canonical_parse_failure":
                        raise
                    if mapping.approved_domain not in {
                        "PAYABLE", "RECEIVABLE", "CASH_TRANSACTION",
                    }:
                        raise
            if parsed:
                date_values.append((min(parsed), max(parsed)))
        observed_range = (
            min(value[0] for value in date_values) if date_values else None,
            max(value[1] for value in date_values) if date_values else None,
        )
        missing = any(column.missing_count for column in profile.columns)
        quality_state = "ISSUES_FOUND" if missing or profile.duplicate_row_candidates else "ACCEPTABLE"
        entry = RegistryEntry(
            dataset_id=dataset.dataset_id,
            registry_schema_version=REGISTRY_SCHEMA_VERSION,
            registry_version=version,
            entry_digest="",
            registered_at=_utc_text(self.clock()),
            source_filename=dataset.source_filename,
            source_fingerprint=dataset.source_sha256,
            source_type=dataset.detected_format,
            source_sheet=dataset.source_sheet,
            ingestion_run_id=dataset.ingestion_run_id,
            ingestion_contract_version=dataset.ingestion_contract_version,
            profile_version=profile.profile_version,
            profile_digest=profile.profile_digest,
            semantic_mapping_version=mapping.mapping_version,
            semantic_mapping_digest=mapping.mapping_digest,
            mapping_statuses={item.source_column: item.status for item in mapping.proposals},
            unresolved_semantics=tuple(item.source_column for item in mapping.proposals
                                       if item.status != "CONFIRMED"),
            quality_state=quality_state,
            currency_state=mapping.currency_state,
            confirmed_currency=mapping.confirmed_currency,
            canonical_domain=mapping.approved_domain,
            observed_date_range=observed_range,
            row_count=profile.row_count,
            lifecycle_state="REGISTERED",
            readiness_state="BLOCKED",
            lineage={
                "source_fingerprint": dataset.source_sha256,
                "source_sheet": dataset.source_sheet,
                "source_row_offset": 2 if dataset.detected_format == "CSV" else None,
                "source_row_reference": "preserved_source_row_number",
                "profile_digest": profile.profile_digest,
                "semantic_mapping_digest": mapping.mapping_digest,
            },
            capability_readiness={},
            preparation_version=(None if preparation is None
                                 else preparation.preparation_version),
            preparation_digest=(None if preparation is None
                                else preparation.preparation_digest),
            quality_report_version=(None if quality is None
                                    else quality.quality_report_version),
            quality_report_digest=(None if quality is None
                                   else quality.quality_report_digest),
            canonical_view_digest=(None if canonical is None
                                   else canonical.canonical_view_digest),
        )
        entry = self._seal(entry)
        directory = self.root / "registry" / dataset.dataset_id
        version_path = directory / "versions" / f"{version}.json"
        if version_path.exists():
            raise OnboardingError("registry_version_conflict")
        _atomic_json(version_path, entry.to_dict())
        _atomic_json(directory / "current.json", entry.to_dict())
        return entry

    def get(self, dataset_id: str) -> RegistryEntry:
        if not re_dataset_id(dataset_id):
            raise OnboardingError("invalid_dataset_id")
        target = self.root / "registry" / dataset_id / "current.json"
        try:
            payload = json.loads(target.read_text(encoding="utf-8"))
            if type(payload) is not dict or payload.get("registry_schema_version") != REGISTRY_SCHEMA_VERSION:
                raise ValueError
            if _digest(payload, "entry_digest") != payload.get("entry_digest"):
                raise OnboardingError("registry_digest_mismatch")
            entry = RegistryEntry.from_dict(payload)
            if (entry.dataset_id != dataset_id
                    or entry.lifecycle_state not in {"REGISTERED", "READY", "BLOCKED", "REJECTED", "NEEDS_CONFIRMATION"}
                    or entry.readiness_state not in {"READY", "BLOCKED"}):
                raise OnboardingError("registry_corrupt")
            profile = self.load_profile(dataset_id, entry.profile_digest)
            mapping = self.load_mapping(dataset_id, entry.semantic_mapping_version,
                                        entry.semantic_mapping_digest)
            if mapping.profile_digest != profile.profile_digest:
                raise OnboardingError("artifact_mismatch")
            if entry.preparation_digest is not None:
                preparation = self.load_preparation(dataset_id, entry.preparation_digest)
                if preparation.preparation_version != entry.preparation_version:
                    raise OnboardingError("artifact_mismatch")
            if entry.quality_report_digest is not None:
                quality = self.load_quality(dataset_id, entry.quality_report_digest)
                if (quality.quality_report_version != entry.quality_report_version
                        or quality.profile_digest != entry.profile_digest
                        or quality.preparation_digest != entry.preparation_digest):
                    raise OnboardingError("artifact_mismatch")
                if quality.mapping_digest != entry.semantic_mapping_digest:
                    raise OnboardingError("quality_report_stale")
            if entry.canonical_view_digest is not None:
                canonical = self.load_canonical(
                    dataset_id, entry.canonical_view_digest,
                )
                if (canonical.profile_digest != entry.profile_digest
                        or canonical.preparation_digest != entry.preparation_digest):
                    raise OnboardingError("artifact_mismatch")
                if canonical.semantic_mapping_digest != entry.semantic_mapping_digest:
                    raise OnboardingError("canonical_spec_stale")
            capabilities = entry.capability_readiness.get("capabilities", [])
            available = any(item.get("state") in {"AVAILABLE", "AVAILABLE_WITH_LIMITATIONS"}
                            for item in capabilities
                            if type(item) is dict)
            if ((entry.readiness_state == "READY" or entry.lifecycle_state == "READY") != available
                    or entry.capability_readiness
                    and (entry.capability_readiness.get("dataset_id") != dataset_id
                         or entry.capability_readiness.get("mapping_digest")
                         != entry.semantic_mapping_digest)):
                raise OnboardingError("registry_corrupt")
            return entry
        except FileNotFoundError:
            raise OnboardingError("dataset_not_found") from None
        except (OSError, ValueError, TypeError, KeyError):
            raise OnboardingError("registry_corrupt") from None

    def record_readiness(self, dataset_id: str, report) -> RegistryEntry:
        current = self.get(dataset_id)
        if report.dataset_id != dataset_id or report.mapping_digest != current.semantic_mapping_digest:
            raise OnboardingError("artifact_mismatch")
        blocked = report.all_blocked
        lifecycle_state = "BLOCKED" if blocked else "READY"
        readiness_state = "BLOCKED" if blocked else "READY"
        readiness = report.to_dict()
        if (current.lifecycle_state == lifecycle_state
                and current.readiness_state == readiness_state
                and current.capability_readiness == readiness):
            return current
        version = current.registry_version + 1
        updated = replace(
            current,
            registry_version=version,
            registered_at=_utc_text(self.clock()),
            lifecycle_state=lifecycle_state,
            readiness_state=readiness_state,
            capability_readiness=readiness,
            entry_digest="",
        )
        updated = self._seal(updated)
        directory = self.root / "registry" / dataset_id
        version_path = directory / "versions" / f"{version}.json"
        if version_path.exists():
            raise OnboardingError("registry_version_conflict")
        _atomic_json(version_path, updated.to_dict())
        _atomic_json(directory / "current.json", updated.to_dict())
        return updated

    def invalidate_mapping(self, dataset_id: str, mapping: SemanticMapping, *,
                           quality: DataQualityReport | None = None) -> RegistryEntry:
        current = self.get(dataset_id)
        if mapping.dataset_id != dataset_id or mapping.profile_digest != current.profile_digest:
            raise OnboardingError("artifact_mismatch")
        if quality is not None and (
            quality.dataset_id != dataset_id
            or quality.mapping_digest != mapping.mapping_digest
        ):
            raise OnboardingError("artifact_mismatch")
        version = current.registry_version + 1
        updated = replace(
            current,
            registry_version=version,
            registered_at=_utc_text(self.clock()),
            semantic_mapping_version=mapping.mapping_version,
            semantic_mapping_digest=mapping.mapping_digest,
            mapping_statuses={item.source_column: item.status for item in mapping.proposals},
            unresolved_semantics=tuple(item.source_column for item in mapping.proposals
                                       if item.status != "CONFIRMED"),
            lifecycle_state=mapping.status,
            readiness_state="BLOCKED",
            capability_readiness={},
            quality_report_version=(current.quality_report_version if quality is None
                                    else quality.quality_report_version),
            quality_report_digest=(current.quality_report_digest if quality is None
                                   else quality.quality_report_digest),
            canonical_view_digest=None,
            entry_digest="",
        )
        updated = self._seal(updated)
        directory = self.root / "registry" / dataset_id
        _atomic_json(directory / "versions" / f"{version}.json", updated.to_dict())
        _atomic_json(directory / "current.json", updated.to_dict())
        return updated

    @staticmethod
    def _seal(entry: RegistryEntry) -> RegistryEntry:
        return replace(entry, entry_digest=_digest(entry.to_dict(), "entry_digest"))


def re_dataset_id(value: str) -> bool:
    return type(value) is str and len(value) == 23 and value.startswith("ds_") and all(
        character in "0123456789abcdef" for character in value[3:]
    )
