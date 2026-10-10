"""Closed-ontology semantic suggestions over deterministic profiles."""

from dataclasses import dataclass, replace
import hashlib
import json
import re
from typing import Any

from src.agents.provider import ProviderLocation

from .profiling import ColumnProfile, DatasetProfile
from .prompts import SEMANTIC_PROMPT_VERSION, semantic_request


SEMANTIC_ROLES = (
    "TRANSACTION_DATE", "POSTING_DATE", "DUE_DATE", "AMOUNT", "CURRENCY", "DESCRIPTION",
    "ACCOUNT", "CATEGORY", "DEBIT_CREDIT_INDICATOR", "VOUCHER_TYPE", "DEPARTMENT", "ENTITY",
    "COUNTRY", "SEGMENT", "PRODUCT", "UNITS_SOLD", "SALES", "PROFIT", "DISCOUNT",
    "GROSS_SALES", "COGS", "SALE_PRICE", "MANUFACTURING_PRICE", "INVOICE_ID", "SUPPLIER",
    "STATUS", "ACTUAL_BUDGET_INDICATOR", "CASH_DIRECTION", "BALANCE",
)
SEMANTIC_ROLE_VALUE_KINDS = {
    "SALES": "MONETARY_AMOUNT",
    "PROFIT": "MONETARY_AMOUNT",
    "DISCOUNT": "MONETARY_AMOUNT",
    "UNITS_SOLD": "QUANTITY",
}
_ROLE_SET = frozenset(SEMANTIC_ROLES)
_PROVIDER_KEYS = {"version", "proposals"}
_PROPOSAL_KEYS = {"column_id", "status", "proposed_role", "confidence", "rationale", "alternatives"}
_CONFIDENCE = {"HIGH", "MEDIUM", "LOW", "UNKNOWN"}
_EXECUTABLE_TEXT = re.compile(
    r"(?:\b(?:select|insert|update|delete|drop|alter|create|exec|eval|import)\b|"
    r"\b(?:rm|curl|wget|bash|powershell)\b|```)", re.IGNORECASE,
)


def _normalize(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.casefold()).strip("_")


def _utf8_prefix(value: str, max_bytes: int) -> str:
    encoded = value.encode("utf-8")
    if len(encoded) <= max_bytes:
        return value
    return encoded[:max_bytes].decode("utf-8", errors="ignore")


_ALIASES = {
    "date": ("TRANSACTION_DATE", "HIGH"),
    "transaction_date": ("TRANSACTION_DATE", "HIGH"),
    "dt_mov": ("TRANSACTION_DATE", "MEDIUM"),
    "posting_date": ("POSTING_DATE", "HIGH"),
    "due_date": ("DUE_DATE", "HIGH"),
    "amount": ("AMOUNT", "HIGH"),
    "vl_liq": ("AMOUNT", "MEDIUM"),
    "currency": ("CURRENCY", "HIGH"),
    "description": ("DESCRIPTION", "HIGH"),
    "account": ("ACCOUNT", "HIGH"),
    "category": ("CATEGORY", "HIGH"),
    "dr_cr": ("DEBIT_CREDIT_INDICATOR", "HIGH"),
    "debit_credit": ("DEBIT_CREDIT_INDICATOR", "HIGH"),
    "tipo": ("DEBIT_CREDIT_INDICATOR", "LOW"),
    "voucher_type": ("VOUCHER_TYPE", "HIGH"),
    "department": ("DEPARTMENT", "HIGH"),
    "entity": ("ENTITY", "HIGH"),
    "emp": ("ENTITY", "LOW"),
    "country": ("COUNTRY", "HIGH"),
    "segment": ("SEGMENT", "HIGH"),
    "product": ("PRODUCT", "HIGH"),
    "units_sold": ("UNITS_SOLD", "HIGH"),
    "sales": ("SALES", "HIGH"),
    "sale_amount": ("SALES", "MEDIUM"),
    "profit": ("PROFIT", "HIGH"),
    "discount": ("DISCOUNT", "HIGH"),
    "gross_sales": ("GROSS_SALES", "HIGH"),
    "cogs": ("COGS", "HIGH"),
    "sale_price": ("SALE_PRICE", "HIGH"),
    "manufacturing_price": ("MANUFACTURING_PRICE", "HIGH"),
    "invoice_id": ("INVOICE_ID", "HIGH"),
    "supplier": ("SUPPLIER", "HIGH"),
    "status": ("STATUS", "HIGH"),
    "actual_budget": ("ACTUAL_BUDGET_INDICATOR", "MEDIUM"),
    "cash_direction": ("CASH_DIRECTION", "HIGH"),
    "balance": ("BALANCE", "HIGH"),
}

_NUMERIC_ROLES = {
    "AMOUNT", "UNITS_SOLD", "SALES", "PROFIT", "DISCOUNT", "GROSS_SALES", "COGS",
    "SALE_PRICE", "MANUFACTURING_PRICE", "BALANCE",
}
_DATE_ROLES = {"TRANSACTION_DATE", "POSTING_DATE", "DUE_DATE"}
_EXCLUSIVE_ROLES = _NUMERIC_ROLES | _DATE_ROLES | {
    "CURRENCY", "DEBIT_CREDIT_INDICATOR", "INVOICE_ID", "CASH_DIRECTION",
    "ACTUAL_BUDGET_INDICATOR",
}


@dataclass(frozen=True)
class SemanticProposal:
    source_column: str
    column_id: str
    proposed_role: str | None
    status: str
    confidence: str
    rationale: str
    confirmation_required: bool
    conflicts: tuple[str, ...] = ()
    alternatives: tuple[str, ...] = ()
    authority_source: str | None = None
    structural_type: str = "OTHER"
    observed_values: tuple[str, ...] = ()
    approved_format: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_column": self.source_column,
            "column_id": self.column_id,
            "proposed_role": self.proposed_role,
            "status": self.status,
            "confidence": self.confidence,
            "rationale": self.rationale,
            "confirmation_required": self.confirmation_required,
            "conflicts": list(self.conflicts),
            "alternatives": list(self.alternatives),
            "authority_source": self.authority_source,
            "structural_type": self.structural_type,
            "observed_values": list(self.observed_values),
            "approved_format": self.approved_format,
        }


@dataclass(frozen=True)
class SemanticMapping:
    status: str
    dataset_id: str
    profile_digest: str
    mapping_version: int
    mapping_digest: str
    proposals: tuple[SemanticProposal, ...]
    domain_suggestions: tuple[str, ...]
    approved_domain: str | None
    provider_status: str
    currency_state: str
    confirmed_currency: str | None
    decisions: tuple[dict[str, Any], ...] = ()

    def proposal(self, column: str) -> SemanticProposal:
        for item in self.proposals:
            if item.source_column == column:
                return item
        raise KeyError(column)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "dataset_id": self.dataset_id,
            "profile_digest": self.profile_digest,
            "mapping_version": self.mapping_version,
            "mapping_digest": self.mapping_digest,
            "proposals": [item.to_dict() for item in self.proposals],
            "domain_suggestions": list(self.domain_suggestions),
            "approved_domain": self.approved_domain,
            "provider_status": self.provider_status,
            "currency_state": self.currency_state,
            "confirmed_currency": self.confirmed_currency,
            "decisions": list(self.decisions),
        }


class SemanticMapper:
    def __init__(self, *, provider=None):
        if provider is not None and getattr(provider, "location", None) is not ProviderLocation.LOCAL:
            raise ValueError("Semantic mapping providers must be local.")
        self.provider = provider

    def suggest(self, profile: DatasetProfile) -> SemanticMapping:
        proposals = [self._deterministic(column) for column in profile.columns]
        provider_status = "NOT_USED"
        if self.provider is not None:
            try:
                output = self.provider.complete(semantic_request(self._packet(profile), SEMANTIC_ROLES))
                model_proposals = self._validate_provider(output, profile)
            except Exception:
                provider_status = "UNAVAILABLE"
            else:
                if model_proposals is None:
                    provider_status = "INVALID_OUTPUT"
                else:
                    provider_status = "ACCEPTED"
                    by_id = {item.column_id: index for index, item in enumerate(proposals)}
                    for model in model_proposals:
                        index = by_id[model["column_id"]]
                        if proposals[index].status == "UNKNOWN":
                            proposals[index] = replace(
                                proposals[index],
                                proposed_role=model["proposed_role"],
                                status=model["status"],
                                confidence=model["confidence"],
                                rationale=model["rationale"],
                                confirmation_required=model["status"] == "SUGGESTED",
                                alternatives=tuple(model["alternatives"]),
                            )
        proposals = self._detect_conflicts(proposals)
        roles = {item.proposed_role for item in proposals if item.status == "SUGGESTED"}
        domains = []
        if {"TRANSACTION_DATE", "COUNTRY", "SEGMENT", "PRODUCT", "UNITS_SOLD", "SALES", "PROFIT"} <= roles:
            domains.append("SALES_RECORD")
        if {"POSTING_DATE", "AMOUNT"} <= roles:
            domains.append("ACCOUNTING_TRANSACTION")
        if {"INVOICE_ID", "SUPPLIER", "DUE_DATE", "AMOUNT", "STATUS"} <= roles:
            domains.append("PAYABLE")
        mapping = SemanticMapping(
            status="NEEDS_CONFIRMATION",
            dataset_id=profile.dataset_id,
            profile_digest=profile.profile_digest,
            mapping_version=1,
            mapping_digest="",
            proposals=tuple(proposals),
            domain_suggestions=tuple(domains),
            approved_domain=None,
            provider_status=provider_status,
            currency_state="UNKNOWN",
            confirmed_currency=None,
        )
        return replace(mapping, mapping_digest=mapping_digest(mapping.to_dict()))

    @staticmethod
    def _deterministic(column: ColumnProfile) -> SemanticProposal:
        alias = _ALIASES.get(_normalize(column.name))
        if alias is None:
            return SemanticProposal(column.name, column.column_id, None, "UNKNOWN", "UNKNOWN",
                                    "No approved alias establishes a bounded suggestion.", False,
                                    structural_type=column.structural_type,
                                    observed_values=column.confirmation_values)
        role, confidence = alias
        compatible = not (
            role in _NUMERIC_ROLES and column.structural_type not in {"INTEGER", "DECIMAL", "EMPTY"}
            or role in _DATE_ROLES and column.structural_type not in {"DATE", "AMBIGUOUS_DATE", "EMPTY"}
        )
        if not compatible:
            return SemanticProposal(column.name, column.column_id, None, "UNKNOWN", "UNKNOWN",
                                    "The column name and structural type are incompatible.", False,
                                    alternatives=(role,), structural_type=column.structural_type,
                                    observed_values=column.confirmation_values)
        return SemanticProposal(
            column.name, column.column_id, role, "SUGGESTED", confidence,
            "A normalized source-column alias and compatible structural observation support this suggestion.",
            True, structural_type=column.structural_type,
            observed_values=column.confirmation_values,
        )

    @staticmethod
    def _packet(profile: DatasetProfile) -> dict[str, Any]:
        return {
            "dataset_id": profile.dataset_id,
            "row_count": profile.row_count,
            "column_count": profile.column_count,
            "currency_state": profile.currency_state,
            "columns": [
                {
                    "column_id": column.column_id,
                    "column_name": _utf8_prefix(column.name, 48),
                    "structural_type": column.structural_type,
                    "missing_percentage": column.missing_percentage,
                    "unique_count": column.unique_count,
                    "decimal_parse_success": column.decimal_parse_success,
                    "date_parse_success": column.date_parse_success,
                    "ambiguous_date_count": column.ambiguous_date_count,
                    "patterns": list(column.patterns),
                    "formatting_observations": list(column.formatting_observations),
                    "safe_examples": [_utf8_prefix(value, 24) for value in column.examples[:2]],
                }
                for column in profile.columns
            ],
        }

    @staticmethod
    def _validate_provider(output: str, profile: DatasetProfile) -> list[dict] | None:
        try:
            payload = json.loads(output)
        except (TypeError, ValueError):
            return None
        if type(payload) is not dict or set(payload) != _PROVIDER_KEYS or payload.get("version") != SEMANTIC_PROMPT_VERSION:
            return None
        items = payload.get("proposals")
        if type(items) is not list or len(items) > profile.column_count:
            return None
        allowed_ids = {column.column_id for column in profile.columns}
        seen = set()
        validated = []
        for item in items:
            if type(item) is not dict or set(item) != _PROPOSAL_KEYS:
                return None
            column_id = item.get("column_id")
            status = item.get("status")
            role = item.get("proposed_role")
            confidence = item.get("confidence")
            rationale = item.get("rationale")
            alternatives = item.get("alternatives")
            if column_id not in allowed_ids or column_id in seen:
                return None
            if status not in {"SUGGESTED", "UNKNOWN"}:
                return None
            if role is not None and role not in _ROLE_SET:
                return None
            if (status == "SUGGESTED") != (role is not None):
                return None
            if (confidence not in _CONFIDENCE or type(rationale) is not str or len(rationale) > 240
                    or not rationale.isprintable() or _EXECUTABLE_TEXT.search(rationale)):
                return None
            if (type(alternatives) is not list or len(alternatives) > 2
                    or len(set(alternatives)) != len(alternatives)
                    or any(role not in _ROLE_SET for role in alternatives)):
                return None
            seen.add(column_id)
            validated.append(item)
        return validated

    @staticmethod
    def _detect_conflicts(proposals: list[SemanticProposal]) -> list[SemanticProposal]:
        by_role: dict[str, list[int]] = {}
        for index, proposal in enumerate(proposals):
            if proposal.status == "SUGGESTED" and proposal.proposed_role in _EXCLUSIVE_ROLES:
                by_role.setdefault(proposal.proposed_role, []).append(index)
        for role, indexes in by_role.items():
            if len(indexes) > 1:
                columns = tuple(proposals[index].source_column for index in indexes)
                for index in indexes:
                    proposals[index] = replace(
                        proposals[index], status="CONFLICT", confidence="UNKNOWN",
                        conflicts=tuple(column for column in columns if column != proposals[index].source_column),
                        rationale=f"More than one source column proposes exclusive role {role}.",
                    )
        return proposals

def mapping_digest(payload: dict[str, Any]) -> str:
    canonical = dict(payload)
    canonical["mapping_digest"] = ""
    return hashlib.sha256(json.dumps(
        canonical, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")).hexdigest()


def mapping_from_dict(payload: dict[str, Any]) -> SemanticMapping:
    """Rehydrate a validated local mapping artifact."""
    if type(payload) is not dict or mapping_digest(payload) != payload.get("mapping_digest"):
        from .models import OnboardingError
        raise OnboardingError("mapping_digest_mismatch")
    try:
        proposals = tuple(SemanticProposal(**(item | {
            "conflicts": tuple(item["conflicts"]),
            "alternatives": tuple(item["alternatives"]),
            "observed_values": tuple(item["observed_values"]),
        })) for item in payload["proposals"])
        return SemanticMapping(**(payload | {
            "proposals": proposals,
            "domain_suggestions": tuple(payload["domain_suggestions"]),
            "decisions": tuple(payload["decisions"]),
        }))
    except (KeyError, TypeError, ValueError):
        from .models import OnboardingError
        raise OnboardingError("mapping_corrupt") from None
