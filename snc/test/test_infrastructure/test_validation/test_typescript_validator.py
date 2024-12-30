import pytest
from pathlib import Path
from typing import List, Any
import subprocess
from unittest.mock import patch

from snc.infrastructure.validation.validators.typescript_validator import (
    TypeScriptValidator,
)
from snc.application.interfaces.ivalidation_service import (
    ValidationError,
    ValidationResult,
)


@pytest.fixture
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


def test_validate_decorator_syntax(typescript_validator: TypeScriptValidator):
    code = """
    @Component({
      selector: invalid-selector,  // Missing quotes
      template: '<div></div'  // Unclosed tag
    })
    export class MyComponent {}
    """
    result = typescript_validator.validate(code)
    assert not result.success
    assert len(result.errors) >= 1
    # Print actual error messages for debugging
    print("\nDecorator syntax errors:")
    for error in result.errors:
        print(f"- {error.message}")
    # tsc reports this as a syntax error with missing comma or unexpected token
    assert any(
        "," in error.message.lower()
        or "expected" in error.message.lower()
        or "cannot find name" in error.message.lower()
        for error in result.errors
    )


def test_validate_interface_implementation(typescript_validator: TypeScriptValidator):
    code = """
    interface UserService {
      getUser(): User;
    }
    class BadImplementation implements UserService {
      // Missing implementation of getUser()
    }
    """
    result = typescript_validator.validate(code)
    assert not result.success
    assert any("implement" in error.message.lower() for error in result.errors)


def test_validate_generic_types(typescript_validator: TypeScriptValidator):
    code = """
    function processItems<T>(items: T[]): number {
      return "not a number";  // Type error with generics
    }
    """
    result = typescript_validator.validate(code)
    assert not result.success
    assert any(
        "type 'string' is not assignable to type 'number'" in error.message.lower()
        for error in result.errors
    )


def test_validate_async_promise(typescript_validator: TypeScriptValidator):
    code = """
    async function getData(): Promise<string> {
      return 42;  // Wrong return type for Promise
    }
    """
    result = typescript_validator.validate(code)
    assert not result.success
    assert any(
        "type 'number' is not assignable to type 'string'" in error.message.lower()
        for error in result.errors
    )


def test_validate_module_imports(typescript_validator: TypeScriptValidator):
    code = """
    import { NonExistentComponent } from './non-existent';
    export { UnexportedThing };
    """
    result = typescript_validator.validate(code)
    assert not result.success
    assert any("cannot find module" in error.message.lower() for error in result.errors)


def test_validate_template_type_checking(typescript_validator: TypeScriptValidator):
    code = """
    import { Component } from '@angular/core';
    @Component({
      template: '{{ user.nonexistentProperty }}'
    })
    export class MyComponent {
      user: { name: string };
    }
    """
    result = typescript_validator.validate(code)
    assert not result.success
    # tsc reports this as a property access error
    assert any(
        "property" in error.message.lower() or "cannot find name" in error.message.lower()
        for error in result.errors
    )


def test_validate_lifecycle_methods(typescript_validator: TypeScriptValidator):
    code = """
    import { OnInit } from '@angular/core';
    export class MyComponent implements OnInit {
      ngOnInit(param: string): void {}  // Wrong signature
    }
    """
    result = typescript_validator.validate(code)
    assert not result.success
    # Print actual error messages for debugging
    print("\nLifecycle method errors:")
    for error in result.errors:
        print(f"- {error.message}")
    # tsc reports this as a method implementation error
    assert any(
        "implement" in error.message.lower()
        or "signature" in error.message.lower()
        or "property" in error.message.lower()
        for error in result.errors
    )


def test_validate_type_assertions(typescript_validator: TypeScriptValidator):
    code = """
    let num: number = "string" as any as number;  // Unsafe type assertion
    num.toFixed(2);  // This could fail at runtime
    """
    result = typescript_validator.validate(code)
    assert not result.success
    assert any("type assertion" in error.message.lower() for error in result.errors)


def test_validate_enum_declarations(typescript_validator: TypeScriptValidator):
    """Test validation of enum declarations."""
    code = """
    enum Direction {
        Up = "UP"
        Down = "DOWN"  // Missing comma
    }
    const dir: Direction = "LEFT";  // Invalid enum value
    """
    result = typescript_validator.validate(code)
    assert not result.success
    assert len(result.errors) > 0
    # Print actual error messages for debugging
    print("\nEnum validation errors:")
    for error in result.errors:
        print(f"- {error.message}")
    # Check for various ways tsc might report the syntax error
    assert any(
        "," in error.message.lower()
        or "expected" in error.message.lower()
        or "syntax" in error.message.lower()
        for error in result.errors
    )


def test_validate_abstract_class(typescript_validator: TypeScriptValidator):
    """Test validation of abstract classes."""
    code = """
    abstract class Animal {
        abstract makeSound(): void;
        abstract get age(): number;
    }
    class Dog extends Animal {
        // Missing implementation of abstract members
    }
    """
    result = typescript_validator.validate(code)
    assert not result.success
    assert any(
        "non-abstract class" in error.message.lower() and "implement" in error.message.lower()
        for error in result.errors
    )


def test_validate_union_types(typescript_validator: TypeScriptValidator):
    """Test validation of union types."""
    code = """
    type Status = "active" | "inactive" | "pending";
    let status: Status = "unknown";  // Invalid union type value

    type NumberOrString = number | string;
    const value: NumberOrString = true;  // Type error
    """
    result = typescript_validator.validate(code)
    assert not result.success
    assert any(
        "type 'boolean' is not assignable" in error.message.lower() for error in result.errors
    )


def test_validate_mapped_types(typescript_validator: TypeScriptValidator):
    """Test validation of mapped types."""
    code = """
    interface Person {
        name: string;
        age: number;
    }
    type ReadonlyPerson = {
        readonly [K in keyof Person]: Person[K]
    };
    let person: ReadonlyPerson = { name: "John", age: "25" };  // Type error in age
    person.name = "Jane";  // Error: readonly property
    """
    result = typescript_validator.validate(code)
    assert not result.success
    assert any(
        "readonly" in error.message.lower()
        or "type 'string' is not assignable to type 'number'" in error.message.lower()
        for error in result.errors
    )


def test_validate_conditional_types(typescript_validator: TypeScriptValidator):
    """Test validation of conditional types."""
    code = """
    type TypeName<T> = T extends string
        ? "string"
        : T extends number
        ? "number"
        : "object";

    const name: TypeName<boolean> = "string";  // Type error
    """
    result = typescript_validator.validate(code)
    assert not result.success
    assert any(
        "type" in error.message.lower() and "assignable" in error.message.lower()
        for error in result.errors
    )


def test_validate_decorators_with_parameters(typescript_validator: TypeScriptValidator):
    """Test validation of decorators with parameters."""
    code = """
    function log(target: any, key: string, descriptor: PropertyDescriptor) {
        // Decorator implementation
    }

    class Calculator {
        @log()  // Error: decorator function must be called without parentheses
        add(a: number, b: number): number {
            return a + b;
        }
    }
    """
    result = typescript_validator.validate(code)
    assert not result.success
    assert any("decorator" in error.message.lower() for error in result.errors)


def test_validate_namespace_declarations(typescript_validator: TypeScriptValidator):
    """Test validation of namespace declarations."""
    code = """
    namespace Validation {
        export interface StringValidator {
            isValid(s: string): boolean;
        }

        class InvalidClass implements StringValidator {
            // Missing implementation
        }
    }

    let validator: Validation.StringValidator = new Validation.InvalidClass();  // Error
    """
    result = typescript_validator.validate(code)
    assert not result.success
    assert any("implement" in error.message.lower() for error in result.errors)


def test_validate_index_signatures(typescript_validator: TypeScriptValidator):
    """Test validation of index signatures."""
    code = """
    interface StringMap {
        [key: string]: string;
    }

    let map: StringMap = {
        key1: "value1",
        key2: 42  // Type error: number not assignable to string
    };
    """
    result = typescript_validator.validate(code)
    assert not result.success
    assert any(
        "type 'number' is not assignable to type 'string'" in error.message.lower()
        for error in result.errors
    )


def test_validate_semicolon_rules(typescript_validator: TypeScriptValidator):
    """Test validation of semicolon rules with different statement types."""
    code = """
    const x = 5  // Missing semicolon after declaration
    let y = 10   // Missing semicolon after declaration
    var z = 15   // Missing semicolon after declaration
    return x + y // Missing semicolon after return
    function test() {
        const obj = {
            key: "value"  // No semicolon needed in object literal
        }
        return {
            result: true  // No semicolon needed in object literal
        }
    }
    """
    result = typescript_validator.validate(code)
    assert not result.success
    assert len(result.errors) >= 4  # Should catch all missing semicolons
    assert any("Missing semicolon" in error.message for error in result.errors)


def test_validate_complex_angular_component(typescript_validator: TypeScriptValidator):
    """Test validation of a complex Angular component with multiple features."""
    code = """
    import { Component, OnInit, Input } from '@angular/core';
    import { FormGroup, FormBuilder } from '@angular/forms';

    @Component({
        selector app-test,  // Invalid selector format
        template: '<div>
            <form [formGroup]="form">
                <input formControlName="name">
                {{ nonexistentProperty }}  // Property doesn't exist
            </form>
        </div>'  // Malformed template
    })
    export class TestComponent implements OnInit {
        @Input() data: any;  // Using any type
        form: FormGroup;

        constructor(private fb: FormBuilder) {
            this.form = this.fb.group({
                name: ['']
            });
        }

        ngOnInit(param: string) {  // Wrong signature
            this.loadData()  // Missing semicolon
        }

        private loadData() {
            const x: number = "string";  // Type error
            return x;
        }
    }
    """
    result = typescript_validator.validate(code)
    assert not result.success
    print("\nComplex Angular component errors:")
    for error in result.errors:
        print(f"- {error.message}")
    assert len(result.errors) >= 5  # Should catch multiple types of errors


def test_validate_advanced_types(typescript_validator: TypeScriptValidator):
    """Test validation of advanced TypeScript type features."""
    code = """
    // Intersection types
    type Combined = { name: string } & { age: number };
    const invalid: Combined = { name: "John" };  // Missing age property

    // Literal types
    type Status = "active" | "inactive";
    const status: Status = "pending";  // Invalid literal

    // Mapped types with modifiers
    type Optional<T> = { [K in keyof T]?: T[K] };
    type Required<T> = { [K in keyof T]-?: T[K] };

    // Invalid use of mapped types
    interface User { name: string; age: number; }
    const user: Required<User> = { name: "John" };  // Missing required age

    // Template literal types
    type EmailLocale = `${string}@${string}.${string}`;
    const email: EmailLocale = "invalid-email";  // Invalid format

    // Recursive types
    type TreeNode<T> = {
        value: T;
        children: TreeNode<T>[];
    }
    const invalidNode: TreeNode<number> = {
        value: "string",  // Type error
        children: []
    };
    """
    result = typescript_validator.validate(code)
    assert not result.success
    print("\nAdvanced types errors:")
    for error in result.errors:
        print(f"- {error.message}")
    assert len(result.errors) >= 4  # Should catch various type errors


def test_validate_error_handling(typescript_validator: TypeScriptValidator):
    """Test validation error handling for malformed code and edge cases."""
    code = """
    // Malformed import
    import { from './module';

    // Invalid decorator syntax
    @decorator(
    class Test {
        // Unterminated string
        str: string = "unclosed

        // Invalid type cast
        num = <number>"123";

        // Malformed function
        test( {
            return
        }
    }
    """
    result = typescript_validator.validate(code)
    assert not result.success
    print("\nError handling test errors:")
    for error in result.errors:
        print(f"- {error.message}")
    assert len(result.errors) >= 3  # Should catch syntax errors


def test_validate_tsconfig_options(typescript_validator: TypeScriptValidator):
    """Test validation with different TypeScript compiler options."""
    code = """
    // Test strict null checks
    function process(value: string | null) {
        console.log(value.length);  // Potential null reference
    }

    // Test no implicit any
    function calculate(x, y) {  // Missing type annotations
        return x + y;
    }

    // Test strict property initialization
    class User {
        name: string;  // Property not initialized
        constructor() {}
    }

    // Test no implicit returns
    function getValue(flag: boolean) {
        if (flag) {
            return 42;
        }
        // Missing return in else branch
    }
    """
    result = typescript_validator.validate(code)
    assert not result.success
    print("\nTypeScript config validation errors:")
    for error in result.errors:
        print(f"- {error.message}")
    assert len(result.errors) >= 4  # Should catch various compiler option violations


def test_validate_npm_install_failure(typescript_validator: TypeScriptValidator):
    """Test validation when npm install fails."""
    code = """
    import { Component } from '@angular/core';

    @Component({
        selector: 'app-test',
        template: '<div>{{ message }}</div>'
    })
    export class TestComponent {
        message: string = "Hello World";
    }
    """

    with patch("subprocess.run") as mock_run:
        # Force subprocess.run to raise a CalledProcessError
        mock_run.side_effect = subprocess.CalledProcessError(
            returncode=1,
            cmd="npm install --prefix /fake_dir",
            output="npm ERR! code E404\nnpm ERR! 404 Not Found",
            stderr="npm ERR! 404 Not Found",
        )

        result = typescript_validator.validate(code)
        assert not result.success
        assert len(result.errors) > 0
        assert any("Failed to install dependencies" in error.message for error in result.errors)


def test_validate_unusual_tsc_output(typescript_validator: TypeScriptValidator):
    """Test validation when tsc produces unusual error output."""
    code = """
    // Invalid TypeScript code that might trigger unusual compiler output
    import { NonExistentModule } from '@angular/core';
    """

    with patch("subprocess.run") as mock_run:
        # Mock tsc output with unusual error format
        mock_proc = subprocess.CompletedProcess(
            args=[],
            returncode=2,
            stdout="error TS2307: Cannot find module '@angular/core' or its corresponding type declarations.",
            stderr="",
        )
        mock_run.return_value = mock_proc

        result = typescript_validator.validate(code)
        assert not result.success
        assert len(result.errors) > 0
        assert any("Cannot find module" in error.message for error in result.errors)


def test_validate_strict_mode(typescript_validator: TypeScriptValidator):
    """Test validation with strict mode enabled."""
    code = """
    function greet(name) {  // Parameter 'name' implicitly has an 'any' type
        return "Hello " + name.toUpperCase();
    }

    let value;  // Variable 'value' implicitly has an 'any' type
    value = greet(42);  // Argument of type 'number' is not assignable to parameter of type 'string'
    """

    with patch("subprocess.run") as mock_run:
        # Mock tsc output with strict mode errors
        mock_proc = subprocess.CompletedProcess(
            args=[],
            returncode=2,
            stdout="""
            code.ts(1,14): error TS7006: Parameter 'name' implicitly has an 'any' type.
            code.ts(5,5): error TS7008: Member 'value' implicitly has an 'any' type.
            code.ts(6,17): error TS2345: Argument of type 'number' is not assignable to parameter of type 'string'.
            """,
            stderr="",
        )
        mock_run.return_value = mock_proc

        result = typescript_validator.validate(code)
        assert not result.success
        assert len(result.errors) >= 3
        assert any("implicitly has an 'any' type" in error.message for error in result.errors)
        assert any(
            "not assignable to parameter of type 'string'" in error.message
            for error in result.errors
        )


def test_validate_tsc_timeout(typescript_validator: TypeScriptValidator):
    """Test validation when TypeScript compiler times out."""
    code = """
    // Some valid TypeScript code
    function example(): void {
        console.log("Hello, World!");
    }
    """

    with patch("subprocess.run") as mock_run:

        def mock_subprocess_run(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess:
            if "npm" in args[0]:
                # Let npm install succeed
                return subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
            else:
                # Make tsc timeout
                raise subprocess.TimeoutExpired(
                    cmd="tsc",
                    timeout=30,
                    output="Partial compilation output...",
                    stderr="Compilation timed out",
                )

        mock_run.side_effect = mock_subprocess_run

        result = typescript_validator.validate(code)
        assert not result.success
        assert len(result.errors) > 0
        assert any("timed out" in error.message.lower() for error in result.errors)


def test_validate_npm_install_stderr(typescript_validator: TypeScriptValidator):
    """Test validation when npm install produces stderr output."""
    code = "const x: number = 1;"

    with patch("subprocess.run") as mock_run:
        # Mock npm install with stderr output but successful return code
        def mock_subprocess_run(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess:
            if "npm" in args[0]:
                return subprocess.CompletedProcess(
                    args=[], returncode=0, stdout="", stderr="npm WARN deprecated package@1.0.0"
                )
            return subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")

        mock_run.side_effect = mock_subprocess_run
        result = typescript_validator.validate(code)
        assert result.success
        assert len(result.errors) == 0


def test_validate_tsc_stderr(typescript_validator: TypeScriptValidator):
    """Test validation when tsc produces stderr output."""
    code = "const x: number = 1;"

    with patch("subprocess.run") as mock_run:

        def mock_subprocess_run(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess:
            if "npm" in args[0]:
                return subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
            return subprocess.CompletedProcess(
                args=[],
                returncode=1,
                stdout="",
                stderr="error TS18003: No inputs were found in config file.",
            )

        mock_run.side_effect = mock_subprocess_run
        result = typescript_validator.validate(code)
        assert not result.success
        assert len(result.errors) > 0
        assert any("No inputs were found" in error.message for error in result.errors)


def test_validate_special_error_format(typescript_validator: TypeScriptValidator):
    """Test validation with special error message format."""
    code = """
    import { Component } from '@angular/core';

    @Component({
        template: '<div>{{ nonexistentProperty }}</div>'
    })
    export class TestComponent {}
    """

    with patch("subprocess.run") as mock_run:

        def mock_subprocess_run(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess:
            if "npm" in args[0]:
                return subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
            return subprocess.CompletedProcess(
                args=[],
                returncode=1,
                stdout="error TS2339: Property 'nonexistentProperty' does not exist.",
                stderr="",
            )

        mock_run.side_effect = mock_subprocess_run
        result = typescript_validator.validate(code)
        assert not result.success
        assert len(result.errors) > 0
        assert any("does not exist" in error.message for error in result.errors)


def test_validate_strict_mode_config(typescript_validator: TypeScriptValidator):
    """Test validation with strict mode configuration."""
    code = """
    function example(param) {  // Parameter 'param' implicitly has an 'any' type
        return param.length;
    }
    """

    with patch("subprocess.run") as mock_run:

        def mock_subprocess_run(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess:
            if "npm" in args[0]:
                return subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
            return subprocess.CompletedProcess(
                args=[],
                returncode=1,
                stdout="""
                code.ts(1,17): error TS7006: Parameter 'param' implicitly has an 'any' type.
                code.ts(2,16): error TS2571: Object is of type 'unknown'.
                """,
                stderr="",
            )

        mock_run.side_effect = mock_subprocess_run
        result = typescript_validator.validate(code)
        assert not result.success
        assert len(result.errors) >= 2
        assert any("implicitly has an 'any' type" in error.message for error in result.errors)
        assert any("Object is of type 'unknown'" in error.message for error in result.errors)


def test_validate_advanced_config(typescript_validator: TypeScriptValidator):
    """Test validation with advanced TypeScript configuration."""
    code = """
    import { Component } from '@angular/core';

    @Component({
        template: `
            <div *ngFor="let item of items">
                {{ item.nonexistentProperty }}
            </div>
        `
    })
    export class TestComponent {
        items = [{ name: 'test' }];
    }
    """

    with patch("subprocess.run") as mock_run:

        def mock_subprocess_run(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess:
            if "npm" in args[0]:
                return subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
            return subprocess.CompletedProcess(
                args=[],
                returncode=1,
                stdout="""
                code.ts(7,24): error TS2339: Property 'nonexistentProperty' does not exist on type '{ name: string; }'.
                """,
                stderr="",
            )

        mock_run.side_effect = mock_subprocess_run
        result = typescript_validator.validate(code)
        assert not result.success
        assert len(result.errors) > 0
        assert any("does not exist on type" in error.message for error in result.errors)


def test_validate_tsc_compilation_error(typescript_validator: TypeScriptValidator):
    """Test validation when tsc compilation fails with a specific error."""
    code = """
    import { Component } from '@angular/core';

    @Component({
        selector: 'app-test',
        template: '<div>{{ message }</div>'  // Missing closing brace
    })
    export class TestComponent {
        message: string = "Hello World";
    }
    """

    with patch("subprocess.run") as mock_run:

        def mock_subprocess_run(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess:
            if "npm" in args[0]:
                return subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
            return subprocess.CompletedProcess(
                args=[],
                returncode=1,
                stdout="",
                stderr="""
                code.ts(6,32): error TS1005: '>' expected.
                code.ts(6,33): error TS1002: Unterminated string literal.
                """,
            )

        mock_run.side_effect = mock_subprocess_run
        result = typescript_validator.validate(code)
        assert not result.success
        assert len(result.errors) >= 2
        assert any("expected" in error.message.lower() for error in result.errors)
        assert any("unterminated string" in error.message.lower() for error in result.errors)


def test_validate_special_error_handling(typescript_validator: TypeScriptValidator):
    """Test validation with special error handling cases."""
    code = """
    import { Component } from '@angular/core';

    @Component({
        selector: 'app-test',
        template: '<div>{{ message }}</div>'
    })
    export class TestComponent {
        message: string = "Hello World"  // Missing semicolon
        private router: Router;  // Router not imported
    }
    """

    with patch("subprocess.run") as mock_run:

        def mock_subprocess_run(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess:
            if "npm" in args[0]:
                return subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
            return subprocess.CompletedProcess(
                args=[],
                returncode=1,
                stdout="""
                code.ts(9,43): error TS1005: ';' expected.
                code.ts(10,21): error TS2304: Cannot find name 'Router'.
                """,
                stderr="",
            )

        mock_run.side_effect = mock_subprocess_run
        result = typescript_validator.validate(code)
        assert not result.success
        assert len(result.errors) >= 2
        assert any("';' expected" in error.message for error in result.errors)
        assert any("Cannot find name 'Router'" in error.message for error in result.errors)


def test_validate_advanced_angular_config(typescript_validator: TypeScriptValidator):
    """Test validation with advanced Angular configuration."""
    code = """
    import { Component, OnInit } from '@angular/core';
    import { FormBuilder, FormGroup, Validators } from '@angular/forms';

    @Component({
        selector: 'app-test',
        template: `
            <form [formGroup]="form" (ngSubmit)="onSubmit()">
                <input formControlName="name" required>
                <span *ngIf="form.get('name').hasError('required')">
                    Name is required
                </span>
            </form>
        `
    })
    export class TestComponent implements OnInit {
        form: FormGroup;

        constructor(private fb: FormBuilder) {}

        ngOnInit(): void {
            this.form = this.fb.group({
                name: ['', [Validators.required]]
            });
        }

        onSubmit(): void {
            if (this.form.valid) {
                console.log(this.form.value);
            }
        }
    }
    """

    with patch("subprocess.run") as mock_run:

        def mock_subprocess_run(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess:
            if "npm" in args[0]:
                return subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
            return subprocess.CompletedProcess(
                args=[],
                returncode=1,
                stdout="""
                code.ts(10,28): error TS2339: Property 'hasError' does not exist on type 'AbstractControl'.
                code.ts(21,17): error TS2345: Argument of type 'string[]' is not assignable to parameter of type 'ValidatorFn'.
                """,
                stderr="",
            )

        mock_run.side_effect = mock_subprocess_run
        result = typescript_validator.validate(code)
        assert not result.success
        assert len(result.errors) >= 2
        assert any("does not exist on type" in error.message for error in result.errors)
        assert any("is not assignable to parameter" in error.message for error in result.errors)


def test_validate_advanced_typescript_features(typescript_validator: TypeScriptValidator):
    """Test validation of advanced TypeScript features with various error conditions."""
    code = """
    // Test strict mode features
    function strictTest(value) {  // Missing type annotation
        return value.length;  // Potential null reference
    }

    // Test advanced configuration
    interface Complex<T> {
        data: T;
        process(): void;
    }

    class Implementation implements Complex<string> {
        data: string;
        // Missing process method
    }

    // Test special error handling
    @Component({
        template: `
            <div *customDirective="let item from items">
                {{ item.missing?.property }}
            </div>
        `
    })
    class TestComponent {
        items: any[];  // Using any type in strict mode
    }
    """

    with patch("subprocess.run") as mock_run:

        def mock_subprocess_run(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess:
            if "npm" in args[0]:
                return subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
            return subprocess.CompletedProcess(
                args=[],
                returncode=1,
                stdout="""
                code.ts(2,19): error TS7006: Parameter 'value' implicitly has an 'any' type.
                code.ts(3,16): error TS18048: 'value' is possibly 'undefined'.
                code.ts(13,7): error TS2420: Class 'Implementation' incorrectly implements interface 'Complex<string>'.
                code.ts(20,24): error TS2339: Property 'missing' does not exist on type 'any'.
                code.ts(25,16): error TS7005: Variable 'items' implicitly has an 'any[]' type.
                """,
                stderr="Some additional error information",
            )

        mock_run.side_effect = mock_subprocess_run
        result = typescript_validator.validate(code)
        assert not result.success
        assert len(result.errors) >= 5
        assert any("implicitly has an 'any' type" in error.message for error in result.errors)
        assert any("possibly 'undefined'" in error.message for error in result.errors)
        assert any("incorrectly implements interface" in error.message for error in result.errors)
        assert any("does not exist on type" in error.message for error in result.errors)
        assert any("implicitly has an 'any[]' type" in error.message for error in result.errors)


def test_validate_edge_cases(typescript_validator: TypeScriptValidator):
    """Test validation of edge cases and error handling scenarios."""
    code = """
    // Test strict mode and advanced configuration
    @Component({
        template: `
            <div *ngFor="let item of items">
                {{ item?.property }}
            </div>
        `
    })
    class TestComponent {
        private items: any[];  // Using any type in strict mode

        constructor() {
            this.items = [{ property: 'test' }];
        }

        ngOnInit() {
            const result = this.processItems();
            console.log(result);
        }

        private processItems(): string {
            return this.items
                .map(item => item.property)
                .join(', ');
        }
    }
    """

    with patch("subprocess.run") as mock_run:

        def mock_subprocess_run(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess:
            if "npm" in args[0]:
                # Test npm install with warnings
                return subprocess.CompletedProcess(
                    args=[], returncode=0, stdout="", stderr="npm WARN deprecated package@1.0.0"
                )
            # Test tsc with various error formats
            return subprocess.CompletedProcess(
                args=[],
                returncode=1,
                stdout="""
                code.ts(11,23): error TS7005: Variable 'items' implicitly has an 'any[]' type.
                code.ts(18,13): error TS7006: Parameter 'result' implicitly has an 'any' type.
                code.ts(23,16): error TS7006: Parameter 'item' implicitly has an 'any' type.
                """,
                stderr="""
                error TS18003: No inputs were found in config file.
                error TS6059: File is not under 'rootDir'.
                """,
            )

        mock_run.side_effect = mock_subprocess_run
        result = typescript_validator.validate(code)
        assert not result.success
        assert len(result.errors) >= 5
        # Check for various error types
        assert any("implicitly has an 'any[]' type" in error.message for error in result.errors)
        assert any("implicitly has an 'any' type" in error.message for error in result.errors)
        assert any("No inputs were found" in error.message for error in result.errors)
        assert any("File is not under 'rootDir'" in error.message for error in result.errors)


def test_validate_advanced_configuration(typescript_validator: TypeScriptValidator):
    """Test validation with advanced TypeScript configuration and error handling."""
    code = """
    // Test strict mode and advanced configuration
    @Component({
        template: `
            <div *ngFor="let item of items">
                {{ item?.property }}
            </div>
        `
    })
    class TestComponent {
        private items: any[];  // Using any type in strict mode

        constructor() {
            this.items = [{ property: 'test' }];
        }

        ngOnInit() {
            const result = this.processItems();
            console.log(result);
        }

        private processItems(): string {
            return this.items
                .map(item => item.property)
                .join(', ');
        }
    }
    """

    with patch("subprocess.run") as mock_run:

        def mock_subprocess_run(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess:
            if "npm" in args[0]:
                # Test npm install with compilation error
                return subprocess.CompletedProcess(
                    args=[],
                    returncode=1,
                    stdout="",
                    stderr="npm ERR! code ENOENT\nnpm ERR! syscall spawn tsc\nnpm ERR! path tsc",
                )
            # Test tsc with various error formats and configurations
            return subprocess.CompletedProcess(
                args=[],
                returncode=1,
                stdout="""
                code.ts(11,23): error TS7005: Variable 'items' implicitly has an 'any[]' type.
                code.ts(18,13): error TS7006: Parameter 'result' implicitly has an 'any' type.
                code.ts(23,16): error TS7006: Parameter 'item' implicitly has an 'any' type.
                """,
                stderr="""
                error TS18003: No inputs were found in config file.
                error TS6059: File is not under 'rootDir'.
                error TS5023: Unknown compiler option 'strictPropertyInitialization'.
                error TS5042: Option 'project' cannot be mixed with source files on a command line.
                """,
            )

        mock_run.side_effect = mock_subprocess_run
        result = typescript_validator.validate(code)
        assert not result.success
        assert len(result.errors) >= 7
        # Check for various error types
        assert any("implicitly has an 'any[]' type" in error.message for error in result.errors)
        assert any("implicitly has an 'any' type" in error.message for error in result.errors)
        assert any("No inputs were found" in error.message for error in result.errors)
        assert any("File is not under 'rootDir'" in error.message for error in result.errors)
        assert any("Unknown compiler option" in error.message for error in result.errors)
        assert any("cannot be mixed with source files" in error.message for error in result.errors)


def _validate_code(validator: TypeScriptValidator, code: str, tmp_path: Path) -> ValidationResult:
    """Helper function to validate TypeScript code."""
    return validator.validate(code)
