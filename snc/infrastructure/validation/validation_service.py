import os
import yaml
import re
from typing import List, Optional
from snc.application.interfaces.ivalidation_service import (
    IValidationService,
    ValidationResult,
    ValidationError,
)
from snc.domain.models import DomainCompiledMultifact
from sqlalchemy.orm import Session
from snc.infrastructure.entities.compiled_multifact import CompiledMultifact
from snc.infrastructure.entities.ni_token import NIToken
from snc.infrastructure.entities.ni_document import NIDocument
from sqlalchemy import select
from snc.infrastructure.validation.validators import TypeScriptValidator
import threading


class ConcreteValidationService(IValidationService):
    """
    The ConcreteValidationService replaces the legacy ValidationService.
    It:
    - Loads validator config
    - Finds and instantiates the correct validator
    - Retrieves artifact code and related NI content
    - Runs syntax and semantic checks
    - Updates artifact validity
    """

    _CONFIG = None

    def __init__(self, session: Session):
        self._main_session = session
        self._thread_local = threading.local()
        self._thread_local.session = session
        self.typescript_validator = TypeScriptValidator()

    @property
    def session(self) -> Session:
        return self._thread_local.session

    @session.setter
    def session(self, new_session: Session) -> None:
        self._thread_local.session = new_session

    def validate_artifact(self, artifact_id: int) -> ValidationResult:
        """Validate a compiled artifact."""
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
                        ValidationError(message=f"Artifact {artifact_id} not found")
                    ],
                )

            # Validate the code
            validation_result = self.typescript_validator.validate(artifact.code)
            if not validation_result.success:
                artifact.valid = False
                self._thread_local.session.commit()

            return validation_result

        except Exception as e:
            self._thread_local.session.rollback()
            return ValidationResult(
                success=False,
                errors=[ValidationError(message=str(e))],
            )

    def _derive_expectations_from_ni(self, ni_content: str) -> dict:
        component_pattern = re.compile(r"component\s+named\s+(\w+)", re.IGNORECASE)
        method_pattern = re.compile(r"method\s+(\w+)", re.IGNORECASE)

        expected_components = component_pattern.findall(ni_content)
        expected_methods = method_pattern.findall(ni_content)

        return {
            "expected_components": expected_components,
            "expected_methods": expected_methods,
        }

    def _load_config(self):
        if self._CONFIG is None:
            # Assume config.yml is in the same directory as this file
            config_path = os.path.join(
                os.path.dirname(__file__), "validators", "config.yml"
            )
            with open(config_path, "r") as f:
                self._CONFIG = yaml.safe_load(f)
        return self._CONFIG

    def _get_validator(self, language: str):
        validators_config = self.config.get("validators", {})
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
