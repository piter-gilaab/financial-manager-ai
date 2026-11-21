"""Lossless JSON projection for authoritative application evidence."""

from dataclasses import fields, is_dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from math import isfinite
from pathlib import Path
from typing import Mapping

from pydantic import BaseModel


def to_json_safe(value):
    """Return JSON-native data without coercing Decimal to binary floats."""
    if value is None or type(value) in {str, bool, int}:
        return value
    if type(value) is float:
        if not isfinite(value):
            raise ValueError("Non-finite values are not valid API evidence.")
        return value
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise ValueError("Non-finite Decimal values are not valid API evidence.")
        return format(value, "f")
    if isinstance(value, Enum):
        return to_json_safe(value.value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Path):
        raise ValueError("Filesystem paths are private and cannot be serialized.")
    if isinstance(value, BaseModel):
        return to_json_safe(value.model_dump(mode="python"))
    if is_dataclass(value) and not isinstance(value, type):
        return {item.name: to_json_safe(getattr(value, item.name)) for item in fields(value)}
    if isinstance(value, Mapping):
        if any(type(key) is not str for key in value):
            raise ValueError("API object keys must be strings.")
        return {key: to_json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_json_safe(item) for item in value]
    raise ValueError("Unsupported private value in API projection.")

