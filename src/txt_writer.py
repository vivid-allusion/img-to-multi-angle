#!/usr/bin/env python3
"""TXT file writer with timestamped output directories."""

from datetime import datetime
from pathlib import Path
from typing import Optional
from loguru import logger

from .constants import TIMESTAMP_FORMAT


def create_output_directory(base_output_dir: Path, timestamp: Optional[datetime] = None) -> Path:
    """
    Create timestamped output directory with _MONTAGE suffix.

    Args:
        base_output_dir: Base output directory (USER-FILES/05.OUTPUT)
        timestamp: Optional timestamp (uses now() if not provided)

    Returns:
        Path to created output directory
    """
    if timestamp is None:
        timestamp = datetime.now()
    
    dir_name = f"{timestamp.strftime(TIMESTAMP_FORMAT)}_MONTAGE"
    output_dir = base_output_dir / dir_name
    
    output_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Output directory: {output_dir}")
    
    return output_dir


def save_txt_output(
    content: str,
    output_dir: Path,
    input_filename: str,
    timestamp: Optional[datetime] = None,
    relative_path: Optional[Path] = None
) -> Path:
    """
    Save TXT content to output file with timestamped filename.
    
    Mirrors input directory structure if relative_path is provided.

    Args:
        content: Content to save
        output_dir: Output directory
        input_filename: Original input filename (without extension)
        timestamp: Optional timestamp (uses now() if not provided)
        relative_path: Optional relative path from input directory (for structure mirroring)

    Returns:
        Path to saved file
    """
    if timestamp is None:
        timestamp = datetime.now()
    
    output_filename = f"{timestamp.strftime(TIMESTAMP_FORMAT)}_{input_filename}.txt"
    
    if relative_path and relative_path.parent != Path("."):
        target_dir = output_dir / relative_path.parent
        target_dir.mkdir(parents=True, exist_ok=True)
        output_path = target_dir / output_filename
    else:
        output_path = output_dir / output_filename
    
    try:
        output_path.write_text(content, encoding="utf-8")
        logger.success(f"Saved: {output_path.relative_to(output_dir)}")
        return output_path
    except Exception as e:
        logger.error(f"Failed to save {output_path}: {e}")
        raise
