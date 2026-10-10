"""Thin workflow facade over ingestion, profiling, decisions, registry and readiness."""

from datetime import datetime, timezone
from pathlib import Path

from .decisions import SemanticDecisionService
from .ingestion import SafeFileIngestor
from .models import IngestionLimits, OnboardingError
from .profiling import DeterministicProfiler
from .readiness import CapabilityDiscovery
from .registry import DatasetRegistry
from .semantics import SemanticMapper


class OnboardingManager:
    def __init__(self, onboarding_root: Path | str = Path("data/onboarding"), *,
                 semantic_provider=None, limits: IngestionLimits | None = None, clock=None):
        self.root = Path(onboarding_root)
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self._ingestor = SafeFileIngestor(self.root, limits=limits, clock=self.clock)
        self._profiler = DeterministicProfiler()
        self._mapper = SemanticMapper(provider=semantic_provider)
        self._decisions = SemanticDecisionService(clock=self.clock)
        self._registry = DatasetRegistry(self.root, clock=self.clock)
        self._discovery = CapabilityDiscovery(self.root)

    def add(self, source_path: Path | str, *, sheet: str | None = None,
            provenance_note: str | None = None) -> dict:
        dataset = self._ingestor.ingest(source_path, sheet=sheet, provenance_note=provenance_note)
        profile = self._profiler.profile(dataset)
        mapping = self._mapper.suggest(profile)
        self._registry.save_profile(profile)
        self._registry.save_mapping(mapping)
        state = {
            "dataset_id": dataset.dataset_id,
            "lifecycle_state": "NEEDS_CONFIRMATION",
            "source_filename": dataset.source_filename,
            "source_type": dataset.detected_format,
            "source_sheet": dataset.source_sheet,
            "source_fingerprint": dataset.source_sha256,
            "ingestion_run_id": dataset.ingestion_run_id,
            "row_count": profile.row_count,
            "column_count": profile.column_count,
            "profile_version": profile.profile_version,
            "profile_digest": profile.profile_digest,
            "mapping_version": mapping.mapping_version,
            "mapping_digest": mapping.mapping_digest,
            "confirmation_required_count": sum(item.confirmation_required for item in mapping.proposals),
            "approved_domain": mapping.approved_domain,
            "currency_state": mapping.currency_state,
            "readiness_state": "BLOCKED",
            "registry_version": None,
        }
        self._write_state(state)
        return dict(state)

    def status(self, dataset_id: str) -> dict:
        return dict(self._state(dataset_id))

    def profile(self, dataset_id: str) -> dict:
        return self._profile(dataset_id).to_dict()

    def mappings(self, dataset_id: str) -> dict:
        return self._mapping(dataset_id).to_dict()

    def confirm(self, dataset_id: str, column: str, role: str, *, evidence: str,
                value_mapping: dict[str, str] | None = None,
                date_format: str | None = None) -> dict:
        mapping = self._mapping(dataset_id)
        try:
            current = mapping.proposal(column)
        except KeyError:
            raise OnboardingError("column_not_found") from None
        decision = "CONFIRM" if current.proposed_role == role else "CORRECT"
        updated = self._decisions.decide(
            mapping, column=column, decision=decision, role=role, evidence=evidence,
            value_mapping=value_mapping, date_format=date_format,
        )
        return self._after_mapping(dataset_id, updated)

    def reject(self, dataset_id: str, column: str, *, evidence: str) -> dict:
        updated = self._decisions.decide(
            self._mapping(dataset_id), column=column, decision="REJECT", evidence=evidence,
        )
        return self._after_mapping(dataset_id, updated)

    def confirm_domain(self, dataset_id: str, domain: str, *, evidence: str) -> dict:
        updated = self._decisions.approve_domain(
            self._mapping(dataset_id), domain=domain, evidence=evidence,
        )
        return self._after_mapping(dataset_id, updated)

    def stop(self, dataset_id: str, *, reject: bool, evidence: str) -> dict:
        updated = self._decisions.stop(self._mapping(dataset_id), reject=reject, evidence=evidence)
        return self._after_mapping(dataset_id, updated)

    def capabilities(self, dataset_id: str) -> dict:
        try:
            state = self._state(dataset_id)
            profile = self._registry.load_profile(dataset_id, state["profile_digest"])
            mapping = self._registry.load_mapping(
                dataset_id, state["mapping_version"], state["mapping_digest"],
            )
            report = self._discovery.evaluate(profile, mapping)
        except OnboardingError as error:
            if error.code in {"invalid_dataset_id", "dataset_not_found"}:
                raise
            report = self._discovery.blocked_report(dataset_id)
        else:
            if mapping.status == "SEMANTICALLY_APPROVED":
                final = self._registry.record_readiness(dataset_id, report)
                if (state.get("registry_version") != final.registry_version
                        or state.get("lifecycle_state") != final.lifecycle_state
                        or state.get("readiness_state") != final.readiness_state):
                    state.update({
                        "lifecycle_state": final.lifecycle_state,
                        "readiness_state": final.readiness_state,
                        "registry_version": final.registry_version,
                    })
                    self._write_state(state)
        return report.to_dict()

    def financial_analysis_readiness(self, dataset_id: str) -> dict:
        """Return the dataset-scoped Financial Analysis projection."""
        report = self.capabilities(dataset_id)
        analysis = next(
            item for item in report["capabilities"]
            if item["identifier"] == "FINANCIAL_ANALYSIS"
        )
        return {
            "dataset_id": report["dataset_id"],
            "canonical_domain": report["canonical_domain"],
            "currency": report["currency"],
            **analysis,
        }

    @staticmethod
    def blocked_financial_analysis_readiness() -> dict:
        """Return the controlled Manager projection for an unresolved dataset."""
        report = CapabilityDiscovery.blocked_report("").to_dict()
        analysis = next(
            item for item in report["capabilities"]
            if item["identifier"] == "FINANCIAL_ANALYSIS"
        )
        return {
            "dataset_id": None,
            "canonical_domain": None,
            "currency": report["currency"],
            **analysis,
        }

    def _after_mapping(self, dataset_id: str, mapping) -> dict:
        self._registry.save_mapping(mapping)
        state = self._state(dataset_id)
        state.update({
            "lifecycle_state": mapping.status,
            "mapping_version": mapping.mapping_version,
            "mapping_digest": mapping.mapping_digest,
            "confirmation_required_count": sum(item.confirmation_required for item in mapping.proposals),
            "approved_domain": mapping.approved_domain,
            "currency_state": mapping.currency_state,
            "readiness_state": "BLOCKED",
        })
        if mapping.status == "SEMANTICALLY_APPROVED":
            profile = self._profile(dataset_id)
            dataset = self._ingestor.load(dataset_id, state["ingestion_run_id"])
            registered = self._registry.register(dataset, profile, mapping)
            # Binding authenticates workflow-to-registry identity. Publish the
            # REGISTERED transition before readiness probes use that same seam.
            state.update({
                "lifecycle_state": registered.lifecycle_state,
                "readiness_state": registered.readiness_state,
                "registry_version": registered.registry_version,
            })
            self._write_state(state)
            report = self._discovery.evaluate(profile, mapping)
            final = self._registry.record_readiness(dataset_id, report)
            state.update({
                "lifecycle_state": final.lifecycle_state,
                "readiness_state": final.readiness_state,
                "registry_version": final.registry_version,
            })
        elif state.get("registry_version") is not None:
            invalidated = self._registry.invalidate_mapping(dataset_id, mapping)
            state["registry_version"] = invalidated.registry_version
        self._write_state(state)
        return dict(state)

    def _state(self, dataset_id: str) -> dict:
        return self._registry.workflow(dataset_id)

    def _profile(self, dataset_id: str):
        state = self._state(dataset_id)
        return self._registry.load_profile(dataset_id, state["profile_digest"])

    def _mapping(self, dataset_id: str):
        state = self._state(dataset_id)
        return self._registry.load_mapping(
            dataset_id, state["mapping_version"], state["mapping_digest"],
        )

    def _write_state(self, state: dict) -> None:
        stored = self._registry.save_workflow(state)
        state.clear()
        state.update(stored)
