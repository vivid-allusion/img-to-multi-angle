#!/usr/bin/env python3
"""Data models for multi-angle MD processing."""

from dataclasses import dataclass
from typing import Optional
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
class ProcessingResult:
    """Result from processing a single file."""
    filename: str
    success: bool
    output_path: Optional[Path] = None
    error: Optional[str] = None
    usage: Optional[UsageData] = None
    cost: float = 0.0
