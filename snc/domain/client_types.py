"""Enums for client types in the System Narrative Compiler."""

from enum import Enum


class ClientType(Enum):
    """
    Enumeration of supported LLM clients.

    - OPENAI: Models and endpoints associated with OpenAI.
    - GROQ: Models and endpoints offered by the Groq service.
    """

    OPENAI = "openai"
    GROQ = "groq"
