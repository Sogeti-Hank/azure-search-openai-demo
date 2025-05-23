"""
parser.py

This module defines the abstract Parser base class, which specifies the
interface for parsing file content into Page objects. It is intended to be
subclassed by concrete parsers for different file formats (e.g., text,
CSV, PDF, HTML, JSON). The class supports asynchronous parsing and is a
key component in the document ingestion and processing pipeline.
"""

from abc import ABC
from collections.abc import AsyncGenerator
from typing import IO

from .page import Page


class Parser(ABC):
    """
    Abstract parser that parses content into Page objects
    """

    async def parse(self, content: IO) -> AsyncGenerator[Page, None]:
        if False:
            yield  # pragma: no cover - this is necessary for mypy to type check
