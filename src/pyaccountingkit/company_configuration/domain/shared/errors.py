"""Stable, non-transport-specific failures for Company Configuration."""


class DomainError(ValueError):
    """Base for predictable domain rejections, never raw infrastructure failures."""

    code = "DOMAIN_ERROR"

    def __init__(self, message: str):
        super().__init__(message)


class InvalidIdentifier(DomainError):
    code = "INVALID_IDENTIFIER"


class InvalidScope(DomainError):
    code = "INVALID_SCOPE"


class InvalidInterval(DomainError):
    code = "INVALID_INTERVAL"


class InvalidReference(DomainError):
    code = "INVALID_REFERENCE"


class InvalidDigest(DomainError):
    code = "INVALID_DIGEST"


class VersionConflict(DomainError):
    code = "VERSION_CONFLICT"


class InvalidTransition(DomainError):
    code = "INVALID_TRANSITION"


class InvalidLegalEntity(DomainError):
    code = "INVALID_LEGAL_ENTITY"
