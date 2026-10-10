"""Deterministic structural profiling with no financial interpretation."""

from collections import Counter
from dataclasses import dataclass, replace
from datetime import date
from decimal import Decimal, InvalidOperation
import hashlib
import json
import re
from typing import Any

from .models import IngestedDataset


PROFILE_VERSION = "1.0"
_MISSING = {"", "na", "n/a", "null", "none"}
_INTEGER = re.compile(r"^[+-]?\d+$")
_PLAIN_DECIMAL = re.compile(r"^[+-]?(?:\d+\.\d+|\d+)$")
_MONEY_DECIMAL = re.compile(
    r"^\(?[+-]?(?:R\$|US\$|CA\$|[$€£])?\s*\d{1,3}(?:,\d{3})*(?:\.\d+)?\)?$",
    re.IGNORECASE,
)
_AMBIGUOUS_DATE = re.compile(r"^\d{1,2}/\d{1,2}/\d{4}$")
_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_LONG_DIGITS = re.compile(r"^\d{9,}$")
_IDENTIFIER_NAME = re.compile(r"(?:^|_)(?:id|identifier|account|tax|cpf|cnpj|email)(?:_|$)", re.IGNORECASE)


def is_missing_value(value: str) -> bool:
    return value.strip().casefold() in _MISSING


def _decimal_value(value: str) -> Decimal | None:
    stripped = value.strip()
    if not (_PLAIN_DECIMAL.fullmatch(stripped) or _MONEY_DECIMAL.fullmatch(stripped)):
        return None
    negative_parentheses = stripped.startswith("(") and stripped.endswith(")")
    normalized = stripped.strip("()").strip()
    for symbol in ("R$", "US$", "CA$", "$", "€", "£"):
        normalized = normalized.replace(symbol, "")
    normalized = normalized.replace(",", "").strip()
    try:
        parsed = Decimal(normalized)
    except InvalidOperation:
        return None
    return -parsed if negative_parentheses else parsed


def _iso_date(value: str) -> date | None:
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value.strip()):
        return None
    try:
        return date.fromisoformat(value.strip())
    except ValueError:
        return None


@dataclass(frozen=True)
class ColumnProfile:
    column_id: str
    name: str
    source_representation: str
    structural_type: str
    missing_count: int
    missing_percentage: str
    unique_count: int
    decimal_parse_success: int
    date_parse_success: int
    ambiguous_date_count: int
    numeric_min: str | None
    numeric_max: str | None
    decimal_scales: tuple[int, ...]
    date_min: str | None
    date_max: str | None
    categorical_cardinality: int
    examples: tuple[str, ...]
    frequencies: tuple[tuple[str, int], ...]
    possible_identifier: bool
    likely_sensitive: bool
    patterns: tuple[str, ...]
    formatting_observations: tuple[str, ...]
    confirmation_values: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        payload = self.__dict__.copy()
        payload["decimal_scales"] = list(self.decimal_scales)
        payload["examples"] = list(self.examples)
        payload["frequencies"] = [list(item) for item in self.frequencies]
        payload["patterns"] = list(self.patterns)
        payload["formatting_observations"] = list(self.formatting_observations)
        payload["confirmation_values"] = list(self.confirmation_values)
        return payload


@dataclass(frozen=True)
class DatasetProfile:
    status: str
    dataset_id: str
    source_sha256: str
    profile_version: str
    profile_digest: str
    row_count: int
    column_count: int
    columns: tuple[ColumnProfile, ...]
    duplicate_row_candidates: int
    currency_state: str
    bounds: dict[str, int]

    def column(self, name: str) -> ColumnProfile:
        for column in self.columns:
            if column.name == name:
                return column
        raise KeyError(name)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "dataset_id": self.dataset_id,
            "source_sha256": self.source_sha256,
            "profile_version": self.profile_version,
            "profile_digest": self.profile_digest,
            "row_count": self.row_count,
            "column_count": self.column_count,
            "columns": [column.to_dict() for column in self.columns],
            "duplicate_row_candidates": self.duplicate_row_candidates,
            "currency_state": self.currency_state,
            "bounds": dict(self.bounds),
        }


class DeterministicProfiler:
    def __init__(self, *, max_examples: int = 5, max_frequencies: int = 5):
        if max_examples < 0 or max_frequencies < 0:
            raise ValueError("Profile bounds cannot be negative.")
        self.max_examples = max_examples
        self.max_frequencies = max_frequencies

    def profile(self, dataset: IngestedDataset) -> DatasetProfile:
        return self.profile_from_rows(
            dataset_id=dataset.dataset_id,
            source_sha256=dataset.source_sha256,
            columns=dataset.columns,
            rows=dataset.rows,
        )

    def profile_from_rows(self, *, dataset_id: str, source_sha256: str,
                          columns: tuple[str, ...], rows: tuple[tuple[str, ...], ...]) -> DatasetProfile:
        column_profiles = tuple(
            self._column(dataset_id, index, name, tuple(row[index] for row in rows), len(rows))
            for index, name in enumerate(columns)
        )
        duplicates = len(rows) - len(set(rows))
        profile = DatasetProfile(
            status="PROFILED",
            dataset_id=dataset_id,
            source_sha256=source_sha256,
            profile_version=PROFILE_VERSION,
            profile_digest="",
            row_count=len(rows),
            column_count=len(columns),
            columns=column_profiles,
            duplicate_row_candidates=duplicates,
            currency_state="UNKNOWN",
            bounds={"max_examples": self.max_examples, "max_frequencies": self.max_frequencies},
        )
        digest = profile_digest(profile.to_dict())
        return replace(profile, profile_digest=digest)

    def _column(self, dataset_id: str, index: int, name: str, values: tuple[str, ...],
                row_count: int) -> ColumnProfile:
        observed = tuple(value for value in values if not is_missing_value(value))
        missing_count = row_count - len(observed)
        missing_percentage = "0.000000" if row_count == 0 else str(
            (Decimal(missing_count) * Decimal(100) / Decimal(row_count)).quantize(Decimal("0.000001"))
        )
        decimals = tuple(_decimal_value(value) for value in observed)
        parsed_decimals = tuple(value for value in decimals if value is not None)
        dates = tuple(_iso_date(value) for value in observed)
        parsed_dates = tuple(value for value in dates if value is not None)
        ambiguous_dates = sum(bool(_AMBIGUOUS_DATE.fullmatch(value.strip())) for value in observed)
        lowered = tuple(value.strip().casefold() for value in observed)
        booleans = bool(observed) and all(value in {"true", "false", "yes", "no"} for value in lowered)
        if not observed:
            structural_type = "EMPTY"
        elif len(parsed_dates) == len(observed):
            structural_type = "DATE"
        elif ambiguous_dates == len(observed):
            structural_type = "AMBIGUOUS_DATE"
        elif len(parsed_decimals) == len(observed):
            structural_type = "INTEGER" if all(_INTEGER.fullmatch(value.strip()) for value in observed) else "DECIMAL"
        elif booleans:
            structural_type = "BOOLEAN"
        elif parsed_decimals or parsed_dates or ambiguous_dates:
            structural_type = "OTHER"
        else:
            structural_type = "TEXT"

        counter = Counter(observed)
        unique_first = tuple(dict.fromkeys(observed))
        email_values = bool(observed) and any(_EMAIL.fullmatch(value.strip()) for value in observed)
        long_numbers = bool(observed) and any(_LONG_DIGITS.fullmatch(value.strip()) for value in observed)
        identifier_name = bool(_IDENTIFIER_NAME.search(re.sub(r"\W+", "_", name)))
        high_cardinality = (structural_type == "TEXT" and len(observed) >= 10
                            and Decimal(len(set(observed))) / Decimal(len(observed)) >= Decimal("0.9"))
        possible_identifier = identifier_name or email_values or long_numbers or high_cardinality
        likely_sensitive = email_values or long_numbers or identifier_name or high_cardinality
        patterns = []
        if email_values:
            patterns.append("email_like")
        if long_numbers:
            patterns.append("long_numeric_identifier_like")
        if identifier_name:
            patterns.append("identifier_name_signal")
        if high_cardinality:
            patterns.append("high_cardinality")
        if likely_sensitive:
            patterns.append("raw_samples_suppressed")
            examples: tuple[str, ...] = ()
            frequencies: tuple[tuple[str, int], ...] = ()
        else:
            examples = unique_first[:self.max_examples]
            first_position = {value: position for position, value in enumerate(unique_first)}
            ordered = sorted(counter.items(), key=lambda item: (-item[1], first_position[item[0]]))
            frequencies = tuple(ordered[:self.max_frequencies])

        formatting = []
        if any(_MONEY_DECIMAL.fullmatch(value.strip()) and not _PLAIN_DECIMAL.fullmatch(value.strip())
               for value in observed):
            formatting.append("monetary_formatting_observed")
        if any(any(symbol in value for symbol in ("$", "€", "£")) for value in observed):
            formatting.append("currency_symbol_observed")
        scales = tuple(sorted({max(0, -value.as_tuple().exponent) for value in parsed_decimals}))
        return ColumnProfile(
            column_id="col_" + hashlib.sha256(f"{dataset_id}:{index}:{name}".encode("utf-8")).hexdigest()[:16],
            name=name,
            source_representation="STRING",
            structural_type=structural_type,
            missing_count=missing_count,
            missing_percentage=missing_percentage,
            unique_count=len(set(observed)),
            decimal_parse_success=len(parsed_decimals),
            date_parse_success=len(parsed_dates),
            ambiguous_date_count=ambiguous_dates,
            numeric_min=str(min(parsed_decimals)) if parsed_decimals else None,
            numeric_max=str(max(parsed_decimals)) if parsed_decimals else None,
            decimal_scales=scales,
            date_min=min(parsed_dates).isoformat() if parsed_dates else None,
            date_max=max(parsed_dates).isoformat() if parsed_dates else None,
            categorical_cardinality=len(set(observed)),
            examples=examples,
            frequencies=frequencies,
            possible_identifier=possible_identifier,
            likely_sensitive=likely_sensitive,
            patterns=tuple(patterns),
            formatting_observations=tuple(formatting),
            confirmation_values=(unique_first if len(unique_first) <= 20 and not likely_sensitive else ()),
        )


def profile_digest(payload: dict[str, Any]) -> str:
    canonical = dict(payload)
    canonical["profile_digest"] = ""
    return hashlib.sha256(json.dumps(
        canonical, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")).hexdigest()


def profile_from_dict(payload: dict[str, Any]) -> DatasetProfile:
    """Rehydrate a validated local profile artifact without recomputing it."""
    if type(payload) is not dict or profile_digest(payload) != payload.get("profile_digest"):
        from .models import OnboardingError
        raise OnboardingError("profile_digest_mismatch")
    try:
        columns = tuple(ColumnProfile(**(item | {
            "decimal_scales": tuple(item["decimal_scales"]),
            "examples": tuple(item["examples"]),
            "frequencies": tuple(tuple(value) for value in item["frequencies"]),
            "patterns": tuple(item["patterns"]),
            "formatting_observations": tuple(item["formatting_observations"]),
            "confirmation_values": tuple(item["confirmation_values"]),
        })) for item in payload["columns"])
        return DatasetProfile(**(payload | {"columns": columns}))
    except (KeyError, TypeError, ValueError):
        from .models import OnboardingError
        raise OnboardingError("profile_corrupt") from None
