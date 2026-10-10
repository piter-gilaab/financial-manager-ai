"""Synthetic, data-only fixtures for Dynamic Data Onboarding tests."""

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


def write_csv(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def write_xlsx(path: Path, *, sheets: dict[str, list[list[str]]], formula: bool = False,
               external_link: bool = False, macro: bool = False,
               shared_strings: bool = False,
               row_numbers: dict[str, list[int]] | None = None,
               cell_reference_override: str | None = None) -> Path:
    """Write the small Open XML subset accepted by the test parser."""
    names = list(sheets)
    workbook_sheets = "".join(
        f'<sheet name="{name}" sheetId="{index}" r:id="rId{index}"/>'
        for index, name in enumerate(names, start=1)
    )
    workbook = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f'<sheets>{workbook_sheets}</sheets></workbook>'
    )
    relationships = "".join(
        '<Relationship '
        f'Id="rId{index}" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
        f'Target="worksheets/sheet{index}.xml"/>'
        for index in range(1, len(names) + 1)
    )
    workbook_rels = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        f'{relationships}</Relationships>'
    )
    with ZipFile(path, "w", ZIP_DEFLATED) as archive:
        archive.writestr("xl/workbook.xml", workbook)
        archive.writestr("xl/_rels/workbook.xml.rels", workbook_rels)
        shared_values = []
        if shared_strings:
            shared_values = list(dict.fromkeys(value for rows in sheets.values() for row in rows for value in row))
            archive.writestr(
                "xl/sharedStrings.xml",
                '<?xml version="1.0" encoding="UTF-8"?>'
                '<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
                + "".join(f"<si><t>{value}</t></si>" for value in shared_values) + "</sst>",
            )
        for index, (sheet_name, rows) in enumerate(sheets.items(), start=1):
            encoded_rows = []
            numbers = ((row_numbers or {}).get(sheet_name) or list(range(1, len(rows) + 1)))
            for row_index, (row_number, row) in enumerate(zip(numbers, rows), start=1):
                encoded_cells = []
                for column_number, value in enumerate(row, start=1):
                    column = chr(64 + column_number)
                    reference = (cell_reference_override if cell_reference_override is not None
                                 and row_index == 1 and column_number == 1
                                 else f"{column}{row_number}")
                    if formula and row_index == 2 and column_number == 1:
                        content = f"<f>{value}</f><v>2</v>"
                    elif shared_strings:
                        content = f"<v>{shared_values.index(value)}</v>"
                    else:
                        content = f'<is><t>{value}</t></is>'
                    encoded_cells.append(
                        f'<c r="{reference}" t="{"s" if shared_strings else "inlineStr"}">{content}</c>'
                    )
                encoded_rows.append(f'<row r="{row_number}">{"".join(encoded_cells)}</row>')
            worksheet = (
                '<?xml version="1.0" encoding="UTF-8"?>'
                '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
                f'<sheetData>{"".join(encoded_rows)}</sheetData></worksheet>'
            )
            archive.writestr(f"xl/worksheets/sheet{index}.xml", worksheet)
        if external_link:
            archive.writestr("xl/externalLinks/externalLink1.xml", "<externalLink/>")
        if macro:
            archive.writestr("xl/vbaProject.bin", b"not executable")
    return path


def mark_xlsx_encrypted(path: Path) -> Path:
    """Set ZIP encryption flags without needing an encryption-writing dependency."""
    data = bytearray(path.read_bytes())
    for signature, flag_offset in ((b"PK\x03\x04", 6), (b"PK\x01\x02", 8)):
        start = 0
        while True:
            position = data.find(signature, start)
            if position < 0:
                break
            flags = int.from_bytes(data[position + flag_offset:position + flag_offset + 2], "little")
            data[position + flag_offset:position + flag_offset + 2] = (flags | 1).to_bytes(2, "little")
            start = position + 4
    path.write_bytes(data)
    return path
