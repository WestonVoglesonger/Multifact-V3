"""
System Narrative Compiler (SNC): A compiler for handling system narratives with multi-token dependencies and LLM integration.
"""

from snc.application.services.ni_orchestrator import NIOrchestrator
from snc.application.services.dependency_graph_service import DependencyGraphService
from snc.infrastructure.llm.model_factory import OpenAIModelType
from snc.config import Settings, get_settings

__version__ = "0.1.0"

__all__ = [
    "NIOrchestrator",
    "DependencyGraphService",
    "OpenAIModelType",
    "Settings",
    "get_settings",
]
