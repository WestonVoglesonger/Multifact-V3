from typing import List
from snc.application.interfaces.iartifact_repository import IArtifactRepository
from snc.application.interfaces.icode_fixer_service import ICodeFixerService
from snc.application.interfaces.ivalidation_service import IValidationService
from snc.application.services.exceptions import ArtifactNotFoundError
from snc.application.services.exceptions import LLMParsingError
from snc.application.interfaces.ivalidation_service import (
    ValidationResult,
    ValidationError,
)
from sqlalchemy.orm import Session
from snc.infrastructure.entities import CompiledMultifact


class SelfRepairService:
    def __init__(
        self,
        artifact_repo: IArtifactRepository,
        validation_service: IValidationService,
        code_fixer_service: ICodeFixerService,
        session: Session,
    ):
        self.artifact_repo = artifact_repo
        self.validation_service = validation_service
        self.code_fixer_service = code_fixer_service
        self.session = session

    def repair_artifact(self, artifact_id: int, max_attempts: int = 3) -> bool:
        artifact = self.artifact_repo.get_artifact_by_id(artifact_id)
        if not artifact:
            raise ArtifactNotFoundError(f"Artifact with id {artifact_id} not found.")

        for attempt in range(max_attempts):
            result = self.validation_service.validate_artifact(artifact_id)

            if result.success:
                artifact_entity = self.session.query(CompiledMultifact).get(artifact_id)
                artifact_entity.valid = True
                self.session.commit()
                return True
            else:
                error_summary = self._summarize_errors(result.errors)
                new_code = self.code_fixer_service.fix_code(
                    artifact.code, error_summary
                )
                # Update artifact with new code and set valid=False until next validation
                self.artifact_repo.update_artifact_code(
                    artifact_id, new_code, valid=False
                )

        # After max attempts, final check
        final_result = self.validation_service.validate_artifact(artifact_id)
        if final_result.success:
            artifact_entity = self.session.query(CompiledMultifact).get(artifact_id)
            artifact_entity.valid = True
            self.session.commit()
            return True
        else:
            # Mark as invalid if needed
            self.artifact_repo.update_artifact_code(
                artifact_id, artifact.code, valid=False
            )
            return False

    def _summarize_errors(self, errors: List[ValidationError]) -> str:
        lines = ["Found the following TypeScript errors:"]
        for err in errors:
            lines.append(f"{err.file}({err.line},{err.char}): {err.message}")
        return "\n".join(lines)
