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
        self.typescript_validator = TypeScriptValidator()

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
        """
        try:
            # Get the artifact
            artifact = (
                self._thread_local.session.query(CompiledMultifact)
                .filter(CompiledMultifact.id == artifact_id)
                .one_or_none()
            )
            if not artifact:
                return ValidationResult(
                    success=False,
                    errors=[
                        ValidationError(
                            message=f"Artifact {artifact_id} not found",
                            file="",
                            line=0,
                            char=0,
                        )
                    ],
                )

            # Validate the code
            validation_result = self.typescript_validator.validate(
                artifact.code
            )
            if not validation_result.success:
                artifact.valid = False
                self._thread_local.session.commit()

            return validation_result

        except Exception as e:
            self._thread_local.session.rollback()
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

    def _derive_expectations_from_ni(
        self, ni_content: str
    ) -> Dict[str, List[str]]:
        """Derive expected components and methods from NI content.
        
        Args:
            ni_content: Natural instruction content to parse
            
        Returns:
            Dict with expected components and methods
        """
        component_pattern = re.compile(
            r"component\s+named\s+(\w+)", re.IGNORECASE
        )
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
            raise ValueError(
                f"No validator configured for language: {language}"
            )

        class_name = lang_cfg["class"]
        tool = lang_cfg.get("tool", "")

        # Assuming validators are in the same package
        module_path = "snc.infrastructure.validation.validators"
        validator_module = __import__(module_path, fromlist=[class_name])
        validator_class = getattr(validator_module, class_name)
        return validator_class(tool=tool)
