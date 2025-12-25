"""Custom exceptions for mypylogger."""


class MypyloggerError(Exception):
    """Base exception for all mypylogger errors."""


class ConfigurationError(MypyloggerError):
    """Raised when configuration is invalid or cannot be resolved."""


class FormattingError(MypyloggerError):
    """Raised when JSON formatting fails."""


class HandlerError(MypyloggerError):
    """Raised when handler setup or operation fails."""
