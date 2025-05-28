from azure.search.documents.indexes.models import SimpleField
from azure.identity.aio import (
    AzureDeveloperCliCredential,
    ManagedIdentityCredential,
    get_bearer_token_provider,
)
from typing import Any, Dict, Union
from openai import AsyncAzureOpenAI

import os
import logging
logger = logging.getLogger("scripts")


class FieldCustomizer:
    """
    Concrete parser that can parse CSV into Page objects. Each row becomes a Page object.
    """

def append_fields(fields: list) -> list:
    """
    Appends custom fields to the given list of fields.
    
    Args:
        fields (list): The list of fields to append to.
    
    Returns:
        list: The updated list of fields with custom fields appended.
    """
    fields.append(SimpleField(name="planid", type="Edm.String", filterable=True, facetable=False))
    fields.append(SimpleField(name="doctype", type="Edm.String", filterable=True, facetable=False))
    fields.append(SimpleField(name="locale", type="Edm.String", filterable=True, facetable=True))
    
    return fields

class MedicaDocClassifier:
    def __init__(self, llm_client):
        self.llm_client = llm_client

    async def classify(self, text: str) -> Dict[str, Any]:
        """
        Uses an LLM to classify the document and extract metadata.
        Returns a dict with keys like 'doctype', 'planid', 'locale', etc.
        """

        azure_credential: Union[AzureDeveloperCliCredential, ManagedIdentityCredential]
        if not self.llm_client:
            logger.info("No LLM client provided, initializing Azure OpenAI client.")
            logger.info("AZURE_OPENAI_API_VERSION = " + os.getenv("AZURE_OPENAI_API_VERSION"))
            azure_credential = AzureDeveloperCliCredential()  # or ManagedIdentityCredential()
            token_provider = get_bearer_token_provider(azure_credential, "https://cognitiveservices.azure.com/.default")
            logger.info("Token Provider " + token_provider)
            llm_client = AsyncAzureOpenAI(
                api_version= os.getenv("AZURE_OPENAI_API_VERSION")
                azure_endpoint= "https://cog-zvuhhhpiitc46.openai.azure.com/",  ## endpoint,  -Hank
                azure_ad_token_provider=token_provider,
            )
        prompt = (
            """You are an intelligent assistant helping to classify documents and extract metadata from them.
                You will answer in the json format provided in the example below, do not stray from this concise answer pattern, do not add any info you do not find in the provided text.
                If you cannot determine an answer, remember it is better to give a 100% correct response than it is to give a guess.

                If you can determine that the string has a value for "Plan Identifier", it may look like "2025-IFBAPBCPCMNZ" for instance, then you have found a document where doctype = poc, and planid = the Plan Identifier previously described.  In this same doc, you will find the state that the plan applies to, return the 2 letter abbreviation for the state as the locale.
                

                If you can determine that the string has a value for "Summary of Benefits and Coverage:" then you have found a Summary of Benefits doc, where doctype = sbc, but leave the locale and planid blank. See the following example
                

                If you can determine that the string has the following value: Location: Benefits/A-Z List, then you have a doctype = a2z, but leave the locale and planid blank. See the following example.
               """
            f"Document:\n{text[:2000]}"  # Limit to first 2000 chars for prompt size
        )
        response = await self.llm_client.chat.completions.create(
            model="gpt-4",  # or your deployment/model name
            messages=[{"role": "user", "content": prompt}],
            max_tokens=256,
            temperature=0
        )
        # Parse the LLM's response as JSON
        import json
        try:
            result = json.loads(response.choices[0].message.content)
        except Exception:
            result = {"doctype": None, "planid": None, "locale": None}
        return result