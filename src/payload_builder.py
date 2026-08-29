"""Shared user-message content builder for vision payloads."""

from typing import Dict, List, Optional, Union
from urllib.parse import urlparse

from .assets import Asset


class PayloadIntegrityError(ValueError):
    """Raised when a payload does not carry the expected image parts."""


def _image_part(url: str) -> Dict[str, object]:
    return {"type": "image_url", "image_url": {"url": url, "detail": "original"}}


def _url_basename(url: str) -> str:
    path = urlparse(url).path
    return path.rsplit("/", 1)[-1] or url


def _ref_url(ref: Union[str, Asset]) -> str:
    return ref.url if isinstance(ref, Asset) else ref


def _marker_text(ref_images: List[Union[str, Asset]]) -> str:
    """Marker lines naming each image in order (the cache breakpoint).

    Asset-bearing files label refs by id (phase_1 §1.2); legacy files keep
    the basename wording so their payloads stay unchanged.
    """
    lines = ["Image 1 is the original scene image to reframe."]
    for index, ref in enumerate(ref_images, start=2):
        if isinstance(ref, Asset):
            note = f' — "{ref.note}"' if ref.note else ""
            lines.append(f"Image {index} is asset {ref.id} (role: {ref.role}){note}.")
        else:
            lines.append(
                f"Image {index} is a character sheet reference named {_url_basename(ref)}."
            )
    return "\n".join(lines)


def build_user_content(
    scene: str,
    original_image: str,
    ref_images: List[Union[str, Asset]],
    angle_text: str,
    shot_sheet: Optional[str] = None,
    cache_breakpoint: bool = False,
    cache_ttl: Optional[str] = None,
) -> List[Dict[str, object]]:
    """Return an ordered list of content parts for the user message.

    Order (stable across all angles of one file, then the variable part):
    1. text      — scene description (and shot sheet, when present)
    2. image_url — the original image, detail "original"
    3. image_url — each grounding reference, in order, detail "original"
    4. text      — marker lines naming each image in order (the cache breakpoint)
    5. text      — the angle template (the only part that varies across calls)

    Refs may be bare URLs (legacy — every shot gets all refs) or Asset
    objects (per-shot grounding, phase_1 §1.4). The image-count invariant
    compares against whatever list it was handed.
    """
    scene_text = f"{scene}\n\n{shot_sheet}" if shot_sheet else scene

    parts: List[Dict[str, object]] = [{"type": "text", "text": scene_text}]
    parts.append(_image_part(original_image))
    for ref in ref_images:
        parts.append(_image_part(_ref_url(ref)))

    marker: Dict[str, object] = {"type": "text", "text": _marker_text(ref_images)}
    if cache_breakpoint:
        if not cache_ttl:
            raise ValueError("cache_breakpoint requires a cache_ttl")
        marker["cache_control"] = {"type": "ephemeral", "ttl": cache_ttl}
    parts.append(marker)

    parts.append({"type": "text", "text": angle_text})

    expected_images = 1 + len(ref_images)
    actual_images = sum(1 for part in parts if part.get("type") == "image_url")
    if actual_images != expected_images:
        raise PayloadIntegrityError(
            f"payload carries {actual_images} image parts, expected {expected_images}"
        )

    return parts
