"""SQLite connection policy and exact validation arithmetic."""

from contextlib import contextmanager
from decimal import Decimal, Inexact, Rounded, localcontext
from pathlib import Path
import sqlite3


class DecimalSum:
    """NULL-aware exact sum; deliberately distinct from SQLite SUM."""

    def __init__(self):
        self.total = None

    def step(self, token):
        if token is None:
            return
        if not isinstance(token, str):
            raise ValueError("DECIMAL_SUM requires stored decimal TEXT")
        with localcontext() as ctx:
            ctx.prec = 60
            ctx.traps[Inexact] = ctx.traps[Rounded] = True
            value = Decimal(token)
            if not value.is_finite():
                raise ValueError("Nonfinite decimal")
            self.total = value if self.total is None else self.total + value

    def finalize(self):
        return None if self.total is None else format(self.total, "f")


@contextmanager
def connect(path, *, readonly=False):
    path = Path(path).resolve()
    connection = sqlite3.connect(
        path.as_uri() + ("?mode=ro" if readonly else "?mode=rwc"),
        uri=True, isolation_level=None,
    )
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys=ON")
    if connection.execute("PRAGMA foreign_keys").fetchone()[0] != 1:
        connection.close()
        raise RuntimeError("Foreign-key enforcement unavailable")
    connection.create_aggregate("DECIMAL_SUM", 1, DecimalSum)
    try:
        yield connection
    finally:
        if connection.in_transaction:
            connection.rollback()
        connection.close()
