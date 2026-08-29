"""Checkbox validator for multi-angle MD input files.

Q15 dual grammar: plain angle-name labels validate against templates only;
suffixed labels ("<Angle> — <subject ids>") additionally validate the ids
against the shot-sheet roster, and the id count against the template's
subject_arity. Failures stay hard (sys.exit).
"""

import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from loguru import logger

from .angle_loader import AngleTemplate, get_available_angle_names
from .md_input_parser import GROUNDS_PATTERN

SUBJECT_ID_PATTERN = re.compile(r"\bS\d+\b")


def validate_checkboxes(
    checkbox_lines: List[str],
    available_angles: Set[str],
    filename: str,
    roster: Optional[Set[str]] = None,
    templates: Optional[Dict[str, AngleTemplate]] = None,
) -> None:
    """Validate checkbox lines against angle templates and, for suffixed
    labels, against the shot-sheet roster.

    Args:
        checkbox_lines: List of raw checkbox lines from MD file
        available_angles: Set of valid angle names from template directory
        filename: MD filename for error messages
        roster: Set of valid subject ids from the shot sheet (None = no sheet)
        templates: Angle templates by name; enables subject_arity checking

    Raises:
        SystemExit: If validation fails
    """
    if not checkbox_lines:
        logger.error(f"{filename}: No checkbox section found")
        logger.error("Run your MD files through the 'add-multi-checkboxes' tool to add the checkbox section")
        sys.exit(1)

    invalid_labels = []
    for line in checkbox_lines:
        stripped = line.strip()
        label = stripped[5:].strip()
        label = GROUNDS_PATTERN.sub("", label).rstrip()

        if " — " in label:
            angle_part, subject_part = label.split(" — ", 1)
            subject_ids = SUBJECT_ID_PATTERN.findall(subject_part)
            if not subject_ids:
                invalid_labels.append(label)
                logger.error(f"{filename}: suffixed label has no subject id: '{label}'")
                continue
            if roster is None:
                invalid_labels.append(label)
                logger.error(f"{filename}: suffixed label but no shot-sheet roster: '{label}'")
                continue
            unknown = [sid for sid in subject_ids if sid not in roster]
            if unknown:
                invalid_labels.append(label)
                logger.error(f"{filename}: unknown subject ids in label: {unknown} — '{label}'")
                continue
            template = (templates or {}).get(angle_part.replace(" ", "_"))
            if template is not None and len(subject_ids) != template.subject_arity:
                invalid_labels.append(label)
                logger.error(
                    f"{filename}: '{template.label}' needs {template.subject_arity} subject(s), "
                    f"label names {len(subject_ids)} ({', '.join(subject_ids)}) — '{label}'"
                )
                continue
        else:
            angle_part = label

        angle_name = angle_part.replace(" ", "_")
        if angle_name not in available_angles:
            invalid_labels.append(label)

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
