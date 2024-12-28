class TokenDiffError(Exception):
    pass


class LLMParsingError(Exception):
    pass


class ArtifactNotFoundError(ValueError):
    pass


class DocumentNotFoundError(ValueError):
    pass


class TokenNotFoundError(ValueError):
    pass


class TokenNameCollisionError(Exception):
    pass


class TokenizationError(Exception):
    """Raised when there is an error during tokenization."""

    pass


class CompilationError(Exception):
    """Raised when there is an error during code compilation."""

    pass


class ValidationError(Exception):
    """Raised when there is an error during code validation."""

    pass


class CodeFixerError(Exception):
    """Raised when there is an error during code fixing."""

    pass


class SelfRepairError(Exception):
    """Raised when there is an error during self-repair process."""

    pass
