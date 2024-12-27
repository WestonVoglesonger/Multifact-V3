import os
import yaml
import re
from typing import List
from backend.application.interfaces.ivalidation_service import IValidationService, ValidationResult, ValidationError
from backend.domain.models import DomainCompiledMultifact
from sqlalchemy.orm import Session
from backend.infrastructure.entities.compiled_multifact import CompiledMultifact
from backend.infrastructure.entities.ni_token import NIToken
from backend.infrastructure.entities.ni_document import NIDocument
from sqlalchemy import select

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
        self.session = session
        self.config = self._load_config()

    def validate_artifact(self, artifact_id: int) -> ValidationResult:
        # 1) Fetch artifact entity
        artifact_ent = self.session.scalars(
            select(CompiledMultifact).where(CompiledMultifact.id == artifact_id)
        ).first()
        if not artifact_ent:
            raise ValueError(f"Artifact with id {artifact_id} not found.")

        # 2) Create the TS validator (or pick by language)
        validator = self._get_validator("typescript")

        # 3) Relaxed syntax check first
        errors = validator.run_syntax_type_check(artifact_ent.code, strict_mode=False)
        success = len(errors) == 0

        if success:
            # 4) If syntax is good, do optional semantic checks
            token_ent = self.session.get(NIToken, artifact_ent.ni_token_id)
            if token_ent:
                doc_ent = self.session.get(NIDocument, token_ent.ni_document_id)
                if doc_ent:
                    # Example: derive expectations from doc content
                    # e.g. "component named X", "method doStuff", etc.
                    expectations = {}
                    sem_errors = validator.run_semantic_checks(artifact_ent.code, expectations)
                    errors.extend(sem_errors)
                    success = len(sem_errors) == 0

        # Mark valid/invalid
        artifact_ent.valid = success

        # 5) Always assign a score/feedback to avoid None
        if success:
            artifact_ent.score = 8.0
            artifact_ent.feedback = "Looks good!"
        else:
            # If invalid, give a minimal score
            artifact_ent.score = 2.0
            artifact_ent.feedback = "Some TS compilation or semantic errors."

        self.session.commit()
        return ValidationResult(success=success, errors=errors)

    def _derive_expectations_from_ni(self, ni_content: str) -> dict:
        component_pattern = re.compile(r"component\s+named\s+(\w+)", re.IGNORECASE)
        method_pattern = re.compile(r"method\s+(\w+)", re.IGNORECASE)

        expected_components = component_pattern.findall(ni_content)
        expected_methods = method_pattern.findall(ni_content)

        return {
            "expected_components": expected_components,
            "expected_methods": expected_methods
        }

    def _load_config(self):
        if self._CONFIG is None:
            # Assume config.yml is in the same directory as this file
            config_path = os.path.join(os.path.dirname(__file__), "validators", "config.yml")
            with open(config_path, 'r') as f:
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
        module_path = "backend.infrastructure.validation.validators"
        validator_module = __import__(module_path, fromlist=[class_name])
        validator_class = getattr(validator_module, class_name)
        return validator_class(tool=tool)
