"""Selftest canary — verifies the whole vision chain, including left/right
orientation, against the configured model."""

import base64
import re
import sys
from pathlib import Path
from typing import Any, Dict
from openrouter import OpenRouter
from loguru import logger

from .response_utils import extract_response_text

SELFTEST_IMAGE_PATH = Path("USER-FILES/01.CONFIG/selftest/orientation_test.png")
SELFTEST_QUESTION = (
    "Name the colour of the leftmost vertical band, the middle band, and the "
    "rightmost band, in that order. Answer with three words."
)


def run_selftest(client: OpenRouter, config: Dict[str, Any]) -> None:
    """Send the orientation test image and assert red, green, blue in order.

    Exits non-zero on any deviation.
    """
    if not SELFTEST_IMAGE_PATH.exists():
        logger.error(f"Selftest image not found: {SELFTEST_IMAGE_PATH}")
        sys.exit(1)

    encoded = base64.b64encode(SELFTEST_IMAGE_PATH.read_bytes()).decode("ascii")

    content = [
        {
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{encoded}", "detail": "original"},
        },
        {"type": "text", "text": SELFTEST_QUESTION},
    ]

    logger.info(f"Running selftest against model: {config['model']}")
    response = client.chat.send(
        model=config["model"],
        messages=[{"role": "user", "content": content}],
    )

    answer = extract_response_text(response).strip().lower()
    words = re.findall(r"[a-z]+", answer)

    if len(words) < 3 or words[:3] != ["red", "green", "blue"]:
        logger.error(f"Selftest FAILED: expected 'red green blue', got: {answer!r}")
        sys.exit(1)

    logger.success("Selftest PASSED: red, green, blue in order — vision chain verified")
