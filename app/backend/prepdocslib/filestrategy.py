"""
filestrategy.py

This module implements file ingestion strategies for Azure-based document
search solutions. It provides asynchronous logic for parsing, splitting, and
processing files from local or cloud storage, and integrates with blob
storage, embedding services, and search index management. The FileStrategy
class orchestrates the end-to-end ingestion process, supporting features like
ACLs, content understanding, and category tagging. The module is extensible
for different file sources and document actions, and is central to the
document ingestion workflow.
"""

import logging
from typing import Optional

from azure.core.credentials import AzureKeyCredential

from .blobmanager import BlobManager
from .embeddings import ImageEmbeddings, OpenAIEmbeddings
from .fileprocessor import FileProcessor
from .listfilestrategy import File, ListFileStrategy
from .mediadescriber import ContentUnderstandingDescriber
from .searchmanager import SearchManager, Section
from .strategy import DocumentAction, SearchInfo, Strategy
from .planid_extractor import extract_plan_id_from_text
import openai

logger = logging.getLogger("scripts")


# Asynchronously parses a file using the appropriate file processor and splits it into sections.
# Returns a list of Section objects for further processing (e.g., indexing).
async def parse_file(
    file: File,
    file_processors: dict[str, FileProcessor],
    category: Optional[str] = None,
    image_embeddings: Optional[ImageEmbeddings] = None,
    openai_client: Optional[object] = None,  # Pass an OpenAI client for LLM extraction
) -> list[Section]:
    key = file.file_extension().lower()  # Get the file extension to select the processor
    processor = file_processors.get(key)  # Retrieve the processor for this file type
    if processor is None:
        logger.info("Skipping '%s', no parser found.", file.filename())
        return []
    logger.info("Ingesting '%s'", file.filename())
    # Parse the file content into pages (async generator)
    pages = [page async for page in processor.parser.parse(content=file.content)]
    logger.info("Splitting '%s' into sections", file.filename())
    if image_embeddings:
        # Warn if image embeddings are used, as images are chunked differently
        logger.warning("Each page will be split into smaller chunks of text, but images will be of the entire page.")

    # --- Plan Identifier Extraction for PDFs ---
    planid = None
    logger.info(f"File Key: {key}, Pages: {len(pages)}")
    logger.info(f"OpenAI Client: {openai_client}")
    if key == ".pdf" and pages and openai_client is not None:
        first_page_text = pages[0].text if pages[0].text else ""
        if first_page_text:
            logger.info("Extracting Plan Identifier from the first page of the PDF")
            planid = await extract_plan_id_from_text(first_page_text, openai_client)
            logger.info(f"Extracted Plan Identifier: {planid}")

    # Split pages into smaller sections for indexing
    sections = []
    for split_page in processor.splitter.split_pages(pages):
        section = Section(split_page, content=file, category=category)
        if planid is not None:
            section.planid = planid  # Attach planid to Section for later indexing
        sections.append(section)
    return sections


class FileStrategy(Strategy):
    """
    Strategy for ingesting documents into a search service from files stored either locally or in a data lake storage account
    """

    def __init__(
        self,
        list_file_strategy: ListFileStrategy,
        blob_manager: BlobManager,
        search_info: SearchInfo,
        file_processors: dict[str, FileProcessor],
        document_action: DocumentAction = DocumentAction.Add,
        embeddings: Optional[OpenAIEmbeddings] = None,
        image_embeddings: Optional[ImageEmbeddings] = None,
        search_analyzer_name: Optional[str] = None,
        search_field_name_embedding: Optional[str] = None,
        use_acls: bool = False,
        category: Optional[str] = None,
        use_content_understanding: bool = False,
        content_understanding_endpoint: Optional[str] = None,
    ):
        # Store all configuration and dependencies for the strategy
        self.list_file_strategy = list_file_strategy
        self.blob_manager = blob_manager
        self.file_processors = file_processors
        self.document_action = document_action
        self.embeddings = embeddings
        self.image_embeddings = image_embeddings
        self.search_analyzer_name = search_analyzer_name
        self.search_field_name_embedding = search_field_name_embedding
        self.search_info = search_info
        self.use_acls = use_acls
        self.category = category
        self.use_content_understanding = use_content_understanding
        self.content_understanding_endpoint = content_understanding_endpoint

    # Initializes the SearchManager with the provided configuration
    def setup_search_manager(self):
        self.search_manager = SearchManager(
            self.search_info,
            self.search_analyzer_name,
            self.use_acls,
            False,
            self.embeddings,
            field_name_embedding=self.search_field_name_embedding,
            search_images=self.image_embeddings is not None,
        )

    # Sets up the search index and (optionally) content understanding analyzer
    async def setup(self):
        self.setup_search_manager()
        await self.search_manager.create_index()

        if self.use_content_understanding:
            if self.content_understanding_endpoint is None:
                raise ValueError("Content Understanding is enabled but no endpoint was provided")
            if isinstance(self.search_info.credential, AzureKeyCredential):
                raise ValueError(
                    "AzureKeyCredential is not supported for Content Understanding, use keyless auth instead"
                )
            cu_manager = ContentUnderstandingDescriber(self.content_understanding_endpoint, self.search_info.credential)
            await cu_manager.create_analyzer()

    # Main entry point for running the ingestion/removal process based on document_action
    async def run(self):
        self.setup_search_manager()
        if self.document_action == DocumentAction.Add:
            files = self.list_file_strategy.list()  # List files to ingest
            async for file in files:
                try:
                    # Parse and split file into sections
                    sections = await parse_file(file, self.file_processors, self.category, self.image_embeddings)
                    if sections:
                        # Upload file to blob storage and get SAS URIs
                        blob_sas_uris = await self.blob_manager.upload_blob(file)
                        blob_image_embeddings: Optional[list[list[float]]] = None
                        if self.image_embeddings and blob_sas_uris:
                            # Generate image embeddings if enabled
                            blob_image_embeddings = await self.image_embeddings.create_embeddings(blob_sas_uris)
                        # Update the search index with the new content
                        await self.search_manager.update_content(sections, blob_image_embeddings, url=file.url)
                finally:
                    if file:
                        file.close()  # Ensure file is closed after processing
        elif self.document_action == DocumentAction.Remove:
            paths = self.list_file_strategy.list_paths()  # List file paths to remove
            async for path in paths:
                await self.blob_manager.remove_blob(path)
                await self.search_manager.remove_content(path)
        elif self.document_action == DocumentAction.RemoveAll:
            await self.blob_manager.remove_blob()
            await self.search_manager.remove_content()


class UploadUserFileStrategy:
    """
    Strategy for ingesting a file that has already been uploaded to a ADLS2 storage account
    """

    def __init__(
        self,
        search_info: SearchInfo,
        file_processors: dict[str, FileProcessor],
        embeddings: Optional[OpenAIEmbeddings] = None,
        image_embeddings: Optional[ImageEmbeddings] = None,
        search_field_name_embedding: Optional[str] = None,
    ):
        # Store configuration and dependencies for user-uploaded file ingestion
        self.file_processors = file_processors
        self.embeddings = embeddings
        self.image_embeddings = image_embeddings
        self.search_info = search_info
        self.search_manager = SearchManager(
            search_info=self.search_info,
            search_analyzer_name=None,
            use_acls=True,
            use_int_vectorization=False,
            embeddings=self.embeddings,
            field_name_embedding=search_field_name_embedding,
            search_images=False,
        )
        self.search_field_name_embedding = search_field_name_embedding

    # Adds a user-uploaded file to the search index
    async def add_file(self, file: File):
        if self.image_embeddings:
            logging.warning("Image embeddings are not currently supported for the user upload feature")
        sections = await parse_file(file, self.file_processors)
        if sections:
            await self.search_manager.update_content(sections, url=file.url)

    # Removes a user-uploaded file from the search index
    async def remove_file(self, filename: str, oid: str):
        if filename is None or filename == "":
            logging.warning("Filename is required to remove a file")
            return
        await self.search_manager.remove_content(filename, oid)
