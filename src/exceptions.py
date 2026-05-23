"""
Custom exception classes for the text processing application.
Provides a hierarchical exception structure for better error handling.
"""


class TextProcessorError(Exception):
    """Base exception for all text processor errors."""
    pass


class ConfigurationError(TextProcessorError):
    """Raised when there's an issue with configuration files or settings."""
    pass


class ProfileError(ConfigurationError):
    """Raised when there's an issue with profile loading or validation."""
    pass


class APIAuthenticationError(TextProcessorError):
    """Raised when API authentication fails."""
    pass


class BatchProcessingError(TextProcessorError):
    """Raised when batch processing encounters an error."""
    pass


class ValidationError(TextProcessorError):
    """Raised when text or response validation fails."""
    pass


class ResponseValidationError(ValidationError):
    """Raised when API response validation fails."""
    pass


class CostCalculationError(TextProcessorError):
    """Raised when cost calculation encounters an error."""
    pass


class FileProcessingError(TextProcessorError):
    """Raised when file I/O operations fail."""
    pass