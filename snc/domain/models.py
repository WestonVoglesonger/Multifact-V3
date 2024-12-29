"""Core domain models for the System Narrative Compiler."""

from datetime import datetime
from typing import Optional, List, Tuple, Literal
from dataclasses import dataclass

# Type alias for supported client types
ClientType = Literal["openai", "groq", "anthropic"]


class DomainToken:
    """A token representing a discrete unit of narrative instruction."""

    def __init__(
        self,
        id: Optional[int],
        token_uuid: str,
        token_name: str,
        token_type: str,
        content: str,
        hash: str,
        scene_name: Optional[str] = None,
        component_name: Optional[str] = None,
        function_name: Optional[str] = None,
        order: int = 0,
        dependencies: Optional[List["DomainToken"]] = None,
    ):
        """Initialize a domain token.

        Args:
            id: Database ID if persisted
            token_uuid: Unique identifier
            token_name: Display name
            token_type: Type of token
            content: Narrative content
            hash: Content hash
            scene_name: Optional scene name
            component_name: Optional component name
            function_name: Optional function name
            order: Token order in document
            dependencies: List of dependent tokens
        """
        self.id = id
        self.token_uuid = token_uuid
        self.token_name = token_name
        self.token_type = token_type
        self.content = content
        self.hash = hash
        self.scene_name = scene_name
        self.component_name = component_name
        self.function_name = function_name
        self.order = order
        self.dependencies = dependencies if dependencies else []

    def add_dependency(self, token: "DomainToken"):
        """Add a dependency token to this token."""
        self.dependencies.append(token)

    def get_dependency_uuids(self) -> List[str]:
        """Get UUIDs of all dependency tokens."""
        return [dep.token_uuid for dep in self.dependencies]


class DomainDocument:
    """A document containing narrative instructions and their tokens."""

    def __init__(
        self,
        doc_id: int,
        content: str,
        version: Optional[str],
        created_at: datetime,
        updated_at: datetime,
        tokens: Optional[List[DomainToken]] = None,
    ):
        """Initialize a domain document.

        Args:
            doc_id: Database ID
            content: Document content
            version: Optional version string
            created_at: Creation timestamp
            updated_at: Last update timestamp
            tokens: List of tokens in document
        """
        self.id = doc_id
        self.content = content
        self.version = version
        self.created_at = created_at
        self.updated_at = updated_at
        self.tokens = tokens if tokens else []

    def add_token(self, token: DomainToken):
        """Add a token to this document."""
        self.tokens.append(token)


class DomainCompiledMultifact:
    """A compiled artifact representing generated code from a token."""

    def __init__(
        self,
        artifact_id: int,
        ni_token_id: int,
        language: str,
        framework: str,
        code: str,
        valid: bool,
        cache_hit: bool,
        created_at: datetime,
        score: Optional[float] = None,
        feedback: Optional[str] = None,
    ):
        """Initialize a compiled artifact.

        Args:
            artifact_id: Database ID
            ni_token_id: ID of source token
            language: Programming language
            framework: Framework used
            code: Generated code
            valid: Whether code is valid
            cache_hit: Whether from cache
            created_at: Creation timestamp
            score: Optional quality score
            feedback: Optional feedback
        """
        self.id = artifact_id
        self.ni_token_id = ni_token_id
        self.language = language
        self.framework = framework
        self.code = code
        self.valid = valid
        self.cache_hit = cache_hit
        self.created_at = created_at
        self.score = score
        self.feedback = feedback

    def set_evaluation_results(self, score: float, feedback: str):
        """Update the artifact with evaluation results."""
        self.score = score
        self.feedback = feedback

    def get_evaluation_summary(self) -> str:
        """Get a summary of the evaluation results."""
        return f"Score: {self.score}, Feedback: {self.feedback}"


class Model:
    """Configuration for a specific language model."""

    def __init__(
        self,
        client_type: ClientType,
        name: str,
        context_window: int,
        max_output_tokens: int,
        prompt_cost_per_1k: float,
        completion_cost_per_1k: float,
        supports_images: bool,
        reasoning_tokens: Optional[float] = None,
        knowledge_cutoff_date: Optional[str] = None,
        supports_audio: bool = False,
        supports_video: bool = False,
        supports_reasoning: bool = False,
    ):
        """Initialize a model configuration.

        Args:
            client_type: Type of LLM client
            name: Model name
            context_window: Max context length
            max_output_tokens: Max generation length
            prompt_cost_per_1k: Input cost per 1k tokens
            completion_cost_per_1k: Output cost per 1k tokens
            supports_images: Whether model handles images
            reasoning_tokens: Optional reasoning capacity
            knowledge_cutoff_date: Optional training cutoff
            supports_audio: Whether model handles audio
            supports_video: Whether model handles video
            supports_reasoning: Whether model can reason
        """
        self.client_type = client_type
        self.name = name
        self.context_window = context_window
        self.max_output_tokens = max_output_tokens
        self.prompt_cost_per_1k = prompt_cost_per_1k
        self.completion_cost_per_1k = completion_cost_per_1k
        self.supports_images = supports_images
        self.reasoning_tokens = reasoning_tokens
        self.knowledge_cutoff_date = knowledge_cutoff_date
        self.supports_audio = supports_audio
        self.supports_video = supports_video
        self.supports_reasoning = supports_reasoning


@dataclass
class TokenDiffResult:
    """Result of comparing tokens between document versions."""

    removed: List[Tuple[DomainToken, Optional[DomainCompiledMultifact]]]
    changed: List[Tuple[DomainToken, Optional[DomainCompiledMultifact], dict]]
    added: List[dict]
    evaluation_differences: Optional[List[Tuple[int, float, str]]] = (
        None  # Token ID, New Score, Feedback
    )
