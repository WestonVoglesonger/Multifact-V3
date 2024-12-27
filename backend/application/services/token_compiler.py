import logging
from typing import List
from backend.domain.models import DomainToken, DomainCompiledMultifact
from backend.infrastructure.llm.base_llm_client import BaseLLMClient
from backend.infrastructure.llm.groq_llm_client import GroqLLMClient
from backend.infrastructure.llm.openai_llm_client import OpenAILLMClient
from backend.application.interfaces.icompilation_service import ICompilationService
from backend.application.interfaces.ivalidation_service import IValidationService
from backend.application.services.code_evaluation_service import CodeEvaluationService
from backend.infrastructure.entities.compiled_multifact import CompiledMultifact


class TokenCompiler:
    def __init__(
        self,
        compilation_service: ICompilationService,
        validation_service: IValidationService,
        evaluation_service: CodeEvaluationService,
    ):
        self.compilation_service = compilation_service
        self.validation_service = validation_service
        self.evaluation_service = evaluation_service
        self.logger = logging.getLogger(__name__)

    def compile_and_validate(
        self,
        tokens: List[DomainToken],
        llm_client: GroqLLMClient | OpenAILLMClient,
        revalidate: bool,
    ):
        """
        Iterates over each DomainToken and:
        1) Compiles the token into an artifact.
        2) Validates the artifact if revalidate=True.
        3) Evaluates the artifact using CodeEvaluationService.
        """
        for tok in tokens:
            if tok.id is None:
                raise ValueError("Token ID cannot be None")

            try:
                # Initial compilation
                artifact = self.compilation_service.compile_token(tok.id, llm_client)

                # Validate if requested
                if revalidate:
                    validation_result = self.validation_service.validate_artifact(
                        artifact.id
                    )
                    if not validation_result.success:
                        for error in validation_result.errors:
                            print(error.message)
                        self.logger.warning(
                            f"Artifact {artifact.id} validation failed. Errors: {validation_result.errors}"
                        )
                        # Mark as invalid but don't raise exception
                        artifact.valid = False
                        self.compilation_service.update_artifact(artifact)
                        continue  # Skip evaluation for invalid artifacts

                # Only evaluate valid artifacts
                if artifact.valid:
                    evaluation_result = self.evaluation_service.evaluate_code(
                        artifact.code, {"token_id": tok.id, "artifact_id": artifact.id}
                    )

                    artifact.score = evaluation_result.get("score", 0)
                    artifact.feedback = evaluation_result.get(
                        "feedback", "No feedback provided."
                    )
                    self.compilation_service.update_artifact(artifact)

            except Exception as e:
                self.logger.error(
                    f"Failed to compile token {tok.token_uuid}. Error: {e}"
                )
                # Create invalid artifact instead of raising
                self.compilation_service.compile_token(
                    tok.id,
                    llm_client,
                )  # The compile_token method already handles failures
