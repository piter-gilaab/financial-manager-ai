"""Append-oriented user semantic decisions; suggestions never approve themselves."""

from dataclasses import replace
from datetime import datetime, timezone
import re
from typing import Callable

from .models import OnboardingError
from .semantics import SEMANTIC_ROLES, SemanticMapping, SemanticProposal


CANONICAL_DOMAINS = (
    "ACCOUNTING_TRANSACTION", "SALES_RECORD", "CASH_TRANSACTION", "PAYABLE", "RECEIVABLE",
    "BUDGET_RECORD", "BALANCE_RECORD", "DOCUMENT_METADATA",
)
_REQUIRED_ROLES = {
    "SALES_RECORD": frozenset({"TRANSACTION_DATE", "SALES"}),
    "ACCOUNTING_TRANSACTION": frozenset({"POSTING_DATE", "AMOUNT"}),
    "PAYABLE": frozenset({"INVOICE_ID", "SUPPLIER", "DUE_DATE", "AMOUNT", "STATUS"}),
}
_CRITICAL_VALUE_ROLES = {"DEBIT_CREDIT_INDICATOR", "CASH_DIRECTION", "ACTUAL_BUDGET_INDICATOR"}
_ISO_CURRENCY = re.compile(r"^[A-Z]{3}$")


def _utc_text(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


class SemanticDecisionService:
    def __init__(self, *, clock: Callable[[], datetime] | None = None):
        self.clock = clock or (lambda: datetime.now(timezone.utc))

    def decide(self, mapping: SemanticMapping, *, column: str, decision: str,
               evidence: str, role: str | None = None,
               value_mapping: dict[str, str] | None = None,
               date_format: str | None = None) -> SemanticMapping:
        self._evidence(evidence)
        if decision not in {"CONFIRM", "CORRECT", "REJECT"}:
            raise OnboardingError("invalid_semantic_decision")
        try:
            current = mapping.proposal(column)
        except KeyError:
            raise OnboardingError("column_not_found") from None
        if decision == "CORRECT":
            if role not in SEMANTIC_ROLES:
                raise OnboardingError("invalid_semantic_role")
            approved_role = role
        elif decision == "CONFIRM":
            approved_role = current.proposed_role
            if approved_role is None:
                raise OnboardingError("missing_semantic_role")
            if role is not None and role != approved_role:
                raise OnboardingError("use_correct_for_changed_role")
        else:
            approved_role = None
        normalized_values = self._validate_value_mapping(
            approved_role, current.observed_values, value_mapping,
        )
        approved_format = self._validate_date_format(current, approved_role, date_format)
        new_status = "REJECTED" if decision == "REJECT" else "CONFIRMED"
        updated_proposal = replace(
            current,
            proposed_role=approved_role,
            status=new_status,
            confidence="HIGH" if approved_role is not None else "UNKNOWN",
            rationale="Explicit user semantic decision recorded.",
            confirmation_required=False,
            conflicts=(),
            alternatives=(),
            authority_source="USER",
            approved_format=approved_format,
        )
        proposals = tuple(updated_proposal if item.column_id == current.column_id else item
                          for item in mapping.proposals)
        version = mapping.mapping_version + 1
        record = {
            "decision": decision,
            "timestamp": _utc_text(self.clock()),
            "mapping_version": version,
            "source_column": current.source_column,
            "column_id": current.column_id,
            "previous_proposal": current.to_dict(),
            "approved_role": approved_role,
            "evidence": evidence,
            "value_mapping": normalized_values,
            "date_format": approved_format,
            "authority_source": "USER",
        }
        currency_state, confirmed_currency = self._currency_state(
            mapping, approved_role, normalized_values, decision,
        )
        result = replace(
            mapping,
            status=self._semantic_status(mapping.approved_domain, proposals),
            mapping_version=version,
            mapping_digest="",
            proposals=proposals,
            currency_state=currency_state,
            confirmed_currency=confirmed_currency,
            decisions=(*mapping.decisions, record),
        )
        return replace(result, mapping_digest=self._digest(result))

    def approve_domain(self, mapping: SemanticMapping, *, domain: str, evidence: str) -> SemanticMapping:
        self._evidence(evidence)
        if domain not in CANONICAL_DOMAINS:
            raise OnboardingError("invalid_canonical_domain")
        version = mapping.mapping_version + 1
        record = {
            "decision": "APPROVE_DOMAIN",
            "timestamp": _utc_text(self.clock()),
            "mapping_version": version,
            "previous_domain": mapping.approved_domain,
            "approved_domain": domain,
            "evidence": evidence,
            "authority_source": "USER",
        }
        result = replace(
            mapping,
            status=self._semantic_status(domain, mapping.proposals),
            mapping_version=version,
            mapping_digest="",
            approved_domain=domain,
            decisions=(*mapping.decisions, record),
        )
        return replace(result, mapping_digest=self._digest(result))

    def stop(self, mapping: SemanticMapping, *, reject: bool, evidence: str) -> SemanticMapping:
        self._evidence(evidence)
        version = mapping.mapping_version + 1
        record = {
            "decision": "REJECT_DATASET" if reject else "STOP",
            "timestamp": _utc_text(self.clock()),
            "mapping_version": version,
            "evidence": evidence,
            "authority_source": "USER",
        }
        result = replace(
            mapping,
            status="REJECTED" if reject else "BLOCKED",
            mapping_version=version,
            mapping_digest="",
            decisions=(*mapping.decisions, record),
        )
        return replace(result, mapping_digest=self._digest(result))

    @staticmethod
    def _evidence(evidence: str) -> None:
        if type(evidence) is not str or not evidence.strip() or len(evidence) > 1_000 or not evidence.isprintable():
            raise OnboardingError("decision_evidence_required")

    @staticmethod
    def _validate_value_mapping(role: str | None, observed_values: tuple[str, ...],
                                value_mapping: dict[str, str] | None):
        if value_mapping is None:
            if role in _CRITICAL_VALUE_ROLES:
                raise OnboardingError("critical_value_mapping_required")
            return None
        if (type(value_mapping) is not dict or not value_mapping or len(value_mapping) > 20
                or any(type(key) is not str or type(value) is not str or not key or not value
                       or len(key) > 100 or len(value) > 100
                       for key, value in value_mapping.items())):
            raise OnboardingError("invalid_value_mapping")
        normalized = dict(sorted(value_mapping.items()))
        if role == "DEBIT_CREDIT_INDICATOR" and set(normalized.values()) - {"DEBIT", "CREDIT"}:
            raise OnboardingError("invalid_value_mapping")
        if role == "CASH_DIRECTION" and set(normalized.values()) - {"INFLOW", "OUTFLOW"}:
            raise OnboardingError("invalid_value_mapping")
        if role == "ACTUAL_BUDGET_INDICATOR" and set(normalized.values()) - {"ACTUAL", "BUDGET"}:
            raise OnboardingError("invalid_value_mapping")
        if role == "CURRENCY":
            if any(not _ISO_CURRENCY.fullmatch(source) or not _ISO_CURRENCY.fullmatch(target)
                   for source, target in normalized.items()):
                raise OnboardingError("invalid_currency_evidence")
        if role in {*_CRITICAL_VALUE_ROLES, "CURRENCY"}:
            if not observed_values:
                raise OnboardingError("critical_values_unavailable")
            if set(normalized) != set(observed_values):
                raise OnboardingError("incomplete_value_mapping")
        return normalized

    @staticmethod
    def _validate_date_format(current: SemanticProposal, role: str | None,
                              date_format: str | None) -> str | None:
        if role not in {"TRANSACTION_DATE", "POSTING_DATE", "DUE_DATE"}:
            if date_format is not None:
                raise OnboardingError("date_format_not_applicable")
            return None
        if current.structural_type == "AMBIGUOUS_DATE":
            if date_format not in {"DD/MM/YYYY", "MM/DD/YYYY"}:
                raise OnboardingError("date_format_required")
            return date_format
        if date_format not in {None, "YYYY-MM-DD"}:
            raise OnboardingError("invalid_date_format")
        return "YYYY-MM-DD"

    @staticmethod
    def _currency_state(mapping: SemanticMapping, role: str | None,
                        values: dict[str, str] | None, decision: str):
        if role != "CURRENCY":
            return mapping.currency_state, mapping.confirmed_currency
        if decision == "REJECT" or not values:
            return "UNKNOWN", None
        codes = set(values.values())
        return ("CONFIRMED", next(iter(codes))) if len(codes) == 1 else ("CONFIRMED_MULTIPLE", None)

    @staticmethod
    def _semantic_status(domain: str | None, proposals: tuple[SemanticProposal, ...]) -> str:
        if domain is None:
            return "NEEDS_CONFIRMATION"
        required = _REQUIRED_ROLES.get(domain)
        if required is None:
            return "NEEDS_CONFIRMATION"
        confirmed = {item.proposed_role for item in proposals if item.status == "CONFIRMED"}
        return "SEMANTICALLY_APPROVED" if required <= confirmed else "NEEDS_CONFIRMATION"

    @staticmethod
    def _digest(mapping: SemanticMapping) -> str:
        from .semantics import mapping_digest
        return mapping_digest(mapping.to_dict())
