import pytest
from backend.application.interfaces.ivalidation_service import (
    IValidationService,
    ValidationResult,
)


def test_ivalidation_service_is_abstract():
    with pytest.raises(
        TypeError, match="Can't instantiate abstract class IValidationService"
    ):
        IValidationService()  # type: ignore


def test_ivalidation_service_minimal_subclass():
    class MinimalValidationService(IValidationService):
        def validate_artifact(self, artifact_id: int) -> ValidationResult:
            return ValidationResult(success=True, errors=[])

    svc = MinimalValidationService()
    result = svc.validate_artifact(123)
    assert result.success is True
    assert result.errors == []
