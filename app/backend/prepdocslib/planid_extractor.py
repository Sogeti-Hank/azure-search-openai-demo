"""
planid_extractor.py

This module provides a utility function to extract the Plan Identifier from a document's first page text using an LLM (e.g., Azure OpenAI or OpenAI API).
"""
import logging
from typing import Optional

import openai

logger = logging.getLogger("scripts")

async def extract_plan_id_from_text(text: str, openai_client, model: str = "gpt-3.5-turbo") -> Optional[str]:
    """
    Uses an LLM to extract the Plan Identifier from the provided text.
    Args:
        text (str): The text from the first page of the document.
        openai_client: An instance of an async OpenAI client (e.g., AsyncOpenAI or AsyncAzureOpenAI).
        model (str): The model to use for extraction.
    Returns:
        Optional[str]: The extracted Plan Identifier, or None if not found.
    """
    prompt = (
        "You are an expert at reading benefit plan documents. "
        "Extract the Plan Identifier from the following text. "
        "If no Plan Identifier is found, set the planid in the following return format with only 'None'.\n\n"
        "If a planid is found, set documentype to POC. "
        "If there is no planid found, set the document_type to A2Z if it is an A to Z document, or SBC if the doc is a Summary of Benefits and Coverage doc. "
        "If the title of the document starts with 'MN', set the locale to MN, otherwise ignore it.\n\n"
        "Return your answer as a JSON object with the following structure:\n"
        '{\n'
        '  "planid": <Plan Identifier or null>,\n'
        f'  "documenttype": "{document_type}",\n'
        f'  "locale": "{locale}"\n'
        '}\n\n'
        f"Text:\n{text}"
    )
    try:
        logger.info("PlanID Extractor entry.")
        response = await openai_client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=20,
            temperature=0.0,
        )
        plan_id = response.choices[0].message.content.strip()
        if plan_id.lower() == "none" or not plan_id:
            return None
        return plan_id
    except Exception as e:
        logger.warning(f"Plan ID extraction failed: {e}")
        return None
