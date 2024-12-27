from datetime import datetime
from typing import Optional, List, Tuple
from dataclasses import dataclass

class DomainToken:
    def __init__(
        self,
        id: Optional[int],
        token_uuid: str,
        token_type: str,
        content: str,
        hash: str,
        scene_name: Optional[str] = None,
        component_name: Optional[str] = None,
        order: int = 0,
        dependencies: Optional[List['DomainToken']] = None
    ):
        self.id = id
        self.token_uuid = token_uuid
        self.token_type = token_type
        self.content = content
        self.hash = hash
        self.scene_name = scene_name
        self.component_name = component_name
        self.order = order
        self.dependencies = dependencies if dependencies else []

    def add_dependency(self, token: 'DomainToken'):
        self.dependencies.append(token)

    def get_dependency_uuids(self) -> List[str]:
        return [dep.token_uuid for dep in self.dependencies]



class DomainDocument:
    def __init__(
        self,
        doc_id: int,
        content: str,
        version: Optional[str],
        created_at: datetime,
        updated_at: datetime,
        tokens: Optional[List[DomainToken]] = None
    ):
        self.id = doc_id
        self.content = content
        self.version = version
        self.created_at = created_at
        self.updated_at = updated_at
        self.tokens = tokens if tokens else []

    def add_token(self, token: DomainToken):
        self.tokens.append(token)

class DomainCompiledMultifact:
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
        feedback: Optional[str] = None
    ):
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
        """
        Updates the artifact with the evaluation results.
        """
        self.score = score
        self.feedback = feedback

    def get_evaluation_summary(self) -> str:
        """
        Returns a string summary of the evaluation results.
        """
        return f"Score: {self.score}, Feedback: {self.feedback}"

class Model:
    def __init__(
        self,
        client_type: 'ClientType',
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
        supports_reasoning: bool = False
    ):
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
    """
    Result of a token diff operation.
    """
    removed: List[Tuple[DomainToken, Optional[DomainCompiledMultifact]]]
    changed: List[Tuple[DomainToken, Optional[DomainCompiledMultifact], dict]]
    added: List[dict]
    evaluation_differences: Optional[List[Tuple[int, float, str]]] = None  # Token ID, New Score, Feedback

