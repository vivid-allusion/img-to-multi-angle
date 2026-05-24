"""Angle template loader for multi-angle reframing feature."""

from pathlib import Path
from typing import Dict
from natsort import natsorted
from loguru import logger


def load_angle_templates(template_dir: Path) -> Dict[str, str]:
    """Load all angle templates from directory.

    Args:
        template_dir: Path to angle-templates directory

    Returns:
        Dict mapping angle name (filename without extension) to template content

    Raises:
        FileNotFoundError: If directory missing or empty
    """
    if not template_dir.exists():
        logger.error(f"Angle templates directory not found: {template_dir}")
        raise FileNotFoundError(f"Angle templates directory not found: {template_dir}")

    template_files = natsorted(template_dir.glob("*.txt"))

    if not template_files:
        logger.error(f"No angle templates found in {template_dir}")
        raise FileNotFoundError(f"No angle templates found in {template_dir}")

    templates = {}
    for tf in template_files:
        angle_name = tf.stem
        content = tf.read_text(encoding="utf-8").strip()
        templates[angle_name] = content

    logger.info(f"Loaded {len(templates)} angle templates from {template_dir}")

    return templates
