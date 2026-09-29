"""Verified, process-local read-only copy of the approved SQLite artifact."""

from contextlib import contextmanager
from pathlib import Path
import sqlite3

from src.database.connection import DecimalSum
from src.database.loaders import APPROVED_RUN_ID, TABLES, digest, read_approved_bundle
from src.database.validation import validate_database

from .filters import predicates
from .models import blocker


DATABASE_SHA256 = "8b9536867d7e1ee2e3fd8b0040d40f5806cf6ecb8afc38491cbc058de727c744"
SCHEMA_SHA256 = "7a815fe0ffbfa68849f5e3e1394d9e9e7fb117c771c7b318c0ab50fe75a83fe5"


class ApprovedSnapshot:
    """Root is trusted application configuration, never a query parameter."""

    def __init__(self, project_root):
        self.root = Path(project_root).resolve()
        self._bundle = None
        self._validated = False

    @contextmanager
    def open(self):
        path = self.root / "data/database/financial_manager.db"
        try:
            payload = path.read_bytes()
            if digest(payload) != DATABASE_SHA256:
                blocker("snapshot_mismatch", "Database differs from the approved contract-1.0 snapshot.")
            if digest((self.root / "src/database/schema.sql").read_bytes()) != SCHEMA_SHA256:
                blocker("schema_mismatch", "DDL differs from the approved schema.")
            if self._bundle is None:
                self._bundle = read_approved_bundle(self.root)
            self._bundle.verify_unchanged()
        except (ValueError, OSError):
            # Exception bodies can contain absolute paths or private artifact
            # contents. Emit a controlled message at the source, before it
            # becomes authoritative evidence copied by the agent/manager.
            blocker("snapshot_mismatch", "The approved local data artifacts could not be read or verified.")
        # The verified bytes, rather than a later path reopen, are queried.
        # query_only protects even this disposable copy; no on-disk connection writes.
        connection = sqlite3.connect(":memory:", isolation_level=None)
        try:
            connection.deserialize(payload)
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys=ON")
            connection.execute("PRAGMA query_only=ON")
            connection.create_aggregate("DECIMAL_SUM", 1, DecimalSum)
            if not self._validated:
                try:
                    validate_database(connection, self._bundle)
                except (ValueError, sqlite3.DatabaseError):
                    blocker("snapshot_validation_failed", "The local snapshot failed integrity validation.")
                self._validated = True
            yield connection
        finally:
            connection.close()

    @staticmethod
    def read(connection, request):
        expressions = predicates(request)
        columns = [f"({sql}) AS _filter_{index}" for index, (_, sql, _) in enumerate(expressions)]
        projection = ", " + ", ".join(columns) if columns else ""
        sql = (
            "SELECT d.*, s.source_row_number, s.processed_row_number" + projection
            + " FROM " + TABLES[request.dataset] + " d JOIN source_record s"
            " ON s.record_id=d.record_id AND s.run_id=d.run_id AND s.source_id=d.source_id"
            " WHERE d.run_id=? AND d.source_id=? ORDER BY s.source_row_number, d.record_id"
        )
        parameters = [value for _, _, values in expressions for value in values]
        parameters.extend((APPROVED_RUN_ID, request.dataset))
        rows = [dict(row) for row in connection.execute(sql, parameters)]
        flags = [dict(row) for row in connection.execute(
            "SELECT * FROM data_quality_flag WHERE run_id=? AND source_id=? ORDER BY flag_row_number",
            (APPROVED_RUN_ID, request.dataset),
        )]
        run = connection.execute("SELECT * FROM processing_run WHERE run_id=?", (APPROVED_RUN_ID,)).fetchone()
        dataset = connection.execute("SELECT * FROM run_dataset WHERE run_id=? AND source_id=?",
                                     (APPROVED_RUN_ID, request.dataset)).fetchone()
        schema = connection.execute("SELECT schema_sha256 FROM schema_version WHERE version=?", (1,)).fetchone()
        metadata = {
            "database_sha256": DATABASE_SHA256, "schema_sha256": schema[0],
            **{field: run[field] for field in ("manifest_sha256", "validation_sha256", "flags_sha256")},
            **{field: dataset[field] for field in ("source_sha256", "processed_sha256")},
        }
        return rows, flags, metadata, [field for field, _, _ in expressions]
