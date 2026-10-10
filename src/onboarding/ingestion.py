"""Bounded, non-executing CSV and XLSX ingestion."""

import csv
from datetime import datetime, timezone
import hashlib
from io import BytesIO
import json
import os
from pathlib import Path, PurePosixPath
import stat
from tempfile import NamedTemporaryFile
from typing import Callable
from uuid import uuid4
import xml.etree.ElementTree as ET
from zipfile import BadZipFile, ZipFile

from .models import IngestedDataset, IngestionLimits, OnboardingError


_DELIMITERS = (",", ";", "\t", "|")
_MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
_DOC_REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_PKG_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"


def _utc_text(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


class SafeFileIngestor:
    """Accept local tabular bytes without interpreting financial meaning."""

    def __init__(self, onboarding_root: Path | str, *, limits: IngestionLimits | None = None,
                 clock: Callable[[], datetime] | None = None):
        self.root = Path(onboarding_root)
        self.limits = limits or IngestionLimits()
        self.clock = clock or (lambda: datetime.now(timezone.utc))

    def ingest(self, source_path: Path | str, *, sheet: str | None = None,
               provenance_note: str | None = None) -> IngestedDataset:
        source = Path(source_path)
        extension = source.suffix.lower()
        if extension not in {".csv", ".xlsx"}:
            raise OnboardingError("unsupported_format")
        data = self._read_source(source)
        if not data:
            raise OnboardingError("empty_file")
        if len(data) > self.limits.max_file_bytes:
            raise OnboardingError("file_too_large")

        if extension == ".csv":
            if data.startswith(b"PK\x03\x04"):
                raise OnboardingError("format_mismatch")
            columns, rows, encoding, delimiter = self._parse_csv(data)
            source_sheet = None
            source_row_numbers = tuple(range(2, len(rows) + 2))
            detected_format = "CSV"
        else:
            if not data.startswith(b"PK"):
                raise OnboardingError("malformed_xlsx")
            columns, rows, source_sheet, source_row_numbers = self._parse_xlsx(data, sheet)
            encoding = delimiter = None
            detected_format = "XLSX"

        digest = hashlib.sha256(data).hexdigest()
        sheet_identity = "" if source_sheet is None else f":{source_sheet}"
        identity = hashlib.sha256(f"{digest}{sheet_identity}".encode("utf-8")).hexdigest()[:20]
        dataset_id = f"ds_{identity}"
        ingestion_run_id = f"ing_{uuid4().hex}"
        ingested_at = _utc_text(self.clock())
        artifact = self._preserve_source(dataset_id, extension, data)
        result = IngestedDataset(
            status="INGESTED",
            dataset_id=dataset_id,
            ingestion_run_id=ingestion_run_id,
            source_filename=source.name,
            detected_format=detected_format,
            source_sha256=digest,
            byte_size=len(data),
            ingested_at=ingested_at,
            columns=columns,
            rows=rows,
            source_row_numbers=source_row_numbers,
            source_sheet=source_sheet,
            encoding=encoding,
            delimiter=delimiter,
            provenance_note=provenance_note,
            artifact_path=artifact,
        )
        self._write_manifest(result)
        return result

    def load(self, dataset_id: str, ingestion_run_id: str) -> IngestedDataset:
        if (not dataset_id.startswith("ds_") or len(dataset_id) != 23
                or not ingestion_run_id.startswith("ing_") or len(ingestion_run_id) != 36
                or not all(character in "0123456789abcdef" for character in dataset_id[3:])
                or not all(character in "0123456789abcdef" for character in ingestion_run_id[4:])):
            raise OnboardingError("invalid_artifact_id")
        manifest_path = self.root / "artifacts" / dataset_id / "ingestions" / f"{ingestion_run_id}.json"
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            extension = ".csv" if manifest["detected_format"] == "CSV" else ".xlsx"
            source = self.root / "artifacts" / dataset_id / "source" / f"source{extension}"
            data = self._read_source(source)
        except (FileNotFoundError, OSError, ValueError, KeyError):
            raise OnboardingError("ingestion_artifact_corrupt") from None
        if hashlib.sha256(data).hexdigest() != manifest.get("source_sha256"):
            raise OnboardingError("ingestion_artifact_corrupt")
        if extension == ".csv":
            columns, rows, encoding, delimiter = self._parse_csv(data)
            source_sheet = None
            source_row_numbers = tuple(range(2, len(rows) + 2))
        else:
            columns, rows, source_sheet, source_row_numbers = self._parse_xlsx(
                data, manifest.get("source_sheet"),
            )
            encoding = delimiter = None
        if list(columns) != manifest.get("columns") or len(rows) != manifest.get("row_count"):
            raise OnboardingError("ingestion_artifact_corrupt")
        return IngestedDataset(
            status="INGESTED", dataset_id=dataset_id, ingestion_run_id=ingestion_run_id,
            source_filename=manifest["source_filename"], detected_format=manifest["detected_format"],
            source_sha256=manifest["source_sha256"], byte_size=manifest["byte_size"],
            ingested_at=manifest["ingested_at"], columns=columns, rows=rows,
            source_row_numbers=source_row_numbers,
            source_sheet=source_sheet, encoding=encoding, delimiter=delimiter,
            provenance_note=manifest.get("provenance_note"), artifact_path=source,
        )

    def _validate_path(self, source: Path) -> None:
        try:
            metadata = source.lstat()
        except (FileNotFoundError, OSError):
            raise OnboardingError("source_unavailable") from None
        if stat.S_ISLNK(metadata.st_mode):
            raise OnboardingError("symlink_not_allowed")
        if not stat.S_ISREG(metadata.st_mode):
            raise OnboardingError("not_regular_file")
        if metadata.st_size > self.limits.max_file_bytes:
            raise OnboardingError("file_too_large")

    def _read_source(self, source: Path) -> bytes:
        """Read once from a no-follow descriptor so parsed bytes equal hashed bytes."""
        self._validate_path(source)
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
        try:
            descriptor = os.open(source, flags)
        except OSError:
            raise OnboardingError("source_unavailable") from None
        try:
            metadata = os.fstat(descriptor)
            if not stat.S_ISREG(metadata.st_mode):
                raise OnboardingError("not_regular_file")
            if metadata.st_size > self.limits.max_file_bytes:
                raise OnboardingError("file_too_large")
            chunks = bytearray()
            while len(chunks) <= self.limits.max_file_bytes:
                chunk = os.read(descriptor, min(65_536, self.limits.max_file_bytes + 1 - len(chunks)))
                if not chunk:
                    break
                chunks.extend(chunk)
            if len(chunks) > self.limits.max_file_bytes:
                raise OnboardingError("file_too_large")
            return bytes(chunks)
        finally:
            os.close(descriptor)

    def _parse_csv(self, data: bytes) -> tuple[tuple[str, ...], tuple[tuple[str, ...], ...], str, str]:
        encoding = "UTF-8-SIG" if data.startswith(b"\xef\xbb\xbf") else "UTF-8"
        try:
            text = data.decode("utf-8-sig")
        except UnicodeDecodeError:
            raise OnboardingError("invalid_encoding") from None
        candidates: list[tuple[str, list[list[str]]]] = []
        for delimiter in _DELIMITERS:
            try:
                parsed = list(csv.reader(text.splitlines(), delimiter=delimiter, strict=True))
            except csv.Error:
                continue
            if parsed and len(parsed[0]) > 1 and all(len(row) == len(parsed[0]) for row in parsed):
                candidates.append((delimiter, parsed))
        if len(candidates) > 1:
            raise OnboardingError("ambiguous_delimiter")
        if candidates:
            delimiter, parsed = candidates[0]
        else:
            try:
                parsed = list(csv.reader(text.splitlines(), delimiter=",", strict=True))
            except csv.Error:
                raise OnboardingError("malformed_csv") from None
            delimiter = ","
        return (*self._validate_table(parsed), encoding, delimiter)

    def _validate_table(self, parsed: list[list[str]]) -> tuple[tuple[str, ...], tuple[tuple[str, ...], ...]]:
        if not parsed or not parsed[0] or (len(parsed) == 1 and all(not value for value in parsed[0])):
            raise OnboardingError("empty_file")
        header = parsed[0]
        if any(not name.strip() or len(name) > self.limits.max_header_chars for name in header):
            raise OnboardingError("invalid_header")
        normalized = [name.strip().casefold() for name in header]
        if len(set(normalized)) != len(normalized):
            raise OnboardingError("duplicate_columns")
        if len(header) > self.limits.max_columns:
            raise OnboardingError("column_limit_exceeded")
        rows = parsed[1:]
        if len(rows) > self.limits.max_rows:
            raise OnboardingError("row_limit_exceeded")
        for row in rows:
            if len(row) != len(header):
                raise OnboardingError("inconsistent_rows")
            if any(len(value) > self.limits.max_cell_chars for value in row):
                raise OnboardingError("cell_limit_exceeded")
        return tuple(header), tuple(tuple(value for value in row) for row in rows)

    def _parse_xlsx(self, data: bytes, selected_sheet: str | None):
        try:
            with ZipFile(BytesIO(data)) as archive:
                self._validate_archive(archive)
                names = set(archive.namelist())
                if any(name.lower().endswith("vbaproject.bin") for name in names):
                    raise OnboardingError("macro_not_allowed")
                if any(name.startswith("xl/externalLinks/") for name in names):
                    raise OnboardingError("external_link_not_allowed")
                shared_strings = self._shared_strings(archive) if "xl/sharedStrings.xml" in names else ()
                workbook = self._xml(archive.read("xl/workbook.xml"))
                relationships = self._xml(archive.read("xl/_rels/workbook.xml.rels"))
                rel_targets = {
                    item.attrib["Id"]: item.attrib["Target"]
                    for item in relationships.findall(f"{{{_PKG_REL_NS}}}Relationship")
                    if item.attrib.get("Type", "").endswith("/worksheet")
                }
                sheets = []
                for item in workbook.findall(f".//{{{_MAIN_NS}}}sheet"):
                    relation = item.attrib.get(f"{{{_DOC_REL_NS}}}id")
                    target = rel_targets.get(relation or "")
                    if target:
                        target_path = PurePosixPath(target)
                        if target_path.is_absolute() or ".." in target_path.parts:
                            raise OnboardingError("unsafe_archive_path")
                        normalized = PurePosixPath("xl") / target_path
                        sheets.append((item.attrib.get("name", ""), normalized.as_posix()))
                if len(sheets) > self.limits.max_sheets:
                    raise OnboardingError("sheet_limit_exceeded")
                parsed_sheets = [
                    (name, target, *self._read_sheet(archive, target, shared_strings))
                    for name, target in sheets
                ]
                nonempty = [(name, target, rows, numbers)
                            for name, target, rows, numbers in parsed_sheets if rows]
                if selected_sheet is None:
                    if len(nonempty) != 1:
                        raise OnboardingError("sheet_selection_required" if nonempty else "empty_file")
                    name, _, parsed, row_numbers = nonempty[0]
                else:
                    matches = [(name, rows, numbers) for name, _, rows, numbers in parsed_sheets
                               if name == selected_sheet]
                    if not matches:
                        raise OnboardingError("sheet_not_found")
                    name, parsed, row_numbers = matches[0]
                    if not parsed:
                        raise OnboardingError("empty_file")
                columns, rows = self._validate_table(parsed)
                return columns, rows, name, tuple(row_numbers[1:])
        except OnboardingError:
            raise
        except RuntimeError:
            raise OnboardingError("encrypted_xlsx_not_allowed") from None
        except (BadZipFile, KeyError, ET.ParseError, OSError, ValueError):
            raise OnboardingError("malformed_xlsx") from None

    def _validate_archive(self, archive: ZipFile) -> None:
        entries = archive.infolist()
        if len(entries) > self.limits.max_zip_entries:
            raise OnboardingError("archive_limit_exceeded")
        total = 0
        for entry in entries:
            if entry.flag_bits & 1:
                raise OnboardingError("encrypted_xlsx_not_allowed")
            path = PurePosixPath(entry.filename)
            if path.is_absolute() or ".." in path.parts:
                raise OnboardingError("unsafe_archive_path")
            total += entry.file_size
            if total > self.limits.max_zip_uncompressed_bytes:
                raise OnboardingError("archive_limit_exceeded")
            if entry.compress_size == 0:
                if entry.file_size:
                    raise OnboardingError("archive_expansion_exceeded")
            elif entry.file_size / entry.compress_size > self.limits.max_zip_expansion_ratio:
                raise OnboardingError("archive_expansion_exceeded")

    @staticmethod
    def _xml(data: bytes) -> ET.Element:
        upper = data.upper()
        if b"<!DOCTYPE" in upper or b"<!ENTITY" in upper:
            raise OnboardingError("unsafe_xml")
        return ET.fromstring(data)

    def _shared_strings(self, archive: ZipFile) -> tuple[str, ...]:
        root = self._xml(archive.read("xl/sharedStrings.xml"))
        values = []
        for item in root.findall(f"{{{_MAIN_NS}}}si"):
            value = "".join(node.text or "" for node in item.findall(f".//{{{_MAIN_NS}}}t"))
            if len(value) > self.limits.max_cell_chars:
                raise OnboardingError("cell_limit_exceeded")
            values.append(value)
        return tuple(values)

    def _read_sheet(self, archive: ZipFile, target: str,
                    shared_strings: tuple[str, ...]) -> tuple[list[list[str]], list[int]]:
        root = self._xml(archive.read(target))
        if root.find(f".//{{{_MAIN_NS}}}f") is not None:
            raise OnboardingError("formula_not_allowed")
        rows: list[list[str]] = []
        row_numbers: list[int] = []
        for row in root.findall(f".//{{{_MAIN_NS}}}row"):
            try:
                row_number = int(row.attrib["r"])
            except (KeyError, ValueError):
                raise OnboardingError("malformed_xlsx") from None
            if (row_number < 1 or row_number > self.limits.max_rows + 1
                    or row_numbers and row_number <= row_numbers[-1]):
                raise OnboardingError("row_limit_exceeded")
            if len(rows) >= self.limits.max_rows + 1:
                raise OnboardingError("row_limit_exceeded")
            cells: list[str] = []
            expected_column = 1
            for cell in row.findall(f"{{{_MAIN_NS}}}c"):
                reference = cell.attrib.get("r", "")
                column = self._column_number(reference)
                if column > self.limits.max_columns:
                    raise OnboardingError("column_limit_exceeded")
                if column < expected_column:
                    raise OnboardingError("malformed_xlsx")
                while expected_column < column:
                    cells.append("")
                    expected_column += 1
                inline = cell.find(f"{{{_MAIN_NS}}}is/{{{_MAIN_NS}}}t")
                value = cell.find(f"{{{_MAIN_NS}}}v")
                text = inline.text if inline is not None else (value.text if value is not None else "")
                if cell.attrib.get("t") == "s":
                    try:
                        text = shared_strings[int(text or "")]
                    except (ValueError, IndexError):
                        raise OnboardingError("malformed_xlsx") from None
                cells.append(text or "")
                expected_column += 1
            rows.append(cells)
            row_numbers.append(row_number)
        return rows, row_numbers

    @staticmethod
    def _column_number(reference: str) -> int:
        letters = "".join(character for character in reference if character.isalpha())
        if not letters:
            raise ValueError("missing cell reference")
        value = 0
        for letter in letters.upper():
            value = value * 26 + ord(letter) - 64
        return value

    def _preserve_source(self, dataset_id: str, extension: str, data: bytes) -> Path:
        directory = self.root / "artifacts" / dataset_id / "source"
        directory.mkdir(parents=True, exist_ok=True)
        target = directory / f"source{extension}"
        if target.exists():
            if target.read_bytes() != data:
                raise OnboardingError("source_fingerprint_conflict")
            return target
        with NamedTemporaryFile(dir=directory, delete=False) as temporary:
            temporary.write(data)
            temporary.flush()
            os.fsync(temporary.fileno())
            temporary_path = Path(temporary.name)
        temporary_path.replace(target)
        return target

    def _write_manifest(self, result: IngestedDataset) -> None:
        directory = self.root / "artifacts" / result.dataset_id / "ingestions"
        directory.mkdir(parents=True, exist_ok=True)
        target = directory / f"{result.ingestion_run_id}.json"
        payload = result.to_dict() | {"limits": self.limits.to_dict()}
        with NamedTemporaryFile("w", encoding="utf-8", dir=directory, delete=False) as temporary:
            json.dump(payload, temporary, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            temporary.write("\n")
            temporary.flush()
            os.fsync(temporary.fileno())
            temporary_path = Path(temporary.name)
        temporary_path.replace(target)
