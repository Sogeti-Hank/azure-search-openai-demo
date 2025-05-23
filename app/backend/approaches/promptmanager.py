"""
promptmanager.py

This module defines the `PromptManager` interface and its Prompty-based implementation for loading, rendering, and managing prompts and tool definitions for LLM-based approaches. It provides:
- The `PromptManager` abstract base class, which defines the interface for loading prompts, loading tool definitions, and rendering prompts with data.
- The `PromptyManager` concrete implementation, which loads prompts and tools from the local prompts directory using the `prompty` library and standard JSON.

This file is central to the orchestration of prompt engineering and tool management for all retrieval-augmented and agentic approaches in the backend.
"""

import json
import pathlib

import prompty
from openai.types.chat import ChatCompletionMessageParam


class PromptManager:
    """
    Abstract base class for prompt management. Defines the interface for loading prompts, loading tools, and rendering prompts with data.
    """

    def load_prompt(self, path: str):
        raise NotImplementedError

    def load_tools(self, path: str):
        raise NotImplementedError

    def render_prompt(self, prompt, data) -> list[ChatCompletionMessageParam]:
        raise NotImplementedError


class PromptyManager(PromptManager):
    """
    Prompty-based implementation of PromptManager. Loads prompts and tool definitions from the local prompts directory.
    """

    PROMPTS_DIRECTORY = pathlib.Path(__file__).parent / "prompts"

    def load_prompt(self, path: str):
        # Loads a prompt file using the prompty library
        return prompty.load(self.PROMPTS_DIRECTORY / path)

    def load_tools(self, path: str):
        # Loads a tool definition file as JSON
        return json.loads(open(self.PROMPTS_DIRECTORY / path).read())

    def render_prompt(self, prompt, data) -> list[ChatCompletionMessageParam]:
        # Renders a prompt with the provided data using prompty
        return prompty.prepare(prompt, data)
