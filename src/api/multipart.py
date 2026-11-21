"""Incremental, bounded multipart staging for the local upload endpoint."""

from dataclasses import dataclass
from pathlib import Path
from tempfile import NamedTemporaryFile

from fastapi import Request
from python_multipart import MultipartParser
from python_multipart.exceptions import MultipartParseError
from python_multipart.multipart import parse_options_header

from src.application import DatasetUpload, StagedDatasetUpload
from src.onboarding import OnboardingError


MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_MULTIPART_BYTES = MAX_UPLOAD_BYTES + 64 * 1024
_FIELD_LIMITS = {"sheet": 256, "provenance_note": 1000}


@dataclass(slots=True)
class _Part:
    headers: dict[bytes, bytes]
    header_name: bytearray
    header_value: bytearray
    name: str | None = None
    is_file: bool = False
    value: bytearray | None = None


class _UploadStager:
    def __init__(self, root: Path):
        self.root = root
        self.part: _Part | None = None
        self.file = None
        self.path: Path | None = None
        self.filename: str | None = None
        self.file_bytes = 0
        self.fields: dict[str, str] = {}
        self.finished = False

    def callbacks(self):
        return {
            "on_part_begin": self.on_part_begin,
            "on_part_data": self.on_part_data,
            "on_part_end": self.on_part_end,
            "on_header_field": self.on_header_field,
            "on_header_value": self.on_header_value,
            "on_header_end": self.on_header_end,
            "on_headers_finished": self.on_headers_finished,
            "on_end": self.on_end,
        }

    def on_part_begin(self):
        self.part = _Part({}, bytearray(), bytearray())

    def on_header_field(self, data, start, end):
        self._current().header_name.extend(data[start:end])

    def on_header_value(self, data, start, end):
        self._current().header_value.extend(data[start:end])

    def on_header_end(self):
        part = self._current()
        name = bytes(part.header_name).strip().lower()
        value = bytes(part.header_value).strip()
        if not name or name in part.headers:
            raise OnboardingError("malformed_multipart")
        part.headers[name] = value
        part.header_name.clear()
        part.header_value.clear()

    def on_headers_finished(self):
        part = self._current()
        disposition, options = parse_options_header(part.headers.get(b"content-disposition"))
        if disposition != b"form-data" or b"name" not in options:
            raise OnboardingError("malformed_multipart")
        try:
            part.name = options[b"name"].decode("utf-8", "strict")
        except UnicodeDecodeError:
            raise OnboardingError("malformed_multipart") from None

        if b"filename" in options:
            if part.name != "file" or self.filename is not None:
                raise OnboardingError("malformed_multipart")
            try:
                filename = options[b"filename"].decode("utf-8", "strict")
            except UnicodeDecodeError:
                raise OnboardingError("unsupported_format") from None
            extension = DatasetUpload(filename, b"").extension()
            if extension not in {".csv", ".xlsx"}:
                raise OnboardingError("unsupported_format")
            temporary = NamedTemporaryFile(
                mode="wb", suffix=extension, prefix="upload-", dir=self.root, delete=False,
            )
            self.file = temporary
            self.path = Path(temporary.name)
            self.filename = filename
            part.is_file = True
            return

        if part.name not in _FIELD_LIMITS or part.name in self.fields:
            raise OnboardingError("malformed_multipart")
        part.value = bytearray()

    def on_part_data(self, data, start, end):
        part = self._current()
        chunk = data[start:end]
        if part.is_file:
            self.file_bytes += len(chunk)
            if self.file_bytes > MAX_UPLOAD_BYTES:
                raise OnboardingError("file_too_large")
            self.file.write(chunk)
            return
        if part.value is None or part.name is None:
            raise OnboardingError("malformed_multipart")
        if len(part.value) + len(chunk) > _FIELD_LIMITS[part.name]:
            raise OnboardingError("malformed_multipart")
        part.value.extend(chunk)

    def on_part_end(self):
        part = self._current()
        if not part.is_file:
            try:
                self.fields[part.name] = bytes(part.value).decode("utf-8", "strict")
            except UnicodeDecodeError:
                raise OnboardingError("malformed_multipart") from None
        self.part = None

    def on_end(self):
        self.finished = True

    def close(self):
        if self.file is not None and not self.file.closed:
            self.file.close()

    def command(self) -> StagedDatasetUpload:
        self.close()
        if not self.finished or self.filename is None or self.path is None:
            raise OnboardingError("malformed_multipart")
        return StagedDatasetUpload(
            filename=self.filename,
            staged_path=self.path,
            sheet=self.fields.get("sheet") or None,
            provenance_note=self.fields.get("provenance_note") or None,
        )

    def _current(self) -> _Part:
        if self.part is None:
            raise OnboardingError("malformed_multipart")
        return self.part


async def stage_multipart_upload(request: Request, root: Path) -> StagedDatasetUpload:
    media_type, options = parse_options_header(request.headers.get("content-type"))
    boundary = options.get(b"boundary")
    if media_type != b"multipart/form-data" or not boundary:
        raise OnboardingError("multipart_required")

    stager = _UploadStager(root)
    parser = MultipartParser(
        boundary, stager.callbacks(), max_size=MAX_MULTIPART_BYTES,
        max_header_count=8, max_header_size=4224,
    )
    received = 0
    try:
        async for chunk in request.stream():
            received += len(chunk)
            if received > MAX_MULTIPART_BYTES:
                raise OnboardingError("file_too_large")
            if parser.write(chunk) != len(chunk):
                raise OnboardingError("file_too_large")
        parser.finalize()
        return stager.command()
    except OnboardingError:
        raise
    except (MultipartParseError, LookupError, TypeError, ValueError):
        raise OnboardingError("malformed_multipart") from None
    finally:
        stager.close()
