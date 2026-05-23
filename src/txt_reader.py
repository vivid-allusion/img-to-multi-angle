#!/usr/bin/env python3
"""TXT file reader with natsort ordering."""

from pathlib import Path
from typing import List
from natsort import natsorted
from loguru import logger


def discover_txt_files(input_dir: Path) -> List[Path]:
    """
    Discover all TXT files in input directory recursively using natsort.

    Args:
        input_dir: Path to input directory

    Returns:
        List of TXT file paths in natural sorted order (recursive)

    Raises:
        FileNotFoundError: If no TXT files found
    """
    txt_files = list(input_dir.rglob("*.txt"))
    
    if not txt_files:
        logger.error(f"No TXT files found in {input_dir}")
        raise FileNotFoundError(f"No TXT files found in {input_dir}")
    
    sorted_files = natsorted(txt_files)
    logger.info(f"Found {len(sorted_files)} TXT files (recursive scan)")
    
    return sorted_files


def read_txt_file(file_path: Path) -> str:
    """
    Read content from a TXT file.

    Args:
        file_path: Path to TXT file

    Returns:
        File content as string

    Raises:
        FileNotFoundError: If file doesn't exist
        IOError: If file can't be read
    """
    if not file_path.exists():
        logger.error(f"File not found: {file_path}")
        raise FileNotFoundError(f"File not found: {file_path}")
    
    try:
        content = file_path.read_text(encoding="utf-8")
        logger.debug(f"Read {len(content)} chars from {file_path.name}")
        return content
    except Exception as e:
        logger.error(f"Failed to read {file_path}: {e}")
        raise
