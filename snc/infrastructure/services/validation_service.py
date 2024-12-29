from snc.application.interfaces.ivalidation_service import (
    IValidationService,
    ValidationResult,
    ValidationError,
)
from snc.infrastructure.entities.compiled_multifact import CompiledMultifact
from snc.infrastructure.entities.ni_token import NIToken
from snc.infrastructure.validation.validators.typescript_validator import (
    TypeScriptValidator,
)
from snc.infrastructure.entities.ni_document import NIDocument
from sqlalchemy.orm import Session
import yaml
import os
from typing import Dict, List
import re


class ConcreteValidationService(IValidationService):
    def __init__(self, session: Session):
        self.session = session
        self.validators = {
            "typescript": TypeScriptValidator(),
            # Add other validators here
        }

    def validate_artifact(self, artifact_id: int) -> ValidationResult:
        """Validate a compiled artifact."""
        artifact = self.session.get(CompiledMultifact, artifact_id)
        if not artifact:
            raise ValueError(f"No artifact found with ID {artifact_id}")

        # Get the validator for this language
        language = artifact.language.lower()
        validator = self.validators.get(language)
        if validator is None:  # Explicitly check for None
            raise ValueError(
                f"No validator configured for language: {artifact.language}"
            )

        # Get the document content for semantic validation
        token = self.session.get(NIToken, artifact.ni_token_id)
        if not token:
            return ValidationResult(
                success=False,
                errors=[
                    ValidationError(file="", line=0, char=0, message="Token not found")
                ],
            )

        doc = self.session.get(NIDocument, token.ni_document_id)
        if not doc:
            return ValidationResult(
                success=False,
                errors=[
                    ValidationError(
                        file="", line=0, char=0, message="Document not found"
                    )
                ],
            )

        # Run syntax checks
        syntax_errors = validator.run_syntax_type_check(artifact.code)
        if syntax_errors:
            return ValidationResult(success=False, errors=syntax_errors)

        # Extract semantic expectations from document
        expectations = self._parse_expectations(doc.content)

        # Run semantic validation
        semantic_errors = validator.run_semantic_checks(artifact.code, expectations)
        if semantic_errors:
            return ValidationResult(success=False, errors=semantic_errors)

        return ValidationResult(success=True, errors=[])

    def _parse_expectations(self, content: str) -> Dict[str, List[str]]:
        """Parse document content to extract expected components and methods."""
        expectations: Dict[str, List[str]] = {
            "expected_components": [],
            "expected_methods": [],
        }

        # Extract component names
        comp_matches = re.finditer(r"component named (\w+)", content)
        expectations["expected_components"].extend(
            match.group(1) for match in comp_matches
        )

        # Extract method names
        method_matches = re.finditer(r"method (\w+)", content)
        expectations["expected_methods"].extend(
            match.group(1) for match in method_matches
        )

        return expectations
