"""
csvparser.py

This module defines CsvParser, a concrete parser for reading CSV files and
converting each row into a Page object for further processing. It is designed
to work asynchronously and integrates with a document ingestion pipeline,
allowing CSV data to be split into logical pages for downstream text splitting
and embedding. The parser handles both binary and text file inputs and skips
header rows to yield only data rows as Page objects.
"""

import csv
from collections.abc import AsyncGenerator
from typing import IO

from .page import Page
from .parser import Parser


class CsvParser(Parser):
    """
    Concrete parser that can parse CSV into Page objects. Each row becomes a Page object.
    """

    async def parse(self, content: IO) -> AsyncGenerator[Page, None]:
        # Check if content is in bytes (binary file) and decode to string
        content_str: str
        if isinstance(content, (bytes, bytearray)):
            content_str = content.decode("utf-8")
        elif hasattr(content, "read"):  # Handle BufferedReader
            content_str = content.read().decode("utf-8")

        # Create a CSV reader from the text content
        reader = csv.reader(content_str.splitlines())
        offset = 0

        # Skip the header row
        next(reader, None)

        for i, row in enumerate(reader):
            page_text = ",".join(row)
            yield Page(i, offset, page_text)
            offset += len(page_text) + 1  # Account for newline character
