"""Checkbox validator for multi-angle MD input files.

Self-referential grammar (phase_2 §2.3): every ticked shot id must exist in
the file's own shot-plan block. No template directory is consulted. Failures
stay hard (sys.exit).
"""

import sys
from typing import List, Set

from loguru import logger

from .md_input_parser import _parse_checkbox_line
from .shot_plan import SHOT_ID_PATTERN


def _check_checkbox_line(
    line: str, shot_ids: Set[str], filename: str, seen: Set[str], invalid: List[str]
) -> None:
    """Validate one checkbox line, appending to `invalid` on a hard failure."""
    stripped = line.strip()
    shot_id, _, is_checked = _parse_checkbox_line(stripped)

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
        return
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
        return
    if is_checked and shot_id in seen:
        invalid.append(stripped)
        logger.error(f"{filename}: shot id '{shot_id}' ticked more than once")
        return
    if is_checked:
        seen.add(shot_id)


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

    invalid: List[str] = []
    seen: Set[str] = set()
    for line in checkbox_lines:
        _check_checkbox_line(line, shot_ids, filename, seen, invalid)

    if invalid:
        logger.error(f"{filename}: Invalid checkbox entries:")
        for label in invalid:
            logger.error(f"  - {label}")
        logger.error("Run --plan to regenerate the shot list and checkbox section")
        sys.exit(1)
