from snc.application.interfaces.ivalidation_service import ValidationResult
import re


class TypeScriptValidator:
    def validate(self, code: str, token_content: str) -> ValidationResult:
        """
        Validate TypeScript code against token requirements.
        """
        # First check for basic syntax errors
        if not self._check_basic_syntax(code):
            return ValidationResult(success=False, errors=["Invalid TypeScript syntax"])

        # Extract expected class name from token content
        class_name = self._extract_class_name(token_content)
        if class_name and not self._check_class_exists(code, class_name):
            return ValidationResult(
                success=False,
                errors=[f"Expected class '{class_name}' not found in code"],
            )

        # Extract expected method names from token content
        method_names = self._extract_method_names(token_content)
        for method in method_names:
            if not self._check_method_exists(code, method):
                return ValidationResult(
                    success=False,
                    errors=[f"Expected method '{method}' not found in code"],
                )

        return ValidationResult(success=True, errors=[])

    def _check_basic_syntax(self, code: str) -> bool:
        """
        Check for basic TypeScript syntax errors.
        """
        # Check for matching curly braces
        if code.count("{") != code.count("}"):
            return False

        # Check for matching parentheses
        if code.count("(") != code.count(")"):
            return False

        # Check for basic class structure
        if "class" in code and not re.search(r"class\s+\w+\s*{", code):
            return False

        return True

    def _extract_class_name(self, token_content: str) -> str:
        """
        Extract expected class name from token content.
        """
        match = re.search(r"component\s+named\s+(\w+)", token_content.lower())
        if match:
            return match.group(1)
        return ""

    def _check_class_exists(self, code: str, class_name: str) -> bool:
        """
        Check if a class with the given name exists in the code.
        """
        pattern = rf"class\s+{class_name}\b"
        return bool(re.search(pattern, code))

    def _extract_method_names(self, token_content: str) -> list[str]:
        """
        Extract expected method names from token content.
        """
        methods = []
        for line in token_content.split("\n"):
            match = re.search(r"method\s+(\w+)", line.lower())
            if match:
                methods.append(match.group(1))
        return methods

    def _check_method_exists(self, code: str, method_name: str) -> bool:
        """
        Check if a method with the given name exists in the code.
        """
        pattern = rf"\b{method_name}\s*\([^)]*\)\s*{{?"
        return bool(re.search(pattern, code))
