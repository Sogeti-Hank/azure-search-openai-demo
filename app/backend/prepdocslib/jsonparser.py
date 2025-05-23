"""
jsonparser.py

This module implements JsonParser, a parser for converting JSON files into
Page objects for document ingestion pipelines. It supports both top-level
arrays and objects, yielding each as a Page for downstream processing. The
parser is asynchronous and integrates with the broader parsing and
splitting framework, enabling JSON data to be indexed or embedded for
search and AI applications.
"""

import json
from collections.abc import AsyncGenerator
from typing import IO

from .page import Page
from .parser import Parser


class JsonParser(Parser):
    """
    Concrete parser that can parse JSON into Page objects. A top-level object becomes a single Page, while a top-level array becomes multiple Page objects.
    """

    async def parse(self, content: IO) -> AsyncGenerator[Page, None]:
        offset = 0
        data = json.loads(content.read())
        if isinstance(data, list):
            for i, obj in enumerate(data):
                offset += 1  # For opening bracket or comma before object
                page_text = json.dumps(obj)
                yield Page(i, offset, page_text)
                offset += len(page_text)
        elif isinstance(data, dict):
            yield Page(0, 0, json.dumps(data))
