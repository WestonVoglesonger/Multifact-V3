from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session, scoped_session, sessionmaker
from snc.domain.models import DomainDocument, DomainToken, DomainCompiledMultifact
from snc.domain.model_types import CompilationResult
from snc.infrastructure.entities.compiled_multifact import CompiledMultifact
from snc.infrastructure.entities.ni_token import NIToken
from snc.infrastructure.llm.base_llm_client import BaseLLMClient
from snc.application.interfaces.icompilation_service import ICompilationService
from snc.application.services.code_evaluation_service import CodeEvaluationService
from sqlalchemy import select
import re
from snc.infrastructure.entities.entity_base import EntityBase
import threading


class ConcreteCompilationService(ICompilationService):
    def __init__(self, session: Session):
        self._main_session = session
        self._thread_local = threading.local()
        self._thread_local.session = session

    @property
    def session(self) -> Session:
        return self._thread_local.session

    @session.setter
    def session(self, new_session: Session) -> None:
        self._thread_local.session = new_session

    def compile(self, code: str) -> CompilationResult:
        """Compile code and return the result."""
        try:
            return CompilationResult(
                code=code, valid=True, errors=None, cache_hit=False
            )
        except Exception as e:
            return CompilationResult(
                code="", valid=False, errors=[str(e)], cache_hit=False
            )

    def compile_multifact(
        self, multifact: DomainCompiledMultifact
    ) -> CompilationResult:
        """Compile multifact and return the result."""
        return CompilationResult(
            code=multifact.code,
            valid=multifact.valid,
            errors=None if multifact.valid else ["Compilation failed"],
            cache_hit=multifact.cache_hit,
            score=multifact.score,
            feedback=multifact.feedback,
        )

    def compile_token(
        self, token_id: int, llm_client: BaseLLMClient
    ) -> DomainCompiledMultifact:
        """Compile a token into a multifact."""
        try:
            # Delete any existing non-cached artifacts for this token
            self._thread_local.session.query(CompiledMultifact).filter(
                CompiledMultifact.ni_token_id == token_id,
                CompiledMultifact.cache_hit == False,
            ).delete()

            # Check for cached artifacts
            cached_artifact = (
                self._thread_local.session.query(CompiledMultifact)
                .filter(
                    CompiledMultifact.ni_token_id == token_id,
                    CompiledMultifact.cache_hit == True,
                )
                .first()
            )
            if cached_artifact:
                return cached_artifact.to_domain_artifact()

            # Get token
            token = (
                self._thread_local.session.query(NIToken)
                .filter(NIToken.id == token_id)
                .one_or_none()
            )
            if not token:
                raise ValueError(f"Token with id {token_id} not found")

            # Extract target name from token content
            import re

            patterns = {
                "scene": r"\[Scene:(\w+)\]",
                "component": r"\[Component:(\w+)\]",
                "service": r"\[Service:(\w+)\]",
                "interface": r"\[Interface:(\w+)\]",
                "type": r"\[Type:(\w+)\]",
            }

            pattern = patterns.get(token.token_type)
            if not pattern:
                raise ValueError(f"Unknown token type: {token.token_type}")

            match = re.search(pattern, token.content)
            if not match:
                raise ValueError("Could not extract target name from token content.")

            target_name = match.group(1)

            # Generate code
            code = llm_client.generate_code(token.content)

            # Create new artifact
            artifact = CompiledMultifact(
                ni_token_id=token_id,
                language="typescript",
                framework="angular",
                code=code,
                valid=True,
                cache_hit=False,
                token_hash=None,
            )

            # Expire the session to clear identity map
            self._thread_local.session.expire_all()

            # Add and commit the new artifact
            self._thread_local.session.add(artifact)
            self._thread_local.session.commit()

            return artifact.to_domain_artifact()

        except Exception as e:
            self._thread_local.session.rollback()
            raise e

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
        """Update an existing artifact."""
        try:
            db_artifact = (
                self._thread_local.session.query(CompiledMultifact)
                .filter(CompiledMultifact.id == artifact.id)
                .one_or_none()
            )
            if db_artifact:
                db_artifact.code = artifact.code
                db_artifact.valid = artifact.valid
                db_artifact.score = artifact.score
                db_artifact.feedback = artifact.feedback
                self._thread_local.session.commit()
        except Exception as e:
            self._thread_local.session.rollback()
            raise e

    def get_session(self) -> Session:
        return self.session
