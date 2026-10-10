"""Deterministic semantic, policy and execution readiness for onboarded datasets."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .profiling import DatasetProfile
from .semantics import SemanticMapping


_DYNAMIC_ANALYSIS_LIMITATIONS = (
    "Only the fixed nine-operation SALES_RECORD catalog is available.",
    "No arbitrary filters, measures, groupings or sorting are available.",
    "Dataset targeting requires an exact registered dataset_id.",
)


@dataclass(frozen=True)
class OperationReadiness:
    identifier: str
    state: str
    required_semantics: tuple[str, ...]
    reasons: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "identifier": self.identifier,
            "state": self.state,
            "required_semantics": list(self.required_semantics),
            "reasons": list(self.reasons),
        }


@dataclass(frozen=True)
class CapabilityReadiness:
    identifier: str
    state: str
    semantic_readiness: str
    policy_readiness: str
    execution_readiness: str
    reasons: tuple[str, ...]
    limitations: tuple[str, ...] = ()
    operations: tuple[OperationReadiness, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "identifier": self.identifier,
            "state": self.state,
            "semantic_readiness": self.semantic_readiness,
            "policy_readiness": self.policy_readiness,
            "execution_readiness": self.execution_readiness,
            "reasons": list(self.reasons),
            "limitations": list(self.limitations),
            "operations": [item.to_dict() for item in self.operations],
        }


@dataclass(frozen=True)
class ReadinessReport:
    version: str
    dataset_id: str
    canonical_domain: str | None
    mapping_digest: str
    currency_state: str
    confirmed_currency: str | None
    capabilities: tuple[CapabilityReadiness, ...]

    @property
    def all_blocked(self) -> bool:
        return not any(item.state in {"AVAILABLE", "AVAILABLE_WITH_LIMITATIONS"}
                       for item in self.capabilities)

    def capability(self, identifier: str) -> CapabilityReadiness:
        for item in self.capabilities:
            if item.identifier == identifier:
                return item
        raise KeyError(identifier)

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "dataset_id": self.dataset_id,
            "canonical_domain": self.canonical_domain,
            "mapping_digest": self.mapping_digest,
            "currency": {
                "state": self.currency_state,
                "code": self.confirmed_currency,
            },
            "capabilities": [item.to_dict() for item in self.capabilities],
        }


class CapabilityDiscovery:
    """The only readiness authority for new datasets; an LLM is never consulted."""

    def __init__(self, onboarding_root: Path | str | None = None, *, adapter_resolver=None,
                 binder_factory=None):
        self.root = Path(onboarding_root) if onboarding_root is not None else None
        if adapter_resolver is None:
            from src.execution.registry import adapter_for
            adapter_resolver = adapter_for
        if binder_factory is None:
            from src.execution.binding import DynamicQueryBinder
            binder_factory = DynamicQueryBinder
        self._adapter_resolver = adapter_resolver
        self._binder_factory = binder_factory

    def evaluate(self, profile: DatasetProfile, mapping: SemanticMapping) -> ReadinessReport:
        if mapping.dataset_id != profile.dataset_id or mapping.profile_digest != profile.profile_digest:
            from .models import OnboardingError
            raise OnboardingError("artifact_mismatch")
        return ReadinessReport(
            version="1.1",
            dataset_id=profile.dataset_id,
            canonical_domain=mapping.approved_domain,
            mapping_digest=mapping.mapping_digest,
            currency_state=mapping.currency_state,
            confirmed_currency=mapping.confirmed_currency,
            capabilities=(
                self._analysis(profile, mapping),
                self._anomaly(profile, mapping),
                self._forecast(mapping),
                self._retrieval(mapping),
            ),
        )

    @classmethod
    def blocked_report(cls, dataset_id: str) -> ReadinessReport:
        """Return a path-free report when authenticated artifacts cannot be read."""
        artifact_reason = ("Current registered dataset artifacts failed integrity validation.",)
        return ReadinessReport(
            version="1.1",
            dataset_id=dataset_id,
            canonical_domain=None,
            mapping_digest="",
            currency_state="UNKNOWN",
            confirmed_currency=None,
            capabilities=(
                CapabilityReadiness(
                    "FINANCIAL_ANALYSIS", "BLOCKED", "BLOCKED", "BLOCKED", "BLOCKED",
                    artifact_reason, _DYNAMIC_ANALYSIS_LIMITATIONS,
                    cls._blocked_operations(artifact_reason[0]),
                ),
                CapabilityReadiness(
                    "ANOMALY_DETECTION", "BLOCKED", "BLOCKED", "BLOCKED", "BLOCKED",
                    artifact_reason,
                ),
                CapabilityReadiness(
                    "CASH_FLOW_FORECASTING", "BLOCKED", "BLOCKED", "BLOCKED", "BLOCKED",
                    artifact_reason,
                ),
                CapabilityReadiness(
                    "DOCUMENT_RETRIEVAL", "BLOCKED", "BLOCKED", "BLOCKED", "BLOCKED",
                    artifact_reason,
                ),
            ),
        )

    def _analysis(self, profile: DatasetProfile, mapping: SemanticMapping) -> CapabilityReadiness:
        domain = mapping.approved_domain
        if domain == "ACCOUNTING_TRANSACTION":
            if (mapping.status == "SEMANTICALLY_APPROVED"
                    and self._valid_count(profile, mapping, "AMOUNT") >= 1):
                return self._blocked(
                    "FINANCIAL_ANALYSIS", "READY", "READY",
                    ("No validated dynamic execution adapter exists for ACCOUNTING_TRANSACTION.",),
                    state="BLOCKED_NOT_IMPLEMENTED",
                )
            return self._blocked(
                "FINANCIAL_ANALYSIS", "BLOCKED", "BLOCKED",
                ("Confirmed ACCOUNTING_TRANSACTION date and AMOUNT semantics with valid values are required.",),
            )
        if domain != "SALES_RECORD":
            reason = (f"Financial Analysis is not implemented for the recognized {domain or 'unapproved'} domain.",)
            return self._blocked("FINANCIAL_ANALYSIS", "BLOCKED", "BLOCKED", reason)
        if mapping.status != "SEMANTICALLY_APPROVED":
            return CapabilityReadiness(
                "FINANCIAL_ANALYSIS", "BLOCKED", "BLOCKED",
                "BLOCKED", "BLOCKED",
                ("An approved SALES_RECORD mapping is required before execution readiness can be evaluated.",),
                _DYNAMIC_ANALYSIS_LIMITATIONS,
                self._blocked_operations("Required dataset semantics are not approved."),
            )
        if self.root is None:
            return CapabilityReadiness(
                "FINANCIAL_ANALYSIS", "BLOCKED_NOT_IMPLEMENTED", "READY", "READY", "BLOCKED",
                ("Semantics are sufficient, but no generic execution adapter context was supplied for readiness evaluation.",),
                _DYNAMIC_ANALYSIS_LIMITATIONS,
                self._blocked_operations("Execution infrastructure is unavailable."),
            )
        operations = self._operation_readiness(mapping)
        if any(item.state == "SUPPORTED" for item in operations):
            return CapabilityReadiness(
                "FINANCIAL_ANALYSIS", "AVAILABLE_WITH_LIMITATIONS", "READY", "READY", "READY",
                ("At least one bounded SALES_RECORD operation passed binding and adapter validation.",),
                _DYNAMIC_ANALYSIS_LIMITATIONS,
                operations,
            )
        unavailable = any(
            any(code in reason for code in ("ADAPTER_UNAVAILABLE", "UNSUPPORTED_OPERATION"))
            for item in operations for reason in item.reasons
        )
        return CapabilityReadiness(
            "FINANCIAL_ANALYSIS",
            "BLOCKED_NOT_IMPLEMENTED" if unavailable else "BLOCKED",
            "READY",
            "READY",
            "BLOCKED",
            ("No bounded SALES_RECORD operation currently passes execution validation.",),
            _DYNAMIC_ANALYSIS_LIMITATIONS,
            operations,
        )

    def _operation_readiness(self, mapping: SemanticMapping) -> tuple[OperationReadiness, ...]:
        from src.execution.binding import DynamicQueryRequest, dynamic_operation_bindings

        binder = self._binder_factory(
            self.root,
            adapter_resolver=self._adapter_resolver,
            readiness_probe=True,
        )
        readiness = []
        for binding in dynamic_operation_bindings(mapping.approved_domain):
            identifier = binding.operation.value
            required = binding.required_roles
            bound = binder.bind(DynamicQueryRequest(
                dataset_id=mapping.dataset_id,
                operation=identifier,
            ))
            if not bound.bound:
                readiness.append(OperationReadiness(
                    identifier,
                    "UNSUPPORTED" if bound.outcome.value == "UNSUPPORTED_OPERATION" else "BLOCKED",
                    required,
                    (f"Binding validation returned {bound.outcome.value}.",),
                ))
                continue
            adapter = self._adapter_resolver(bound.request.canonical_domain, self.root)
            if adapter is None:
                readiness.append(OperationReadiness(
                    identifier, "BLOCKED", required,
                    ("Binding validation returned ADAPTER_UNAVAILABLE.",),
                ))
                continue
            validation = adapter.validate(
                bound.request.adapter_request,
                readiness_probe=True,
            )
            readiness.append(OperationReadiness(
                identifier,
                "SUPPORTED" if validation.ready else "BLOCKED",
                required,
                (() if validation.ready else (
                    f"Adapter validation returned {validation.outcome.value}.",
                )),
            ))
        return tuple(readiness)

    @staticmethod
    def _blocked_operations(reason: str) -> tuple[OperationReadiness, ...]:
        from src.execution.binding import dynamic_operation_bindings

        return tuple(OperationReadiness(
            item.operation.value, "BLOCKED", item.required_roles, (reason,),
        ) for item in dynamic_operation_bindings("SALES_RECORD")
        )

    def _anomaly(self, profile: DatasetProfile, mapping: SemanticMapping) -> CapabilityReadiness:
        confirmed_measures = [
            role for role in ("AMOUNT", "SALES", "PROFIT")
            if self._valid_count(profile, mapping, role) >= 30
        ]
        if mapping.status != "SEMANTICALLY_APPROVED" or not confirmed_measures:
            return self._blocked(
                "ANOMALY_DETECTION", "BLOCKED", "BLOCKED",
                ("A supported confirmed measure with at least 30 structurally valid numeric records is required.",),
            )
        return self._blocked(
            "ANOMALY_DETECTION", "READY", "BLOCKED",
            ("No approved screening policy applies to the confirmed domain and measure.",),
        )

    @staticmethod
    def _forecast(mapping: SemanticMapping) -> CapabilityReadiness:
        reasons = (
            "No approved actual settled cash semantics, target, perimeter, calendar/completeness contract and evaluation reserve are established.",
            "Sales, accounting debit/credit and payables are not actual cash movements.",
            "No forecasting model or execution adapter is implemented.",
        )
        if mapping.currency_state != "CONFIRMED":
            reasons += ("Currency is not confirmed for one forecast series.",)
        return CapabilityReadiness(
            "CASH_FLOW_FORECASTING", "BLOCKED", "BLOCKED", "BLOCKED", "BLOCKED", reasons,
        )

    @staticmethod
    def _retrieval(mapping: SemanticMapping) -> CapabilityReadiness:
        return CapabilityReadiness(
            "DOCUMENT_RETRIEVAL", "BLOCKED", "BLOCKED", "BLOCKED", "BLOCKED",
            ("A tabular CSV/XLSX dataset is not an approved financial document corpus.",
             "No retrieval, index or citation execution path is implemented."),
        )

    @staticmethod
    def _valid_count(profile: DatasetProfile, mapping: SemanticMapping, role: str) -> int:
        for proposal in mapping.proposals:
            if proposal.status == "CONFIRMED" and proposal.proposed_role == role:
                column = profile.column(proposal.source_column)
                return column.decimal_parse_success
        return 0

    @staticmethod
    def _blocked(identifier: str, semantic: str, policy: str, reasons: tuple[str, ...],
                 *, state: str = "BLOCKED") -> CapabilityReadiness:
        return CapabilityReadiness(identifier, state, semantic, policy, "BLOCKED", reasons)
