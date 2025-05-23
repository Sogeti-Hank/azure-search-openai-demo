"""
fileprocessor.py

This module defines the FileProcessor dataclass, which encapsulates a parser
and a text splitter for processing files in a document ingestion pipeline. It
is used to coordinate the parsing and splitting of documents into manageable
sections for further processing, such as embedding or indexing. The class is
designed to be immutable and easily composable within larger document
processing strategies.
"""

from dataclasses import dataclass

from .parser import Parser
from .textsplitter import TextSplitter


@dataclass(frozen=True)
class FileProcessor:
    parser: Parser
    splitter: TextSplitter
