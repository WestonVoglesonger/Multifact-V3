"""Interface for code evaluation service."""

from typing import Dict, Any


class ICodeEvaluationService:
    """Interface for evaluating code quality and correctness."""

    def evaluate_code(self, code: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate code and return quality metrics.

        Args:
            code: Code to evaluate
            metadata: Additional metadata about the code

        Returns:
            Dictionary containing evaluation results:
            - score: float between 0 and 1
            - feedback: string with detailed feedback
        """
        raise NotImplementedError
