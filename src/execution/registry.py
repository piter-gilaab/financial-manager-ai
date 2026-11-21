"""Static allowlist for execution adapter construction."""

from pathlib import Path

from .sales_record import SalesRecordExecutionAdapter
from .multidomain import (
    CashTransactionExecutionAdapter,
    PayableExecutionAdapter,
    ReceivableExecutionAdapter,
)


_ADAPTERS = {
    "SALES_RECORD": SalesRecordExecutionAdapter,
    "PAYABLE": PayableExecutionAdapter,
    "RECEIVABLE": ReceivableExecutionAdapter,
    "CASH_TRANSACTION": CashTransactionExecutionAdapter,
}


def adapter_for(domain: str, onboarding_root: Path | str):
    adapter_type = _ADAPTERS.get(domain) if type(domain) is str else None
    return adapter_type(onboarding_root) if adapter_type is not None else None
