"""Closed execution adapters for approved onboarded canonical domains."""

from .binding import (
    BindingOutcome,
    BindingResult,
    BoundExecutionRequest,
    DynamicOperationBinding,
    DynamicQueryBinder,
    DynamicQueryParameters,
    DynamicQueryRequest,
    dynamic_operation_bindings,
)
from .models import (
    AdapterExecutionRequest,
    AdapterOutcome,
    AdapterValidation,
    MissingDimensionPolicy,
    PeriodGranularity,
    SalesRecordOperation,
)
from .registry import adapter_for
from .sales_record import SalesRecordExecutionAdapter

__all__ = [
    "AdapterExecutionRequest",
    "AdapterOutcome",
    "AdapterValidation",
    "BindingOutcome",
    "BindingResult",
    "BoundExecutionRequest",
    "DynamicOperationBinding",
    "DynamicQueryBinder",
    "DynamicQueryParameters",
    "DynamicQueryRequest",
    "MissingDimensionPolicy",
    "PeriodGranularity",
    "SalesRecordExecutionAdapter",
    "SalesRecordOperation",
    "adapter_for",
    "dynamic_operation_bindings",
]
