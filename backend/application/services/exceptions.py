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
