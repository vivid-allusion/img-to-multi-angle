"""MD file parser for multi-angle reframing feature."""

import re
from pathlib import Path
from typing import Tuple, List
from natsort import natsorted
from loguru import logger

MD_IMAGE_PATTERN = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")


def discover_md_files(input_dir: Path) -> List[Path]:
    """Discover all MD files in input directory using natsort.

    Args:
        input_dir: Path to input directory

    Returns:
        List of MD file paths in natural sorted order

    Raises:
        FileNotFoundError: If no MD files found
    """
    md_files = list(input_dir.rglob("*.md"))

    if not md_files:
        logger.error(f"No MD files found in {input_dir}")
        raise FileNotFoundError(f"No MD files found in {input_dir}")

    sorted_files = natsorted(md_files)
    logger.info(f"Found {len(sorted_files)} MD files")

    return sorted_files


def parse_md_file(file_path: Path) -> Tuple[str, str, List[str]]:
    """Parse MD file into scene description, original image, and character sheets.

    Args:
        file_path: Path to MD file

    Returns:
        Tuple of (dataset_a: scene text, dataset_b: first image URL,
                  dataset_c: remaining image URLs)

    Raises:
        ValueError: If file structure is invalid
    """
    content = file_path.read_text(encoding="utf-8")
    lines = content.strip().splitlines()

    if not lines or not lines[0].strip():
        raise ValueError(f"Empty or missing scene description in {file_path.name}")

    dataset_a = lines[0].strip()

    images = []
    for line in lines:
        match = MD_IMAGE_PATTERN.search(line)
        if match:
            images.append(match.group(2))

    if not images:
        raise ValueError(f"No images found in {file_path.name}")

    dataset_b = images[0]
    dataset_c = images[1:]

    logger.info(
        f"Parsed {file_path.name}: scene={len(dataset_a)} chars, "
        f"original_image=1, ref_images={len(dataset_c)}"
    )

    return dataset_a, dataset_b, dataset_c
