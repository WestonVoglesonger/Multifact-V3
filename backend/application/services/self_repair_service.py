from typing import List
from backend.application.interfaces.iartifact_repository import IArtifactRepository
from backend.application.interfaces.icode_fixer_service import ICodeFixerService
from backend.application.interfaces.ivalidation_service import IValidationService
from backend.application.services.exceptions import ArtifactNotFoundError
from backend.application.services.exceptions import LLMParsingError
from backend.domain.models import DomainCompiledMultifact, DomainToken
from backend.application.interfaces.ivalidation_service import ValidationResult, ValidationError

class SelfRepairService:
    def __init__(self, 
                 artifact_repo: IArtifactRepository, 
                 validation_service: IValidationService, 
                 code_fixer_service: ICodeFixerService):
        self.artifact_repo = artifact_repo
        self.validation_service = validation_service
        self.code_fixer_service = code_fixer_service

    def repair_artifact(self, artifact_id: int, max_attempts: int = 3) -> bool:
        artifact = self.artifact_repo.get_artifact_by_id(artifact_id)
        if not artifact:
            raise ArtifactNotFoundError(f"Artifact with id {artifact_id} not found.")

        for attempt in range(max_attempts):
            result = self.validation_service.validate_artifact(artifact_id)

            if result.success:
                return True
            else:
                error_summary = self._summarize_errors(result.errors)
                new_code = self.code_fixer_service.fix_code(artifact.code, error_summary)
                # Update artifact with new code and set valid=False until next validation
                self.artifact_repo.update_artifact_code(artifact_id, new_code, valid=False)

        # After max attempts, final check
        final_result = self.validation_service.validate_artifact(artifact_id)
        if final_result.success:
            return True
        else:
            # Mark as invalid if needed
            self.artifact_repo.update_artifact_code(artifact_id, artifact.code, valid=False)
            return False

    def _summarize_errors(self, errors: List[ValidationError]) -> str:
        lines = ["Found the following TypeScript errors:"]
        for err in errors:
            lines.append(f"{err.file}({err.line},{err.char}): {err.message}")
        return "\n".join(lines)
