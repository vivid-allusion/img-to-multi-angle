"""Checkbox validator for multi-angle MD input files.

Self-referential grammar (phase_2 §2.3): every ticked shot id must exist in
the file's own shot-plan block. No template directory is consulted. Failures
stay hard (sys.exit).
"""

import re
import sys
from typing import List, Set

from loguru import logger

from .md_input_parser import GROUNDS_PATTERN

SHOT_ID_PATTERN = re.compile(r"^SH\d+$")


def validate_checkboxes(
    checkbox_lines: List[str],
    shot_ids: Set[str],
    filename: str,
) -> None:
    """Validate checkbox lines against the file's shot-plan shot ids.

    Args:
        checkbox_lines: List of raw checkbox lines from MD file
        shot_ids: Set of shot ids declared in the file's shot-plan block
        filename: MD filename for error messages

    Raises:
        SystemExit: If validation fails
    """
    if not checkbox_lines:
        logger.error(f"{filename}: No checkbox section found")
        logger.error("Run --plan to generate the shot list and checkbox section")
        sys.exit(1)

    invalid = []
    seen: Set[str] = set()
    for line in checkbox_lines:
        stripped = line.strip()
        is_checked = stripped.startswith("- [x]") or stripped.startswith("- [X]")
        label = GROUNDS_PATTERN.sub("", stripped[5:].strip()).rstrip()
        shot_id = label.split(" — ", 1)[0].strip()

        if not SHOT_ID_PATTERN.match(shot_id):
            if is_checked:
                invalid.append(stripped)
                logger.error(
                    f"{filename}: checkbox label does not lead with a shot id "
                    f"(SH01, SH02, ...): '{stripped}' — run --plan on this file"
                )
            else:
                logger.warning(
                    f"{filename}: unticked label does not lead with a shot id: "
                    f"'{stripped}'"
                )
            continue
        if shot_id not in shot_ids:
            if is_checked:
                invalid.append(stripped)
                logger.error(
                    f"{filename}: shot id '{shot_id}' not found in this file's "
                    f"shot-plan block: '{stripped}'"
                )
            else:
                logger.warning(
                    f"{filename}: unticked shot id '{shot_id}' not found in the "
                    f"shot-plan block: '{stripped}'"
                )
            continue
        if is_checked and shot_id in seen:
            invalid.append(stripped)
            logger.error(f"{filename}: shot id '{shot_id}' ticked more than once")
            continue
        if is_checked:
            seen.add(shot_id)

    if invalid:
        logger.error(f"{filename}: Invalid checkbox entries:")
        for label in invalid:
            logger.error(f"  - {label}")
        logger.error("Run --plan to regenerate the shot list and checkbox section")
        sys.exit(1)
