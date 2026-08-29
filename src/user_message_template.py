"""User message template renderer for multi-angle reframing."""

from pathlib import Path
from loguru import logger

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


def render_user_message(template: str, dataset_d: str) -> str:
    """Render the user message by substituting the angle template text.

    Images are never rendered here. They travel as real `image_url` content
    parts built by `payload_builder.build_user_content`; interpolating a URL
    into this text was the original blind-model defect and must not return.

    Args:
        template: User message template string
        dataset_d: Angle template text

    Returns:
        Rendered user message string
    """
    return template.replace(PLACEHOLDER_DATASET_D, dataset_d)
