"""Data-only contracts for local dataset onboarding."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any


INGESTION_CONTRACT_VERSION = "1.0"


class OnboardingError(Exception):
    """A controlled onboarding failure with a stable, non-sensitive code."""

    def __init__(self, code: str, message: str = "Dataset onboarding could not continue."):
        super().__init__(message)
        self.code = code
        self.safe_message = message


@dataclass(frozen=True)
class IngestionLimits:
    max_file_bytes: int = 10 * 1024 * 1024
    max_rows: int = 100_000
    max_columns: int = 64
    max_cell_chars: int = 4_096
    max_header_chars: int = 256
    max_zip_entries: int = 256
    max_zip_uncompressed_bytes: int = 50 * 1024 * 1024
    max_zip_expansion_ratio: int = 100
    max_sheets: int = 16

    def to_dict(self) -> dict[str, int]:
        return {
            "max_file_bytes": self.max_file_bytes,
            "max_rows": self.max_rows,
            "max_columns": self.max_columns,
            "max_cell_chars": self.max_cell_chars,
            "max_header_chars": self.max_header_chars,
            "max_zip_entries": self.max_zip_entries,
            "max_zip_uncompressed_bytes": self.max_zip_uncompressed_bytes,
            "max_zip_expansion_ratio": self.max_zip_expansion_ratio,
            "max_sheets": self.max_sheets,
        }


@dataclass(frozen=True)
class IngestedDataset:
    status: str
    dataset_id: str
    ingestion_run_id: str
    source_filename: str
    detected_format: str
    source_sha256: str
    byte_size: int
    ingested_at: str
    columns: tuple[str, ...]
    rows: tuple[tuple[str, ...], ...]
    source_row_numbers: tuple[int, ...]
    source_sheet: str | None = None
    encoding: str | None = None
    delimiter: str | None = None
    provenance_note: str | None = None
    ingestion_contract_version: str = INGESTION_CONTRACT_VERSION
    artifact_path: Path | None = None

    @property
    def row_count(self) -> int:
        return len(self.rows)

    @property
    def column_count(self) -> int:
        return len(self.columns)

    def to_dict(self) -> dict[str, Any]:
        """Return a bounded public manifest; rows and local paths stay private."""
        return {
            "status": self.status,
            "dataset_id": self.dataset_id,
            "ingestion_run_id": self.ingestion_run_id,
            "source_filename": self.source_filename,
            "detected_format": self.detected_format,
            "source_sha256": self.source_sha256,
            "byte_size": self.byte_size,
            "ingested_at": self.ingested_at,
            "source_sheet": self.source_sheet,
            "encoding": self.encoding,
            "delimiter": self.delimiter,
            "row_count": self.row_count,
            "column_count": self.column_count,
            "columns": list(self.columns),
            "provenance_note": self.provenance_note,
            "ingestion_contract_version": self.ingestion_contract_version,
        }
