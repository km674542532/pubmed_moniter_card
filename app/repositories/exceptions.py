"""Repository-level exceptions with clear error semantics."""


class RepositoryError(Exception):
    """Base exception for repository operations."""


class NotFoundError(RepositoryError):
    """Raised when an expected record does not exist."""


class DuplicateConstraintError(RepositoryError):
    """Raised when a uniqueness constraint is violated."""
