"""Versioned local JSON artifact store and admitted dataset registry."""

from dataclasses import dataclass, replace
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Callable

from .canonical import normalize_date
from .models import IngestedDataset, OnboardingError
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

    def to_dict(self) -> dict[str, Any]:
        payload = self.__dict__.copy()
        payload["unresolved_semantics"] = list(self.unresolved_semantics)
        payload["observed_date_range"] = list(self.observed_date_range)
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
            self.load_profile(dataset_id, payload["profile_digest"])
            self.load_mapping(dataset_id, payload["mapping_version"], payload["mapping_digest"])
            if payload.get("registry_version") is not None:
                current = self.get(dataset_id)
                if (current.registry_version != payload["registry_version"]
                        or current.semantic_mapping_digest != payload["mapping_digest"]
                        or current.lifecycle_state != payload["lifecycle_state"]):
                    raise OnboardingError("artifact_mismatch")
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

    def register(self, dataset: IngestedDataset, profile: DatasetProfile,
                 mapping: SemanticMapping) -> RegistryEntry:
        if (dataset.dataset_id != profile.dataset_id or dataset.source_sha256 != profile.source_sha256
                or mapping.dataset_id != profile.dataset_id
                or mapping.profile_digest != profile.profile_digest):
            raise OnboardingError("artifact_mismatch")
        if mapping.status != "SEMANTICALLY_APPROVED" or mapping.approved_domain is None:
            raise OnboardingError("mapping_not_approved")
        self.save_profile(profile)
        self.save_mapping(mapping)
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
            parsed = [
                normalize_date(row[indexes[proposal.source_column]], proposal.approved_format)
                for row in dataset.rows
                if not is_missing_value(row[indexes[proposal.source_column]])
            ]
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
            self.load_profile(dataset_id, entry.profile_digest)
            self.load_mapping(dataset_id, entry.semantic_mapping_version,
                              entry.semantic_mapping_digest)
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

    def invalidate_mapping(self, dataset_id: str, mapping: SemanticMapping) -> RegistryEntry:
        current = self.get(dataset_id)
        if mapping.dataset_id != dataset_id or mapping.profile_digest != current.profile_digest:
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
