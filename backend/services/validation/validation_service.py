# backend/services/validation/validation_service.py
import os
import yaml
from typing import List
from sqlalchemy.orm import Session
from sqlalchemy import select
from backend.entities.compiled_multifact import CompiledMultifact
from backend.entities.ni_token import NIToken
from backend.entities.ni_document import NIDocument
import re
from subprocess import run


class ValidationError:
    def __init__(self, file: str, line: int, char: int, message: str):
        self.file = file
        self.line = line
        self.char = char
        self.message = message

    def __repr__(self):
        return f"ValidationError(file={self.file}, line={self.line}, char={self.char}, message={self.message})"


class ValidationResult:
    def __init__(self, success: bool, errors: List[ValidationError]):
        self.success = success
        self.errors = errors

    def __repr__(self):
        return f"ValidationResult(success={self.success}, errors={self.errors})"


class ValidationService:
    """
    Coordinates validation by:
    - Determining language from artifact or NI
    - Loading the correct validator
    - Running checks and returning results
    """

    _CONFIG = None

    @staticmethod
    def _load_config():
        if ValidationService._CONFIG is None:
            config_path = os.path.join(os.path.dirname(__file__), "validators", "config.yml")
            with open(config_path, 'r') as f:
                ValidationService._CONFIG = yaml.safe_load(f)
        return ValidationService._CONFIG

    @staticmethod
    def validate_artifact(artifact_id: int, session: Session) -> ValidationResult:
        artifact = session.scalars(
            select(CompiledMultifact).where(CompiledMultifact.id == artifact_id)
        ).first()
        if not artifact:
            raise ValueError(f"Artifact with id {artifact_id} not found.")

        token = session.get(NIToken, artifact.ni_token_id)
        ni_doc = session.get(NIDocument, token.ni_document_id)
        ni_content = ni_doc.content

        # Derive expectations
        expectations = ValidationService._derive_expectations_from_ni(ni_content)

        # Determine language (for demo, let's assume artifact.language)
        language = artifact.language.lower()  # e.g. "typescript"

        validator = ValidationService._get_validator(language)

        # Run syntax/type check
        errors = validator.run_syntax_type_check(artifact.code)
        success = (len(errors) == 0)

        if success:
            # Run semantic checks
            sem_errors = validator.run_semantic_checks(artifact.code, expectations)
            errors.extend(sem_errors)
            success = (len(errors) == 0)

        artifact.valid = success
        session.commit()

        return ValidationResult(success=success, errors=errors)

    @staticmethod
    def _derive_expectations_from_ni(ni_content: str) -> dict:
        component_pattern = re.compile(r"component\s+named\s+(\w+)", re.IGNORECASE)
        method_pattern = re.compile(r"method\s+(\w+)", re.IGNORECASE)

        expected_components = component_pattern.findall(ni_content)
        expected_methods = method_pattern.findall(ni_content)

        return {
            "expected_components": expected_components,
            "expected_methods": expected_methods
        }

    @staticmethod
    def _get_validator(language: str):
        config = ValidationService._load_config()
        validators_config = config.get("validators", {})
        lang_cfg = validators_config.get(language)
        if not lang_cfg:
            raise ValueError(f"No validator configured for language: {language}")
        class_name = lang_cfg["class"]
        tool = lang_cfg.get("tool", "")

        # Dynamically import and instantiate the validator class
        # Assuming classes are in backend.services.validation.validators namespace
        module_path = "backend.services.validation.validators"
        validator_module = __import__(module_path, fromlist=[class_name])
        validator_class = getattr(validator_module, class_name)
        return validator_class(tool=tool)