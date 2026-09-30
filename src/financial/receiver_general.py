"""Named Receiver General contracts; all rules live in the common core."""


def receiver_general_record_count(core, **options):
    return core._named("receiver_general_record_count", options)


def receiver_general_amount_summary(core, **options):
    return core._named("receiver_general_amount_summary", options)


def receiver_general_amount_by_debit_credit(core, **options):
    return core._named("receiver_general_amount_by_debit_credit", options)


def receiver_general_amount_by_voucher_type(core, **options):
    return core._named("receiver_general_amount_by_voucher_type", options)


def receiver_general_amount_by_department(core, **options):
    return core._named("receiver_general_amount_by_department", options)


def receiver_general_amount_by_period(core, **options):
    return core._named("receiver_general_amount_by_period", options)


def receiver_general_accounting_dimension_summary(core, **options):
    return core._named("receiver_general_accounting_dimension_summary", options)


def receiver_general_extreme_amount_records(core, **options):
    return core._named("receiver_general_extreme_amount_records", options)
