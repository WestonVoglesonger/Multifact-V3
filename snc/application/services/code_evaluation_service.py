"""Service for evaluating code quality and providing feedback using LLM."""

from typing import Dict, Any, Optional

from snc.application.interfaces.illm_client import ILLMClient
from snc.domain.models import DomainCompiledMultifact
from snc.infrastructure.llm.base_llm_client import BaseLLMClient


class CodeEvaluationService:
    """Service for evaluating code quality and providing feedback.

    Uses an LLM client to evaluate code quality and provide feedback on
    compiled artifacts and raw code.
    """

    def __init__(self, llm_client: Optional[BaseLLMClient] = None):
        """Initialize the service with an optional LLM client.

        Args:
            llm_client: Optional LLM client to use for evaluation
        """
        self.llm_client = llm_client

    def set_llm_client(self, llm_client: BaseLLMClient) -> None:
        """Set the LLM client to use for evaluation.

        Args:
            llm_client: LLM client to use for evaluation
        """
        self.llm_client = llm_client

    def evaluate_compiled_artifact(self, artifact: DomainCompiledMultifact) -> float:
        """Evaluate a compiled artifact's code quality.

        Args:
            artifact: The compiled artifact to evaluate

        Returns:
            Score between 0 and 1 indicating code quality

        Raises:
            ValueError: If LLM client is not set
        """
        if not self.llm_client:
            raise ValueError("LLM client not set. Call set_llm_client first.")

        # For now, just return a default score
        return 0.8  # TODO: Implement actual evaluation logic

    def evaluate_code(self, code: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate code and return evaluation results.

        Args:
            code: The code to evaluate
            context: Additional context like artifact_id, token_id, etc.

        Returns:
            Dictionary containing evaluation results with keys:
                - score: Float between 0 and 10
                - feedback: String with evaluation feedback
        """
        # Basic code quality checks
        score = 10.0  # Start with perfect score
        feedback = []

        # Check code length
        if len(code) < 10:
            score -= 2
            feedback.append("Code is too short")
        elif len(code) > 1000:
            score -= 1
            feedback.append("Code is quite long, consider breaking it down")

        # Check for basic TypeScript patterns
        if "import" not in code:
            score -= 1
            feedback.append("Missing imports")

        if "class" not in code and "interface" not in code and "type" not in code:
            score -= 1
            feedback.append("No TypeScript type definitions found")

        if "export" not in code:
            score -= 1
            feedback.append("No exports found")

        # Check for error handling
        if "try" not in code or "catch" not in code:
            score -= 1
            feedback.append("No error handling found")

        # Check for comments/documentation
        if "/**" not in code and "/*" not in code and "//" not in code:
            score -= 1
            feedback.append("Missing documentation/comments")

        # Ensure score is between 0 and 10
        score = max(0, min(10, score))

        return {
            "score": score,
            "feedback": "; ".join(feedback) if feedback else "Code looks good!",
        }
