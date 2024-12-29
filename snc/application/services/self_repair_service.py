"""Service for automatically repairing invalid code artifacts."""

from typing import List
from sqlalchemy.orm import Session

from snc.application.interfaces.iartifact_repository import IArtifactRepository
from snc.application.interfaces.icode_fixer_service import ICodeFixerService
from snc.application.interfaces.ivalidation_service import (
    IValidationService,
    ValidationError,
)
from snc.application.services.exceptions import ArtifactNotFoundError
from snc.infrastructure.entities import CompiledMultifact


class SelfRepairService:
    """Service for automatically repairing invalid code artifacts."""

    def __init__(
        self,
        artifact_repo: IArtifactRepository,
        validation_service: IValidationService,
        code_fixer_service: ICodeFixerService,
        session: Session,
    ) -> None:
        """Initialize the service.

        Args:
            artifact_repo: Repository for artifact operations
            validation_service: Service for validating code
            code_fixer_service: Service for fixing invalid code
            session: Database session for persistence
        """
        self.artifact_repo = artifact_repo
        self.validation_service = validation_service
        self.code_fixer_service = code_fixer_service
        self.session = session

    def repair_artifact(
        self, artifact_id: int, max_attempts: int = 3
    ) -> bool:
        """Attempt to repair an invalid artifact.

        Args:
            artifact_id: ID of artifact to repair
            max_attempts: Maximum number of repair attempts

        Returns:
            True if artifact is valid after repairs, False otherwise

        Raises:
            ArtifactNotFoundError: If artifact not found
        """
        artifact = self.artifact_repo.get_artifact_by_id(artifact_id)
        if not artifact:
            raise ArtifactNotFoundError(
                f"Artifact with id {artifact_id} not found."
            )

        for attempt in range(max_attempts):
            result = self.validation_service.validate_artifact(artifact_id)

            if result.success:
                artifact_entity = (
                    self.session.query(CompiledMultifact)
                    .get(artifact_id)
                )
                if artifact_entity:
                    artifact_entity.valid = True
                    self.session.commit()
                return True
            else:
                error_summary = self._summarize_errors(result.errors)
                new_code = self.code_fixer_service.fix_code(
                    artifact.code,
                    error_summary
                )
                # Update artifact with new code, set valid=False
                self.artifact_repo.update_artifact_code(
                    artifact_id,
                    new_code,
                    valid=False
                )

        # After max attempts, final check
        final_result = self.validation_service.validate_artifact(artifact_id)
        if final_result.success:
            artifact_entity = (
                self.session.query(CompiledMultifact)
                .get(artifact_id)
            )
            if artifact_entity:
                artifact_entity.valid = True
                self.session.commit()
            return True
        else:
            # Mark as invalid if needed
            self.artifact_repo.update_artifact_code(
                artifact_id,
                artifact.code,
                valid=False
            )
            return False

    def _summarize_errors(self, errors: List[ValidationError]) -> str:
        """Format validation errors into a summary string.

        Args:
            errors: List of validation errors to summarize

        Returns:
            Formatted error summary string
        """
        lines = ["Found the following TypeScript errors:"]
        for err in errors:
            lines.append(
                f"{err.file}({err.line},{err.char}): {err.message}"
            )
        return "\n".join(lines)
