"""Static allowlist for execution adapter construction."""

from pathlib import Path

from .sales_record import SalesRecordExecutionAdapter


_ADAPTERS = {"SALES_RECORD": SalesRecordExecutionAdapter}


def adapter_for(domain: str, onboarding_root: Path | str):
    adapter_type = _ADAPTERS.get(domain) if type(domain) is str else None
    return adapter_type(onboarding_root) if adapter_type is not None else None
