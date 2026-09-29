"""Build a new database atomically; never replace an existing destination."""

import argparse
import json
import os
from pathlib import Path
import sqlite3
import tempfile

from .connection import connect
from .loaders import APPROVED_RUN_ID, digest, read_approved_bundle, load_bundle, require
from .validation import validate_database

SCHEMA_PATH = Path(__file__).with_name("schema.sql")


def apply_schema(connection):
    require(connection.in_transaction, "Schema creation requires an explicit transaction")
    # executescript commits pending transactions; execute complete DDL statements
    # individually so schema AND load roll back together.
    statement = ""
    for line in SCHEMA_PATH.read_text(encoding="utf-8").splitlines(keepends=True):
        statement += line
        if sqlite3.complete_statement(statement):
            connection.execute(statement)
            statement = ""
    require(not statement.strip(), "Incomplete schema SQL")
    connection.execute("INSERT INTO schema_version(version,schema_sha256) VALUES(1,?)",
                       (digest(SCHEMA_PATH.read_bytes()),))


def build_database(project_root, database_path, *, run_id=APPROVED_RUN_ID):
    bundle = read_approved_bundle(project_root, run_id=run_id)
    destination = Path(database_path).resolve()
    require(not destination.exists(), "Refusing to replace existing database: " + str(destination))
    for folder in (bundle.root / "data/raw", bundle.root / "data/processed", bundle.root / "notebooks"):
        require(not destination.is_relative_to(folder.resolve()), "Database destination is inside protected sources")
    destination.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(prefix=".financial_manager_", suffix=".db", dir=destination.parent)
    os.close(handle)
    temporary = Path(temporary)
    published = False
    try:
        with connect(temporary) as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                apply_schema(connection)
                load_bundle(connection, bundle)
                validate_database(connection, bundle)
                bundle.verify_unchanged()
                connection.commit()
            except BaseException:
                connection.rollback()
                raise
        with connect(temporary, readonly=True) as connection:
            result = validate_database(connection, bundle)
            require(connection.execute("SELECT version,schema_sha256 FROM schema_version").fetchall()[0][:]
                    == (1, digest(SCHEMA_PATH.read_bytes())), "Schema version/hash mismatch")
        bundle.verify_unchanged()
        # Same-filesystem hard link publishes without ever replacing a racing file.
        os.link(temporary, destination)
        published = True
        with connect(destination, readonly=True) as connection:
            result = validate_database(connection, bundle)
        bundle.verify_unchanged()
        result.update(database=str(destination), database_sha256=digest(destination.read_bytes()),
                      protected_hashes_unchanged=True, disk_reload_passed=True,
                      schema_version=1, schema_sha256=digest(SCHEMA_PATH.read_bytes()))
        return result
    except BaseException:
        if published:
            destination.unlink()  # Only the new file published by this invocation.
        raise
    finally:
        temporary.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=Path("data/database/financial_manager.db"))
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    result = build_database(root, args.database)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
