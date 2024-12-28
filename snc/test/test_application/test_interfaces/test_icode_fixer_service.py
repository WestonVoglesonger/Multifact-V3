import pytest
from snc.application.interfaces.icode_fixer_service import ICodeFixerService


def test_icode_fixer_service_is_abstract():
    with pytest.raises(
        TypeError, match="Can't instantiate abstract class ICodeFixerService"
    ):
        ICodeFixerService()  # type: ignore


def test_icode_fixer_service_minimal_subclass():
    class MinimalCodeFixer(ICodeFixerService):
        def fix_code(self, original_code: str, error_summary: str) -> str:
            return "fixed_code"

    fixer = MinimalCodeFixer()
    assert fixer.fix_code("some_code", "some_error") == "fixed_code"
