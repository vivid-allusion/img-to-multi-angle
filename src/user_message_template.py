"""User message template renderer for multi-angle reframing."""

from pathlib import Path
from typing import List
from loguru import logger

PLACEHOLDER_DATASET_B = "[Dataset B — Original image]"
PLACEHOLDER_DATASET_C = "[Dataset C — Character sheet reference URLs]"
PLACEHOLDER_DATASET_D = "[Dataset D — Angle template text]"


def load_user_message_template(template_path: Path) -> str:
    """Load the user message template file.

    Args:
        template_path: Path to user_message.md

    Returns:
        Template content as string

    Raises:
        FileNotFoundError: If template file missing
    """
    if not template_path.exists():
        logger.error(f"User message template not found: {template_path}")
        raise FileNotFoundError(f"User message template not found: {template_path}")

    content = template_path.read_text(encoding="utf-8")
    logger.info(f"Loaded user message template ({len(content)} chars)")

    return content


def render_user_message(
    template: str,
    dataset_b: str,
    dataset_c: List[str],
    dataset_d: str,
) -> str:
    """Render user message by replacing placeholders with actual data.

    Args:
        template: User message template string
        dataset_b: Original image URL
        dataset_c: Character sheet reference URLs
        dataset_d: Angle template text

    Returns:
        Rendered user message string
    """
    result = template.replace(PLACEHOLDER_DATASET_B, dataset_b)

    if dataset_c:
        ref_images = "\n\n".join(f"![image]({url})" for url in dataset_c)
        result = result.replace(PLACEHOLDER_DATASET_C, ref_images)
    else:
        result = result.replace(PLACEHOLDER_DATASET_C, "No character sheet references provided.")

    result = result.replace(PLACEHOLDER_DATASET_D, dataset_d)

    return result
