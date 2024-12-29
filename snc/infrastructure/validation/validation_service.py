"""Service for validating compiled artifacts."""

import os
import yaml
import re
from typing import Dict, Any, List
from snc.application.interfaces.ivalidation_service import (
    IValidationService,
    ValidationResult,
    ValidationError,
)
from sqlalchemy.orm import Session
from snc.infrastructure.entities.compiled_multifact import CompiledMultifact
from snc.infrastructure.validation.validators import TypeScriptValidator
import threading
from snc.infrastructure.entities.ni_token import NIToken
from snc.infrastructure.entities.ni_document import NIDocument


class ConcreteValidationService(IValidationService):
    """Service for validating compiled artifacts.

    This service:
    - Loads validator config
    - Finds and instantiates the correct validator
    - Retrieves artifact code and related NI content
    - Runs syntax and semantic checks
    - Updates artifact validity
    """

    _CONFIG = None

    def __init__(self, session: Session):
        """Initialize the validation service.

        Args:
            session: Database session to use
        """
        self._main_session = session
        self._thread_local = threading.local()
        self._thread_local.session = session
        self._validators = {"typescript": TypeScriptValidator()}

    @property
    def session(self) -> Session:
        """Get the current thread's database session."""
        return self._thread_local.session

    @session.setter
    def session(self, new_session: Session) -> None:
        """Set the current thread's database session.

        Args:
            new_session: New session to use
        """
        self._thread_local.session = new_session

    def validate_artifact(self, artifact_id: int) -> ValidationResult:
        """Validate a compiled artifact.

        Args:
            artifact_id: ID of artifact to validate

        Returns:
            Validation result with success status and any errors

        Raises:
            ValueError: If artifact is not found or if no validator is configured for the language
        """
        # Get the artifact
        artifact = (
            self._thread_local.session.query(CompiledMultifact)
            .filter(CompiledMultifact.id == artifact_id)
            .one_or_none()
        )
        if not artifact:
            raise ValueError(f"Artifact with id {artifact_id} not found")

        # Check if we have a validator for this language
        if artifact.language not in self._validators:
            raise ValueError(
                f"No validator configured for language: {artifact.language}"
            )

        # Get the token and document content for semantic validation
        token = (
            self._thread_local.session.query(NIToken)
            .filter(NIToken.id == artifact.ni_token_id)
            .one_or_none()
        )
        if not token:
            raise ValueError(f"Token not found for artifact {artifact_id}")

        doc = (
            self._thread_local.session.query(NIDocument)
            .filter(NIDocument.id == token.ni_document_id)
            .one_or_none()
        )
        if not doc:
            raise ValueError(f"Document not found for token {token.id}")

        try:
            # Get semantic expectations from document content
            expectations = self._derive_expectations_from_ni(doc.content)

            # Get the appropriate validator and validate the code
            validator = self._validators[artifact.language]
            validation_result = validator.validate(artifact.code, expectations)

            # Update artifact validity based on validation result
            artifact.valid = validation_result.success
            try:
                self._thread_local.session.commit()
            except:
                self._thread_local.session.rollback()
                raise

            return validation_result

        except Exception as e:
            return ValidationResult(
                success=False,
                errors=[
                    ValidationError(
                        message=str(e),
                        file="",
                        line=0,
                        char=0,
                    )
                ],
            )

    def _derive_expectations_from_ni(self, ni_content: str) -> Dict[str, List[str]]:
        """Derive expected components and methods from NI content.

        Args:
            ni_content: Natural instruction content to parse

        Returns:
            Dict with expected components and methods
        """
        component_pattern = re.compile(r"component\s+named\s+(\w+)", re.IGNORECASE)
        method_pattern = re.compile(r"method\s+(\w+)", re.IGNORECASE)

        expected_components = component_pattern.findall(ni_content)
        expected_methods = method_pattern.findall(ni_content)

        return {
            "expected_components": expected_components,
            "expected_methods": expected_methods,
        }

    def _load_config(self) -> Dict[str, Any]:
        """Load validator configuration from YAML file.

        Returns:
            Configuration dictionary
        """
        if self._CONFIG is None:
            # Assume config.yml is in the same directory as this file
            config_path = os.path.join(
                os.path.dirname(__file__), "validators", "config.yml"
            )
            with open(config_path, "r") as f:
                self._CONFIG = yaml.safe_load(f)
        return self._CONFIG

    def _get_validator(self, language: str) -> Any:
        """Get validator instance for a language.

        Args:
            language: Programming language to get validator for

        Returns:
            Validator instance

        Raises:
            ValueError: If no validator configured for language
        """
        config = self._load_config()
        validators_config = config.get("validators", {})
        lang_cfg = validators_config.get(language)
        if not lang_cfg:
            raise ValueError(f"No validator configured for language: {language}")

        class_name = lang_cfg["class"]
        tool = lang_cfg.get("tool", "")

        # Assuming validators are in the same package
        module_path = "snc.infrastructure.validation.validators"
        validator_module = __import__(module_path, fromlist=[class_name])
        validator_class = getattr(validator_module, class_name)
        return validator_class(tool=tool)
