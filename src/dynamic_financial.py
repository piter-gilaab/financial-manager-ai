"""Dependency-neutral closed vocabulary for dynamic Financial Analysis."""

from enum import Enum


class SalesRecordOperation(str, Enum):
    SALES_RECORD_COUNT = "SALES_RECORD_COUNT"
    SALES_SUMMARY = "SALES_SUMMARY"
    SALES_BY_COUNTRY = "SALES_BY_COUNTRY"
    SALES_BY_PERIOD = "SALES_BY_PERIOD"
    SALES_BY_SEGMENT = "SALES_BY_SEGMENT"
    SALES_BY_PRODUCT = "SALES_BY_PRODUCT"
    PROFIT_SUMMARY = "PROFIT_SUMMARY"
    DISCOUNT_ANALYSIS = "DISCOUNT_ANALYSIS"
    UNITS_SOLD_SUMMARY = "UNITS_SOLD_SUMMARY"


class MissingDimensionPolicy(str, Enum):
    BUCKET = "BUCKET"
    EXCLUDE = "EXCLUDE"


class PeriodGranularity(str, Enum):
    MONTH = "MONTH"
    YEAR = "YEAR"


DYNAMIC_FINANCIAL_OPERATIONS = tuple(item.value for item in SalesRecordOperation)
DYNAMIC_GROUPED_OPERATIONS = frozenset({
    SalesRecordOperation.SALES_BY_COUNTRY.value,
    SalesRecordOperation.SALES_BY_PERIOD.value,
    SalesRecordOperation.SALES_BY_SEGMENT.value,
    SalesRecordOperation.SALES_BY_PRODUCT.value,
})
MISSING_DIMENSION_POLICIES = tuple(item.value for item in MissingDimensionPolicy)
PERIOD_GRANULARITIES = tuple(item.value for item in PeriodGranularity)


def dynamic_parameters_supported(operation, *, granularity=None, missing_dimension=None):
    """Validate only the existing operation/parameter compatibility contract."""
    return (
        type(operation) is str
        and operation in DYNAMIC_FINANCIAL_OPERATIONS
        and (granularity is None or (
            operation == SalesRecordOperation.SALES_BY_PERIOD.value
            and granularity in PERIOD_GRANULARITIES
        ))
        and (missing_dimension is None or (
            operation in DYNAMIC_GROUPED_OPERATIONS
            and missing_dimension in MISSING_DIMENSION_POLICIES
        ))
    )
