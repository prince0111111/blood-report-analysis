"""
Custom exceptions for the Clinical Reasoning Engine.
"""


class KnowledgeEngineError(Exception):
    """Base exception for the knowledge engine."""


class RegistryError(KnowledgeEngineError):
    """Raised when the registry cannot load knowledge."""


class KnowledgeFileError(KnowledgeEngineError):
    """Raised when a knowledge file is invalid."""


class PatternValidationError(KnowledgeEngineError):
    """Raised when a pattern fails validation."""


class MatchError(KnowledgeEngineError):
    """Raised when pattern matching fails."""