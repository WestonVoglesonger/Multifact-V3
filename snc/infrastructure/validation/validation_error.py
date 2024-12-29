"""Validation error class for code validation."""

import re


class ValidationError:
    """Represents a validation error from code validation.
    
    Attributes:
        message: The error message
        file: The file where the error occurred
        line: The line number where the error occurred (1-based)
        char: The character position where the error occurred (1-based)
        error_code: The error code (e.g. TS2307)
        severity: The severity level (error, warning, info)
    """

    def __init__(
        self,
        message: str,
        file: str = "",
        line: int = 0,
        char: int = 0,
        error_code: str = "",
        severity: str = "error",
    ):
        """Initialize a validation error.

        Args:
            message: The error message
            file: The file where the error occurred
            line: The line number where the error occurred (1-based)
            char: The character position where the error occurred (1-based)
            error_code: The error code (e.g. TS2307)
            severity: The severity level (error, warning, info)
        """
        self.message = message
        self.file = file
        self.line = line
        self.char = char
        self.error_code = error_code
        self.severity = severity

        # Try to parse TypeScript error format
        # Example: file.ts(10,5): error TS2307: Cannot find module
        ts_pattern = (
            r"(.+?)\((\d+),(\d+)\):\s*(error|warning)\s+(TS\d+):\s*(.+)"
        )
        ts_match = re.match(ts_pattern, message)
        if ts_match:
            self.file = ts_match.group(1).strip()
            self.line = int(ts_match.group(2))
            self.char = int(ts_match.group(3))
            self.severity = ts_match.group(4)
            self.error_code = ts_match.group(5)
            self.message = ts_match.group(6).strip()

    def __str__(self) -> str:
        """Return a string representation of the error.
        
        Returns:
            String in format: file(line,char): severity code: message
        """
        location = f"{self.file}({self.line},{self.char})" if self.file else ""
        code = f"{self.error_code}: " if self.error_code else ""
        return f"{location}: {self.severity} {code}{self.message}"

    def __repr__(self) -> str:
        """Return a detailed string representation of the error.
        
        Returns:
            String with all attributes in constructor format
        """
        return (
            f"ValidationError(message='{self.message}', file='{self.file}', "
            f"line={self.line}, char={self.char}, "
            f"error_code='{self.error_code}', severity='{self.severity}')"
        )
