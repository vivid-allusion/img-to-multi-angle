"""Checkbox validator for multi-angle MD input files."""

import sys
from pathlib import Path
from typing import List, Set, Tuple
from loguru import logger

from .angle_loader import get_available_angle_names

CHECKBOX_LINE_PATTERN = r"^- \[[ xX]\] .+$"


def validate_checkboxes(
    checkbox_lines: List[str],
    available_angles: Set[str],
    filename: str,
) -> None:
    """Validate checkbox lines against available angle templates.

    Args:
        checkbox_lines: List of raw checkbox lines from MD file
        available_angles: Set of valid angle names from template directory
        filename: MD filename for error messages

    Raises:
        SystemExit: If validation fails
    """
    if not checkbox_lines:
        logger.error(f"{filename}: No checkbox section found")
        logger.error("Run your MD files through the 'add-multi-checkboxes' tool to add the checkbox section")
        sys.exit(1)

    angle_lookup = {name: name for name in available_angles}

    invalid_labels = []
    for line in checkbox_lines:
        stripped = line.strip()
        angle_name = stripped[5:].strip().replace(" ", "_")
        if angle_name not in angle_lookup:
            invalid_labels.append(stripped[5:].strip())

    if invalid_labels:
        logger.error(f"{filename}: Invalid checkbox labels not matching any template:")
        for label in invalid_labels:
            logger.error(f"  - {label}")
        logger.error("Run your MD files through the 'add-multi-checkboxes' tool to refresh the checkbox list")
        sys.exit(1)


def validate_all_files(
    parsed_items: List[Tuple[str, List[str]]],
    template_dir: Path,
) -> None:
    """Validate checkboxes for all input files before processing.

    Args:
        parsed_items: List of (filename, checkbox_lines) tuples
        template_dir: Path to angle-templates directory

    Raises:
        SystemExit: If any file fails validation
    """
    available_angles = set(get_available_angle_names(template_dir))

    for filename, checkbox_lines in parsed_items:
        validate_checkboxes(checkbox_lines, available_angles, filename)

    logger.info(f"Checkbox validation passed for {len(parsed_items)} files against {len(available_angles)} templates")
