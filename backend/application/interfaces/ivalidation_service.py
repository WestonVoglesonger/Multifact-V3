from typing import List
from abc import ABC, abstractmethod


class ValidationError:
    def __init__(self, file: str, line: int, char: int, message: str):
        self.file = file
        self.line = line
        self.char = char
        self.message = message


class ValidationResult:
    def __init__(self, success: bool, errors: List[ValidationError]):
        self.success = success
        self.errors = errors


class IValidationService(ABC):
    @abstractmethod
    def validate_artifact(self, artifact_id: int) -> ValidationResult:
        """
        Validate the artifact identified by artifact_id.

        Returns a ValidationResult object with success=True if valid,
        or success=False with a list of ValidationError otherwise.
        """
        pass
