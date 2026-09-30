"""Named sales-record contracts, without inferred company identity."""


def company_financials_record_count(core, **options):
    return core._named("company_financials_record_count", options)


def company_financials_sales_summary(core, **options):
    return core._named("company_financials_sales_summary", options)


def company_financials_sales_by_period(core, **options):
    return core._named("company_financials_sales_by_period", options)


def company_financials_sales_by_country(core, **options):
    return core._named("company_financials_sales_by_country", options)


def company_financials_sales_by_segment(core, **options):
    return core._named("company_financials_sales_by_segment", options)


def company_financials_sales_by_product(core, **options):
    return core._named("company_financials_sales_by_product", options)


def company_financials_profit_summary(core, **options):
    return core._named("company_financials_profit_summary", options)


def company_financials_discount_analysis(core, **options):
    return core._named("company_financials_discount_analysis", options)


def company_financials_units_sold_summary(core, **options):
    return core._named("company_financials_units_sold_summary", options)
