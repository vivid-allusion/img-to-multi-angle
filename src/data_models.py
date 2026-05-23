#!/usr/bin/env python3
"""Data models and classes for parameter consolidation."""

from dataclasses import dataclass
from typing import Dict, Any, Optional
from pathlib import Path


@dataclass
class UsageData:
    """Consolidated usage data for cost reporting."""
    input_tokens: int
    output_tokens: int
    cache_creation_tokens: int = 0
    cache_read_tokens: int = 0
    filename: Optional[str] = None
    model: Optional[str] = None


@dataclass
class ConfigSource:
    """Track configuration sources for validation."""
    field: str
    value: Any
    source_file: Path
    line_number: Optional[int] = None
    is_override: bool = False


@dataclass
class ReportContext:
    """Context for report generation."""
    output_dir: Path
    stats: Dict[str, Any]
    metadata: Dict[str, Any]
    duration: float


@dataclass
class BatchRequest:
    """Batch request information."""
    custom_id: str
    params: Dict[str, Any]
    filename: str
    content: str


@dataclass
class ProcessingResult:
    """Result from processing a single file."""
    filename: str
    success: bool
    output_path: Optional[Path] = None
    error: Optional[str] = None
    usage: Optional[UsageData] = None
    cost: float = 0.0