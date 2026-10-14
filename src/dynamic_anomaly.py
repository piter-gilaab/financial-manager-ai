"""Dependency-neutral closed catalog for dynamic anomaly mediation."""

from enum import Enum


class DynamicAnomalyOperation(str, Enum):
    SALES_ANOMALY_SCREEN = "SALES_ANOMALY_SCREEN"
    PROFIT_ANOMALY_SCREEN = "PROFIT_ANOMALY_SCREEN"


DYNAMIC_ANOMALY_OPERATIONS = tuple(item.value for item in DynamicAnomalyOperation)
