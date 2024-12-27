from typing import List, Dict, Any
from sqlalchemy.orm import Session
from backend.domain.models import DomainDocument, DomainToken, DomainCompiledMultifact
from backend.infrastructure.entities.compiled_multifact import CompiledMultifact
from backend.infrastructure.entities.ni_token import NIToken
from backend.infrastructure.llm.base_llm_client import BaseLLMClient
from backend.application.interfaces.icompilation_service import ICompilationService
from backend.application.services.code_evaluation_service import CodeEvaluationService
from sqlalchemy import select


class ConcreteCompilationService(ICompilationService):
    def __init__(self, session: Session):
        self.session = session

    def compile_token(
        self, token_id: int, llm_client: BaseLLMClient
    ) -> DomainCompiledMultifact:
        """
        Compile a token into an artifact. Removes any existing artifacts for this token
        before creating a new one to ensure we always have exactly one artifact per token.
        """
        # 1) Ensure the token exists
        t_ent = self.session.scalar(select(NIToken).where(NIToken.id == token_id))
        if not isinstance(t_ent, NIToken):
            raise ValueError(f"Token with id {token_id} not found")

        try:
            # Try to compile
            code = llm_client.generate_code(t_ent.content)
            code = code.replace("```typescript", "").replace("```", "")
            valid = True
        except Exception as e:
            # If compilation fails, create an invalid artifact
            code = f"// Compilation failed: {str(e)}"
            valid = False

        # Delete any existing artifacts for this token
        self.session.query(CompiledMultifact).filter(
            CompiledMultifact.ni_token_id == token_id
        ).delete()
        self.session.commit()

        # Create a new artifact
        artifact = CompiledMultifact(
            ni_token_id=token_id,
            language="typescript",
            framework="angular",
            code=code,
            valid=valid,
            cache_hit=False,
        )
        self.session.add(artifact)
        self.session.commit()

        return artifact.to_domain_artifact()

    def compile_document(
        self, document: DomainDocument, llm_client: BaseLLMClient
    ) -> List[CompiledMultifact]:
        compiled_artifacts = []
        for tok in document.tokens:
            if tok.id is None:
                raise ValueError(f"Token with id {tok.id} not found")
            artifact_domain = self.compile_token(tok.id, llm_client)
            artifact_ent = self.session.query(CompiledMultifact).get(artifact_domain.id)
            compiled_artifacts.append(artifact_ent)
        return compiled_artifacts

    def compile_token_with_dependencies(
        self, token_id: int, llm_client: BaseLLMClient
    ) -> List[CompiledMultifact]:
        compiled_artifacts = []
        result = self.session.query(NIToken).get(token_id)
        if not isinstance(result, NIToken):
            raise ValueError(f"Token with id {token_id} not found")

        # Recurse over dependencies:
        for dep_ent in result.dependencies:
            compiled_artifacts_dep = self.compile_token_with_dependencies(
                dep_ent.id, llm_client
            )
            compiled_artifacts.extend(compiled_artifacts_dep)

        # Now compile this token:
        domain_artifact = self.compile_token(result.id, llm_client)
        artifact_ent = self.session.query(CompiledMultifact).get(domain_artifact.id)
        compiled_artifacts.append(artifact_ent)
        return compiled_artifacts

    def mark_artifact_invalid(self, artifact_id: int) -> None:
        """
        Called by TokenCompiler if revalidate fails so the artifact is committed
        with valid=False.
        """
        artifact_ent = self.session.query(CompiledMultifact).get(artifact_id)
        if artifact_ent:
            artifact_ent.valid = False
            self.session.commit()

    def evaluate_compiled_artifact(
        self, artifact_id: int, evaluator: CodeEvaluationService
    ) -> Dict[str, Any]:
        """
        1. Fetch the compiled artifact by its ID.
        2. Pass the artifact code to the evaluator service.
        3. (Optional) store the results in DB or just return them.

        :param artifact_id: The DB ID of the compiled artifact to evaluate.
        :param session: Your active SQLAlchemy session.
        :param evaluator: The CodeEvaluationService instance (with a second LLM).
        :return: A dict with keys e.g. {'score': float, 'feedback': str}
        """
        artifact = self.session.query(CompiledMultifact).get(artifact_id)
        if not artifact:
            raise ValueError(f"Artifact with ID={artifact_id} does not exist.")

        code = artifact.code
        context = {
            "artifact_id": artifact_id,
            "token_id": artifact.ni_token_id,
            "valid": artifact.valid,
        }

        eval_result = evaluator.evaluate_code(code, context)

        # Store the results directly in the artifact
        artifact.score = float(eval_result["score"])
        artifact.feedback = eval_result["feedback"]
        self.session.commit()

        return eval_result

    def update_artifact(self, artifact: DomainCompiledMultifact) -> None:
        """
        Updates an existing artifact record with new fields (score, feedback, etc.).
        """
        # Grab the corresponding CompiledMultifact from DB
        db_artifact = self.session.query(CompiledMultifact).get(artifact.id)
        if not db_artifact:
            raise ValueError(f"Artifact with ID={artifact.id} not found.")

        # Overwrite fields that might have changed
        db_artifact.code = artifact.code
        db_artifact.valid = artifact.valid
        db_artifact.score = artifact.score
        db_artifact.feedback = artifact.feedback
        db_artifact.cache_hit = artifact.cache_hit

        # Commit to DB
        self.session.commit()

    def get_session(self) -> Session:
        return self.session
