"""Custom exceptions for the System Narrative Compiler services."""


class TokenDiffError(Exception):
    """Raised when there is an error during token diffing operations."""


class LLMParsingError(Exception):
    """Raised when there is an error parsing LLM responses."""


class ArtifactNotFoundError(ValueError):
    """Raised when a requested artifact cannot be found in the repository."""


class DocumentNotFoundError(ValueError):
    """Raised when a requested document cannot be found in the repository."""


class TokenNotFoundError(ValueError):
    """Raised when a requested token cannot be found in the repository."""


class TokenNameCollisionError(Exception):
    """Raised when attempting to create a token with a duplicate name."""


class TokenizationError(Exception):
    """Raised when there is an error during tokenization.

    This can occur when parsing document content into tokens fails.
    """


class CompilationError(Exception):
    """Raised when there is an error during code compilation.

    This can occur when the LLM fails to generate valid code for a token.
    """


class ValidationError(Exception):
    """Raised when there is an error during code validation.

    This can occur when generated code fails to meet validation criteria.
    """


class CodeFixerError(Exception):
    """Raised when there is an error during code fixing.

    This can occur when attempting to fix invalid code automatically fails.
    """


class SelfRepairError(Exception):
    """Raised when there is an error during self-repair process.

    This can occur when the automatic repair of invalid tokens fails.
    """
