"""Connector interface: every source (file, ERP, bank, API) yields rows as {header: text}."""

import csv
import io
from collections.abc import Iterator
from pathlib import Path
from typing import Protocol


class Connector(Protocol):
    def read(self) -> tuple[list[str], Iterator[dict[str, str]]]:
        """Return (headers, row iterator)."""
        ...


class CsvFileConnector:
    """CSV/TSV/semicolon files. Delimiter is sniffed; UTF-8 (with or without BOM) then Latin-1."""

    def __init__(self, path: Path):
        self.path = path

    def _text(self) -> io.StringIO:
        data = self.path.read_bytes()
        for encoding in ("utf-8-sig", "latin-1"):
            try:
                return io.StringIO(data.decode(encoding), newline="")
            except UnicodeDecodeError:
                continue
        raise ValueError("Unsupported file encoding")  # pragma: no cover - latin-1 decodes anything

    def read(self) -> tuple[list[str], Iterator[dict[str, str]]]:
        text = self._text()
        sample = text.read(8192)
        text.seek(0)
        try:
            dialect: type[csv.Dialect] | csv.Dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
        except csv.Error:
            dialect = csv.excel
        reader = csv.DictReader(text, dialect=dialect)
        headers = [h for h in (reader.fieldnames or []) if h is not None]
        if not headers:
            raise ValueError("File has no header row")
        return headers, ({k: v for k, v in row.items() if k is not None} for row in reader)
