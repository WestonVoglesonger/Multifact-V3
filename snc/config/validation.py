"""
Configuration validation module.
"""

from dataclasses import dataclass
from typing import Dict, Optional
import re


@dataclass
class ValidationResult:
    """Result of a configuration validation."""

    is_valid: bool
    message: str


def validate_database_url(url: str) -> ValidationResult:
    """Validate database URL format."""
    valid_schemes = ["sqlite", "postgresql", "mysql"]
    try:
        scheme = url.split("://")[0]
        if scheme not in valid_schemes:
            return ValidationResult(
                False,
                f"Invalid database scheme. Must be one of: {', '.join(valid_schemes)}",
            )
        return ValidationResult(True, "Valid database URL")
    except IndexError:
        return ValidationResult(False, "Invalid database URL format")


def validate_api_key(key: str, provider: str) -> ValidationResult:
    """Validate API key format."""
    patterns = {"openai": r"^sk-[A-Za-z0-9]{48}$", "groq": r"^gsk_[A-Za-z0-9]{48}$"}
    if provider not in patterns:
        return ValidationResult(False, f"Unknown provider: {provider}")

    pattern = patterns[provider]
    if re.match(pattern, key):
        return ValidationResult(True, f"Valid {provider} API key")
    return ValidationResult(False, f"Invalid {provider} API key format")


def validate_log_level(level: str) -> ValidationResult:
    """Validate log level."""
    valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    if level.upper() in valid_levels:
        return ValidationResult(True, "Valid log level")
    return ValidationResult(
        False, f"Invalid log level. Must be one of: {', '.join(valid_levels)}"
    )


def validate_log_file(path: str) -> ValidationResult:
    """Validate log file path."""
    try:
        from pathlib import Path

        log_dir = Path(path).parent
        if not log_dir.exists():
            return ValidationResult(False, f"Log directory does not exist: {log_dir}")
        return ValidationResult(True, "Valid log file path")
    except Exception as e:
        return ValidationResult(False, f"Invalid log file path: {str(e)}")


def validate_config(config: Dict[str, str]) -> Dict[str, ValidationResult]:
    """Validate all configuration settings."""
    results = {}

    if "DATABASE_URL" in config:
        results["DATABASE_URL"] = validate_database_url(config["DATABASE_URL"])

    if "OPENAI_API_KEY" in config:
        results["OPENAI_API_KEY"] = validate_api_key(config["OPENAI_API_KEY"], "openai")

    if "GROQ_API_KEY" in config:
        results["GROQ_API_KEY"] = validate_api_key(config["GROQ_API_KEY"], "groq")

    if "LOG_LEVEL" in config:
        results["LOG_LEVEL"] = validate_log_level(config["LOG_LEVEL"])

    if "LOG_FILE" in config:
        results["LOG_FILE"] = validate_log_file(config["LOG_FILE"])

    return results
