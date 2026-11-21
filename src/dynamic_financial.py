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


def dynamic_parameters_supported(
    operation, *, granularity=None, missing_dimension=None, as_of_date=None,
    allow_missing_as_of=False,
):
    """Validate only the existing operation/parameter compatibility contract."""
    from datetime import date
    from src.multidomain_financial import (
        AS_OF_OPERATIONS, GROUPED_OPERATIONS, MULTIDOMAIN_FINANCIAL_OPERATIONS,
        PERIOD_OPERATIONS, MultiDomainOperation,
    )

    allowed = (*DYNAMIC_FINANCIAL_OPERATIONS, *MULTIDOMAIN_FINANCIAL_OPERATIONS)
    multi = MultiDomainOperation(operation) if operation in MULTIDOMAIN_FINANCIAL_OPERATIONS else None
    valid_as_of = as_of_date is None
    if multi in AS_OF_OPERATIONS and allow_missing_as_of and as_of_date is None:
        valid_as_of = True
    elif multi in AS_OF_OPERATIONS:
        try:
            valid_as_of = (type(as_of_date) is str
                           and date.fromisoformat(as_of_date).isoformat() == as_of_date)
        except ValueError:
            valid_as_of = False
    return (
        type(operation) is str
        and operation in allowed
        and (granularity is None or (
            (operation == SalesRecordOperation.SALES_BY_PERIOD.value or multi in PERIOD_OPERATIONS)
            and granularity in PERIOD_GRANULARITIES
        ))
        and (missing_dimension is None or (
            (operation in DYNAMIC_GROUPED_OPERATIONS or multi in GROUPED_OPERATIONS)
            and missing_dimension in MISSING_DIMENSION_POLICIES
        ))
        and valid_as_of
    )
