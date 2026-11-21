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
from .multidomain import (
    CashTransactionExecutionAdapter,
    PayableExecutionAdapter,
    ReceivableExecutionAdapter,
)
from src.multidomain_financial import MultiDomainOperation

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
    "MultiDomainOperation",
    "PeriodGranularity",
    "PayableExecutionAdapter",
    "ReceivableExecutionAdapter",
    "CashTransactionExecutionAdapter",
    "SalesRecordExecutionAdapter",
    "SalesRecordOperation",
    "adapter_for",
    "dynamic_operation_bindings",
]
