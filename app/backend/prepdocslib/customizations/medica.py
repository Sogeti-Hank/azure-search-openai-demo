from azure.search.documents.indexes.models import SimpleField
from azure.identity.aio import (
    AzureDeveloperCliCredential,
    ManagedIdentityCredential,
    get_bearer_token_provider,
)
from typing import Any, Dict, Union
from openai import AsyncAzureOpenAI


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
            token_provider = get_bearer_token_provider(azure_credential, "https://cognitiveservices.azure.com/.default")
            llm_client = AsyncAzureOpenAI(
                api_version=AZURE_OPENAI_API_VERSION,
                azure_endpoint=endpoint,
                azure_ad_token_provider=token_provider,
            )
        prompt = (
            "Classify the following document and extract metadata fields such as doctype, planid, and locale. "
            "Return the result as a JSON object.\n\n"
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