"""Shared user-message content builder for vision payloads."""

from typing import Dict, List, Optional
from urllib.parse import urlparse


class PayloadIntegrityError(ValueError):
    """Raised when a payload does not carry the expected image parts."""


def _image_part(url: str) -> Dict[str, object]:
    return {"type": "image_url", "image_url": {"url": url, "detail": "original"}}


def _url_basename(url: str) -> str:
    path = urlparse(url).path
    return path.rsplit("/", 1)[-1] or url


def _marker_text(ref_images: List[str]) -> str:
    lines = ["Image 1 is the original scene image to reframe."]
    for index, url in enumerate(ref_images, start=2):
        lines.append(f"Image {index} is a character sheet reference named {_url_basename(url)}.")
    return "\n".join(lines)


def build_user_content(
    scene: str,
    original_image: str,
    ref_images: List[str],
    angle_text: str,
    shot_sheet: Optional[str] = None,
    cache_breakpoint: bool = False,
) -> List[Dict[str, object]]:
    """Return an ordered list of content parts for the user message.

    Order (stable across all angles of one file, then the variable part):
    1. text      — scene description (and shot sheet, when Phase 3 lands)
    2. image_url — the original image, detail "original"
    3. image_url — each character-sheet reference, in order, detail "original"
    4. text      — marker lines naming each image in order
    5. text      — the angle template (the only part that varies across calls)
    """
    scene_text = f"{scene}\n\n{shot_sheet}" if shot_sheet else scene

    parts: List[Dict[str, object]] = [{"type": "text", "text": scene_text}]
    parts.append(_image_part(original_image))
    for url in ref_images:
        parts.append(_image_part(url))

    marker: Dict[str, object] = {"type": "text", "text": _marker_text(ref_images)}
    if cache_breakpoint:
        marker["cache_control"] = {"type": "ephemeral"}
    parts.append(marker)

    parts.append({"type": "text", "text": angle_text})

    expected_images = 1 + len(ref_images)
    actual_images = sum(1 for part in parts if part.get("type") == "image_url")
    if actual_images != expected_images:
        raise PayloadIntegrityError(
            f"payload carries {actual_images} image parts, expected {expected_images}"
        )

    return parts
