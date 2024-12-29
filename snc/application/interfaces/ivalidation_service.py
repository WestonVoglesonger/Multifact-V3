"""Interface for the validation service."""

from typing import List
from abc import ABC, abstractmethod


class ValidationError:
    """Represents a validation error with file location and message."""

    def __init__(self, file: str, line: int, char: int, message: str):
        """Initialize validation error.

        Args:
            file: Path to the file containing the error
            line: Line number where error occurred
            char: Character position where error occurred
            message: Description of the error
        """
        self.file = file
        self.line = line
        self.char = char
        self.message = message


class ValidationResult:
    """Result of a validation operation with success status and errors."""

    def __init__(self, success: bool, errors: List[ValidationError]):
        """Initialize validation result.

        Args:
            success: Whether validation passed
            errors: List of validation errors if any
        """
        self.success = success
        self.errors = errors


class IValidationService(ABC):
    """Interface for validating artifacts."""

    @abstractmethod
    def validate_artifact(self, artifact_id: int) -> ValidationResult:
        """Validate the artifact identified by artifact_id.

        Args:
            artifact_id: ID of the artifact to validate

        Returns:
            ValidationResult with success=True if valid,
            or success=False with a list of ValidationError otherwise.
        """
        pass
