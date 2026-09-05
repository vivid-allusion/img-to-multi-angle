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


class FileProcessingError(TextProcessorError):
    """Raised when file I/O operations fail."""
    pass
