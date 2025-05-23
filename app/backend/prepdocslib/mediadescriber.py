"""
mediadescriber.py

This module provides classes for describing media content, particularly
images, using Azure Content Understanding APIs. It includes an abstract
MediaDescriber and a ContentUnderstandingDescriber that can create custom
analyzers and poll for analysis results. The module is designed for
integration with document processing pipelines that require extraction of
structured information or descriptions from images, supporting advanced
AI-powered document understanding scenarios.
"""

import logging
from abc import ABC

import aiohttp
from azure.core.credentials_async import AsyncTokenCredential
from azure.identity.aio import get_bearer_token_provider
from rich.progress import Progress
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_fixed

logger = logging.getLogger("scripts")


class MediaDescriber(ABC):
    # Abstract base class for media describers. Subclasses must implement describe_image.
    async def describe_image(self, image_bytes) -> str:
        raise NotImplementedError  # pragma: no cover


class ContentUnderstandingDescriber:
    CU_API_VERSION = "2024-12-01-preview"

    # Schema for the custom analyzer to be created in Azure Content Understanding
    analyzer_schema = {
        "analyzerId": "image_analyzer",
        "name": "Image understanding",
        "description": "Extract detailed structured information from images extracted from documents.",
        "baseAnalyzerId": "prebuilt-image",
        "scenario": "image",
        "config": {"returnDetails": False},
        "fieldSchema": {
            "name": "ImageInformation",
            "descriptions": "Description of image.",
            "fields": {
                "Description": {
                    "type": "string",
                    "description": "Description of the image. If the image has a title, start with the title. Include a 2-sentence summary. If the image is a chart, diagram, or table, include the underlying data in an HTML table tag, with accurate numbers. If the image is a chart, describe any axis or legends. The only allowed HTML tags are the table/thead/tr/td/tbody tags.",
                },
            },
        },
    }

    def __init__(self, endpoint: str, credential: AsyncTokenCredential):
        # Store endpoint and credential for API calls
        self.endpoint = endpoint
        self.credential = credential

    async def poll_api(self, session, poll_url, headers):
        # Polls the Azure API for completion of a long-running operation (e.g., analyzer creation or image analysis)
        # Retries up to 60 times, waiting 2 seconds between attempts, if the status is 'Running'.
        @retry(stop=stop_after_attempt(60), wait=wait_fixed(2), retry=retry_if_exception_type(ValueError))
        async def poll():
            # Make a GET request to the poll_url to check operation status
            async with session.get(poll_url, headers=headers) as response:
                response.raise_for_status()
                response_json = await response.json()
                if response_json["status"] == "Failed":
                    # Raise if the operation failed
                    raise Exception("Failed")
                if response_json["status"] == "Running":
                    # Raise ValueError to trigger retry if still running
                    raise ValueError("Running")
                # Return the result if operation succeeded
                return response_json

        return await poll()

    async def create_analyzer(self):
        # Creates a custom analyzer in Azure Content Understanding if it does not already exist
        logger.info("Creating analyzer '%s'...", self.analyzer_schema["analyzerId"])

        # Get a bearer token for authentication
        token_provider = get_bearer_token_provider(self.credential, "https://cognitiveservices.azure.com/.default")
        token = await token_provider()
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        params = {"api-version": self.CU_API_VERSION}
        analyzer_id = self.analyzer_schema["analyzerId"]
        cu_endpoint = f"{self.endpoint}/contentunderstanding/analyzers/{analyzer_id}"
        async with aiohttp.ClientSession() as session:
            # Send PUT request to create the analyzer
            async with session.put(
                url=cu_endpoint, params=params, headers=headers, json=self.analyzer_schema
            ) as response:
                if response.status == 409:
                    # Analyzer already exists
                    logger.info("Analyzer '%s' already exists.", analyzer_id)
                    return
                elif response.status != 201:
                    # Raise exception if creation failed
                    data = await response.text()
                    raise Exception("Error creating analyzer", data)
                else:
                    # Get the polling URL from the response header
                    poll_url = response.headers.get("Operation-Location")

            # Show progress bar while polling for completion
            with Progress() as progress:
                progress.add_task("Creating analyzer...", total=None, start=False)
                await self.poll_api(session, poll_url, headers)

    async def describe_image(self, image_bytes: bytes) -> str:
        # Sends an image to Azure Content Understanding for analysis and returns the description string
        logger.info("Sending image to Azure Content Understanding service...")
        async with aiohttp.ClientSession() as session:
            # Get a bearer token for authentication
            token = await self.credential.get_token("https://cognitiveservices.azure.com/.default")
            headers = {"Authorization": "Bearer " + token.token}
            params = {"api-version": self.CU_API_VERSION}
            analyzer_name = self.analyzer_schema["analyzerId"]
            # Send POST request to analyze the image
            async with session.post(
                url=f"{self.endpoint}/contentunderstanding/analyzers/{analyzer_name}:analyze",
                params=params,
                headers=headers,
                data=image_bytes,
            ) as response:
                response.raise_for_status()
                # Get the polling URL from the response header
                poll_url = response.headers["Operation-Location"]

                # Show progress bar while polling for completion
                with Progress() as progress:
                    progress.add_task("Processing...", total=None, start=False)
                    results = await self.poll_api(session, poll_url, headers)

                # Extract and return the image description from the results
                fields = results["result"]["contents"][0]["fields"]
                return fields["Description"]["valueString"]
