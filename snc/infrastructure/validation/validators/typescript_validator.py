"""TypeScript validator for Angular code."""

import os
import tempfile
import subprocess
import json
import logging
import re
from typing import List, Dict

from snc.application.interfaces.ivalidation_service import (
    ValidationResult,
    ValidationError as IValidationError,
)
from snc.infrastructure.validation.validators.base import CodeValidator


logger = logging.getLogger(__name__)


class TypeScriptValidator(CodeValidator):
    """TypeScript validator for Angular code."""

    def __init__(self, tool: str = "tsc"):
        """Initialize the validator.

        Args:
            tool: TypeScript compiler command (default: tsc)
        """
        self.tool = tool

    def run_syntax_type_check(self, code: str, strict_mode: bool = False) -> List[IValidationError]:
        """Run syntax and type checking on code.

        Args:
            code: Code to check
            strict_mode: Whether to use strict mode

        Returns:
            List of validation errors
        """
        errors = []

        # Check for basic syntax errors first
        lines = code.splitlines()
        brace_count = 0
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue

            # Check for missing semicolons
            if (
                not line.endswith(";")
                and not line.endswith("{")
                and not line.endswith("}")
                and not line.endswith('"')
                and not line.endswith("'")
                and any(line.strip().startswith(kw) for kw in ["return", "const", "let", "var"])
            ):
                errors.append(self._create_error("Missing semicolon", i + 1, len(line)))

            # Track braces
            brace_count += line.count("{") - line.count("}")

            # Check Angular decorator syntax
            if "@Component" in line:
                next_line = lines[i + 1] if i + 1 < len(lines) else ""
                if "selector:" in next_line and not ('"' in next_line or "'" in next_line):
                    errors.append(
                        self._create_error(
                            "Invalid selector format - missing quotes",
                            i + 2,
                            next_line.find("selector:") + 1,
                        )
                    )
                if "template:" in next_line:
                    template_line = next_line.strip()
                    if template_line.count("'") % 2 != 0 or template_line.count('"') % 2 != 0:
                        errors.append(
                            self._create_error(
                                "Unclosed template string", i + 2, next_line.find("template:") + 1
                            )
                        )

            # Check lifecycle method signatures
            if "ngOnInit" in line:
                if "(" in line and ")" in line:
                    params = line[line.find("(") + 1 : line.find(")")]
                    if params.strip():
                        errors.append(
                            self._create_error(
                                "ngOnInit should not have parameters", i + 1, line.find("(") + 1
                            )
                        )

            # Check type assertions
            if " as " in line:
                if "as any as" in line:
                    errors.append(
                        self._create_error(
                            "Unsafe type assertion using 'any'", i + 1, line.find("as any as") + 1
                        )
                    )

        # Check for missing closing braces
        if brace_count > 0:
            errors.append(self._create_error("Missing closing brace", len(lines), 1))

        # Run tsc for additional checks
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create package.json
            package = {
                "name": "temp-validator",
                "version": "1.0.0",
                "dependencies": {
                    "@angular/core": "^16.0.0",
                    "@angular/common": "^16.0.0",
                    "@angular/router": "^16.0.0",
                    "@angular/forms": "^16.0.0",
                    "@angular/compiler": "^16.0.0",
                    "@angular/compiler-cli": "^16.0.0",
                    "rxjs": "^7.0.0",
                    "typescript": "~5.0.0",
                },
            }
            with open(os.path.join(temp_dir, "package.json"), "w") as f:
                json.dump(package, f)

            # Create tsconfig.json with template type checking enabled
            tsconfig = {
                "compilerOptions": {
                    "target": "ES2020",
                    "module": "ESNext",
                    "moduleResolution": "node",
                    "strict": True,
                    "noImplicitAny": True,
                    "strictNullChecks": True,
                    "strictFunctionTypes": True,
                    "strictBindCallApply": True,
                    "strictPropertyInitialization": True,
                    "noImplicitThis": True,
                    "alwaysStrict": True,
                    "noUnusedLocals": True,
                    "noUnusedParameters": True,
                    "noImplicitReturns": True,
                    "noFallthroughCasesInSwitch": True,
                    "noUncheckedIndexedAccess": True,
                    "noImplicitOverride": True,
                    "noPropertyAccessFromIndexSignature": True,
                    "esModuleInterop": True,
                    "skipLibCheck": True,
                    "forceConsistentCasingInFileNames": True,
                    "experimentalDecorators": True,
                    "emitDecoratorMetadata": True,
                    "noEmit": True,
                    "baseUrl": ".",
                    "paths": {"@angular/*": ["node_modules/@angular/*"]},
                    "allowUnreachableCode": False,
                    "allowUnusedLabels": False,
                    "exactOptionalPropertyTypes": True,
                    "noPropertyAccessFromIndexSignature": True,
                    "noUncheckedIndexedAccess": True,
                    "noUnusedLocals": True,
                    "noUnusedParameters": True,
                    "preserveConstEnums": True,
                    "strictBindCallApply": True,
                    "strictFunctionTypes": True,
                    "strictNullChecks": True,
                    "strictPropertyInitialization": True,
                    "useUnknownInCatchVariables": True,
                    "lib": ["ES2020", "DOM"],
                    "allowJs": False,
                    "checkJs": False,
                    "maxNodeModuleJsDepth": 0,
                    "noErrorTruncation": True,
                    "preserveWatchOutput": False,
                    "pretty": False,
                    "extendedDiagnostics": True,
                },
                "angularCompilerOptions": {
                    "fullTemplateTypeCheck": True,
                    "strictTemplates": True,
                    "strictInjectionParameters": True,
                    "strictInputAccessModifiers": True,
                    "strictTemplateTypeChecking": True,
                },
            }
            with open(os.path.join(temp_dir, "tsconfig.json"), "w") as f:
                json.dump(tsconfig, f)

            # Write the code to a .ts file
            ts_file = os.path.join(temp_dir, "code.ts")
            with open(ts_file, "w") as f:
                f.write(code)

            # Install dependencies
            try:
                logger.info("Installing dependencies...")
                result = subprocess.run(
                    ["npm", "install", "--prefix", temp_dir],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                logger.info("npm install output: %s", result.stdout)
                if result.stderr:
                    logger.warning("npm install stderr: %s", result.stderr)
            except subprocess.CalledProcessError as e:
                logger.error("Failed to install dependencies: %s", str(e))
                return [self._create_error(f"Failed to install dependencies: {str(e)}")]

            # Run tsc
            logger.info("Running tsc...")
            try:
                result = subprocess.run(
                    [
                        self.tool,
                        "--project",
                        temp_dir,
                        "--noEmit",
                        "--pretty",
                        "false",
                        "--extendedDiagnostics",
                        "--noErrorTruncation",
                        "--preserveWatchOutput",
                        "--diagnostics",
                    ],
                    capture_output=True,
                    text=True,
                )

                logger.info("tsc exit code: %d", result.returncode)
                logger.info("tsc stdout: %s", result.stdout)
                if result.stderr:
                    logger.info("tsc stderr: %s", result.stderr)

                # Parse errors from tsc output
                if result.returncode != 0:
                    # Combine stdout and stderr since tsc writes errors to both
                    output = result.stdout + result.stderr
                    for line in output.splitlines():
                        # Skip tsconfig errors
                        if "tsconfig.json" in line:
                            continue

                        # Match error lines like: code.ts(2,5): error TS1005: '}' expected.
                        # or: code.ts(2,5): error TS2322: Type 'string' is not assignable to type 'number'.
                        match = re.search(r"code\.ts\((\d+),(\d+)\): error TS\d+: (.+)", line)
                        if match:
                            line_num = int(match.group(1))
                            char_num = int(match.group(2))
                            message = match.group(3).strip()
                            errors.append(self._create_error(message, line_num, char_num))
                            logger.info(
                                "Found error: %s at line %d, char %d", message, line_num, char_num
                            )
                        # Also match errors without line numbers
                        elif "error TS" in line and not line.startswith("../tmp/"):
                            message = line.split("error TS")[1].split(":", 1)[1].strip()
                            errors.append(self._create_error(message))
                            logger.info("Found error: %s", message)

            except subprocess.CalledProcessError as e:
                logger.error("TypeScript compilation failed: %s", str(e))
                errors.append(self._create_error(f"TypeScript compilation failed: {str(e)}"))
            except Exception as e:
                logger.error("Validation error: %s", str(e))
                errors.append(self._create_error(f"Validation error: {str(e)}"))

        return errors

    def validate(
        self, code: str, expectations: Dict[str, List[str]] | None = None
    ) -> ValidationResult:
        """Validate TypeScript code using tsc.

        Args:
            code: Code to validate
            expectations: Optional semantic expectations

        Returns:
            Validation result with errors if any
        """
        if not code.strip():
            return ValidationResult(success=True, errors=[])

        errors = self.run_syntax_type_check(code)
        if expectations:
            errors.extend(self.run_semantic_checks(code, expectations))

        return ValidationResult(success=len(errors) == 0, errors=errors)

    def run_semantic_checks(
        self, code: str, expectations: Dict[str, List[str]]
    ) -> List[IValidationError]:
        """Run semantic checks on TypeScript code.

        Args:
            code: TypeScript code to check
            expectations: Expected components and methods

        Returns:
            List of validation errors
        """
        import re

        errors = []

        # Check for expected component class
        if "expected_components" in expectations:
            for component in expectations["expected_components"]:
                pattern = rf"export\s+class\s+{component}\b"
                if not re.search(pattern, code, re.IGNORECASE):
                    errors.append(
                        self._create_error(f"TSSEM001: Expected class '{component}' not found")
                    )

        # Check for expected methods
        if "expected_methods" in expectations:
            for method in expectations["expected_methods"]:
                pattern = rf"\b{method}\s*\([^)]*\)"
                if not re.search(pattern, code, re.IGNORECASE):
                    errors.append(
                        self._create_error(f"TSSEM002: Expected method '{method}' not found")
                    )

        return errors

    def _create_error(self, message: str, line: int = 1, char: int = 1) -> IValidationError:
        """Create a validation error.

        Args:
            message: Error message
            line: Line number (1-based)
            char: Character position (1-based)

        Returns:
            Validation error
        """
        return IValidationError(
            message=message,
            file="",
            line=line,
            char=char,
        )
