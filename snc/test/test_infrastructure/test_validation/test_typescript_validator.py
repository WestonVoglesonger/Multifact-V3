import pytest
from pathlib import Path
from typing import List

from snc.infrastructure.validation.validators.typescript_validator import (
    TypeScriptValidator,
)
from snc.application.interfaces.ivalidation_service import (
    ValidationError,
    ValidationResult,
)


def typescript_validator() -> TypeScriptValidator:
    """Create a TypeScript validator instance."""
    return TypeScriptValidator()


def test_validate_valid_typescript(typescript_validator: TypeScriptValidator, tmp_path: Path):
    """Test validation of valid TypeScript code."""
    valid_code = """
    function greet(name: string): string {
        return `Hello, ${name}!`;
    }

    interface User {
        id: number;
        name: string;
    }

    class UserGreeter {
        constructor(private user: User) {}

        greet(): string {
            return greet(this.user.name);
        }
    }
    """

    result = _validate_code(typescript_validator, valid_code, tmp_path)
    assert result.success is True
    assert len(result.errors) == 0


def test_validate_syntax_error(typescript_validator: TypeScriptValidator, tmp_path: Path):
    """Test validation of TypeScript code with syntax errors."""
    invalid_code = """
    function brokenFunction(
        console.log("Missing closing parenthesis";
    """

    result = _validate_code(typescript_validator, invalid_code, tmp_path)
    assert result.success is False
    assert len(result.errors) > 0
    assert any("')' expected" in error.message for error in result.errors)


def test_validate_type_error(typescript_validator: TypeScriptValidator, tmp_path: Path):
    """Test validation of TypeScript code with type errors."""
    code_with_type_error = """
    function add(a: number, b: number): number {
        return a + "b";  // Type error: can't add number and string
    }
    """

    result = _validate_code(typescript_validator, code_with_type_error, tmp_path)
    assert result.success is False
    assert len(result.errors) > 0
    assert any(
        "string" in error.message.lower() and "number" in error.message.lower()
        for error in result.errors
    )


def test_validate_missing_imports(typescript_validator: TypeScriptValidator, tmp_path: Path):
    """Test validation of TypeScript code with missing imports."""
    code_with_missing_import = """
    const router = new Router();  // Router is not imported
    """

    result = _validate_code(typescript_validator, code_with_missing_import, tmp_path)
    assert result.success is False
    assert len(result.errors) > 0
    assert any("cannot find name 'router'" in error.message.lower() for error in result.errors)


def test_validate_angular_component(typescript_validator: TypeScriptValidator, tmp_path: Path):
    """Test validation of an Angular component."""
    angular_component = """
    import { Component } from '@angular/core';

    @Component({
        selector: 'app-test',
        template: '<div>{{ message }}</div>'
    })
    export class TestComponent {
        message: string = "Hello World";
    }
    """

    result = _validate_code(typescript_validator, angular_component, tmp_path)
    assert result.success is True
    assert len(result.errors) == 0


def test_validate_multiple_errors(typescript_validator: TypeScriptValidator, tmp_path: Path):
    """Test validation of code with multiple errors."""
    code_with_multiple_errors = """
    function test(a: number, b: string): boolean {
        const result = a + b;  // Type error
        return result  // Missing semicolon and type mismatch
    """  # Missing closing brace

    result = _validate_code(typescript_validator, code_with_multiple_errors, tmp_path)
    assert result.success is False
    assert len(result.errors) > 1  # Should have multiple errors


def test_validate_empty_code(typescript_validator: TypeScriptValidator, tmp_path: Path):
    """Test validation of empty code."""
    result = _validate_code(typescript_validator, "", tmp_path)
    assert result.success is True  # Empty file is technically valid TypeScript
    assert len(result.errors) == 0


def _validate_code(validator: TypeScriptValidator, code: str, tmp_path: Path) -> ValidationResult:
    """Helper function to validate TypeScript code."""
    test_file = tmp_path / "test.ts"
    test_file.write_text(code)
    return validator.validate(str(test_file))
