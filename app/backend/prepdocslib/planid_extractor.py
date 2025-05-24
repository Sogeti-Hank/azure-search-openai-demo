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
        "If no Plan Identifier is found, respond with only 'None'.\n\n"
        f"Text:\n{text}"
    )
    try:
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
