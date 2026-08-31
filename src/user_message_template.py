"""User message template renderer for multi-angle reframing."""

from pathlib import Path
from loguru import logger

PLACEHOLDER_SHOT_LABEL = "[Shot label]"
PLACEHOLDER_SHOT_INTENT = "[Shot intent]"


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

    return template_path.read_text(encoding="utf-8")


def render_user_message(template: str, label: str, intent: str) -> str:
    """Render the user message by substituting the shot's label and intent.

    Images are never rendered here. They travel as real `image_url` content
    parts built by `payload_builder.build_user_content`; interpolating a URL
    into this text was the original blind-model defect and must not return.

    Args:
        template: User message template string
        label: Short shot label (e.g. "CU on the woman")
        intent: The shot's intent written as concrete prose

    Returns:
        Rendered user message string
    """
    rendered = template.replace(PLACEHOLDER_SHOT_LABEL, label)
    return rendered.replace(PLACEHOLDER_SHOT_INTENT, intent)
