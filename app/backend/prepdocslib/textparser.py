"""
textparser.py

This module implements TextParser, a parser for extracting and cleaning
text from plain text files. It uses regular expressions to normalize
whitespace and newlines, and yields the cleaned text as a Page object. The
parser is asynchronous and designed for use in document ingestion
pipelines that require robust text extraction and preprocessing.
"""

import re
from collections.abc import AsyncGenerator
from typing import IO

from .page import Page
from .parser import Parser


def cleanup_data(data: str) -> str:
    """Cleans up the given content using regexes
    Args:
        data: (str): The data to clean up.
    Returns:
        str: The cleaned up data.
    """
    # match two or more newlines and replace them with one new line
    output = re.sub(r"\n{2,}", "\n", data)
    # match two or more spaces that are not newlines and replace them with one space
    output = re.sub(r"[^\S\n]{2,}", " ", output)

    return output.strip()


class TextParser(Parser):
    """Parses simple text into a Page object."""

    async def parse(self, content: IO) -> AsyncGenerator[Page, None]:
        data = content.read()
        decoded_data = data.decode("utf-8")
        text = cleanup_data(decoded_data)
        yield Page(0, 0, text=text)
