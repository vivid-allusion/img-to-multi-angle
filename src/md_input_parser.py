"""MD file parser for multi-angle reframing feature."""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import List
from natsort import natsorted
from loguru import logger

MD_IMAGE_PATTERN = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
MD_LINK_PATTERN = re.compile(r"!?\[[^\]]*\]\([^)]+\)")
URL_PATTERN = re.compile(r"https?://|www\.", re.IGNORECASE)
CHECKBOX_PATTERN = re.compile(r"^-\s\[[ xX]\]\s.+$")


@dataclass
class ParsedMdInput:
    """Parsed MD file contents."""

    scene: str
    original_image: str
    ref_images: List[str]
    checked_angles: List[str]
    all_checkbox_lines: List[str]


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


def _is_checkbox_line(line: str) -> bool:
    """Check if a line is a valid checkbox."""
    return bool(CHECKBOX_PATTERN.match(line.strip()))


def _parse_checkbox_line(line: str) -> tuple[str, bool]:
    """Parse a checkbox line into (angle_name, is_checked).

    Args:
        line: Raw checkbox line like '- [x] Birds Eye View'

    Returns:
        Tuple of (angle_name, is_checked)
    """
    stripped = line.strip()
    is_checked = stripped.startswith("- [x]") or stripped.startswith("- [X]")
    angle_name = stripped[5:].strip()
    return angle_name, is_checked


def _is_skippable_line(line: str) -> bool:
    """Check if a line matches a markdown embed/link or URL pattern."""
    return bool(MD_LINK_PATTERN.search(line) or URL_PATTERN.search(line))


def parse_md_file(file_path: Path) -> ParsedMdInput:
    """Parse MD file into scene, original image, ref images, and checked angles.

    Expected format:
        Lines before first image: scene description (Dataset A); lines
            matching embeds/links/URLs are skipped and logged
        First image line: ![original](url) (Dataset B)
        Then checkbox lines - [ ] / - [x] (Dataset E)
        Then ![ref](url) lines (Dataset C)

    Args:
        file_path: Path to MD file

    Returns:
        ParsedMdInput dataclass

    Raises:
        ValueError: If file structure is invalid
    """
    content = file_path.read_text(encoding="utf-8")
    lines = content.strip().splitlines()

    if not lines or not lines[0].strip():
        raise ValueError(f"Empty or missing scene description in {file_path.name}")

    images = []
    image_line_indices = []
    for i, line in enumerate(lines):
        match = MD_IMAGE_PATTERN.search(line)
        if match:
            images.append(match.group(2))
            image_line_indices.append(i)

    if not images:
        raise ValueError(f"No images found in {file_path.name}")

    first_image_idx = image_line_indices[0]
    scene_lines = []
    for line in lines[:first_image_idx]:
        if _is_skippable_line(line):
            logger.info(f"Skipping line in {file_path.name} (embed/URL): {line.strip()}")
            continue
        scene_lines.append(line.strip())

    if not any(line.strip() for line in scene_lines):
        raise ValueError(f"Scene is empty after filtering in {file_path.name}")

    scene = "\n".join(scene_lines).strip()

    original_image = images[0]

    lines_after_first_image = lines[first_image_idx + 1:]

    checkbox_lines = []
    ref_image_lines = []
    in_checkbox_section = True

    for line in lines_after_first_image:
        stripped = line.strip()
        if not stripped:
            continue
        if in_checkbox_section and _is_checkbox_line(stripped):
            checkbox_lines.append(stripped)
        elif MD_IMAGE_PATTERN.search(stripped):
            in_checkbox_section = False
            ref_image_lines.append(stripped)
        elif _is_checkbox_line(stripped):
            checkbox_lines.append(stripped)
        else:
            in_checkbox_section = False

    checked_angles = []
    all_checkbox_labels = []
    for cb_line in checkbox_lines:
        angle_name, is_checked = _parse_checkbox_line(cb_line)
        normalized = angle_name.replace(" ", "_")
        all_checkbox_labels.append(normalized)
        if is_checked:
            checked_angles.append(normalized)

    ref_images = []
    for line in ref_image_lines:
        match = MD_IMAGE_PATTERN.search(line)
        if match:
            ref_images.append(match.group(2))

    logger.info(
        f"Parsed {file_path.name}: scene={len(scene)} chars, "
        f"original_image=1, checkboxes={len(checkbox_lines)}, "
        f"checked={len(checked_angles)}, ref_images={len(ref_images)}"
    )

    return ParsedMdInput(
        scene=scene,
        original_image=original_image,
        ref_images=ref_images,
        checked_angles=checked_angles,
        all_checkbox_lines=checkbox_lines,
    )
