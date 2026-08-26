"""Pre-API validation. Everything validatable runs before the first API call
and before any output directory exists."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List
import httpx
from openrouter import OpenRouter
from loguru import logger

from .md_input_parser import parse_md_file
from .angle_loader import load_angle_templates
from .checkbox_validator import validate_checkboxes

ANGLE_TEMPLATE_DIR = Path("USER-FILES/01.CONFIG/angle-templates")
MAX_IMAGE_BYTES = 20_000_000


class PreflightError(RuntimeError):
    """Raised when any preflight check fails."""


@dataclass
class PreflightReport:
    """Summary of a passed preflight run."""

    files_validated: int
    urls_checked: int
    model_id: str
    vision_capable: bool


def run_preflight(
    config: Dict[str, Any],
    md_files: List[Path],
    client: OpenRouter,
    plan_mode: bool = False,
) -> PreflightReport:
    """Run all preflight checks in order. Raises on the first failure.

    plan_mode: checkbox validation is skipped (Q19 — --plan accepts files
    without a checkbox section); URL/vision/config checks still run.
    """
    available_angles = set(load_angle_templates(ANGLE_TEMPLATE_DIR).keys())

    parsed_files = []
    for md_path in md_files:
        parsed = parse_md_file(md_path)
        if not plan_mode:
            roster = {s.id for s in parsed.shot_sheet.subjects} if parsed.shot_sheet else None
            validate_checkboxes(parsed.all_checkbox_lines, available_angles, md_path.name, roster=roster)
        parsed_files.append((md_path.name, parsed))

    url_cache: Dict[str, bool] = {}
    for filename, parsed in parsed_files:
        for url in [parsed.original_image, *parsed.ref_images]:
            _check_image_url(url, filename, url_cache)

    _check_model_vision(config, client)

    return PreflightReport(
        files_validated=len(parsed_files),
        urls_checked=len(url_cache),
        model_id=config["model"],
        vision_capable=True,
    )


def _check_image_url(url: str, filename: str, cache: Dict[str, bool]) -> None:
    """Verify one image URL is reachable and looks like an image."""
    if url in cache:
        return

    try:
        response = httpx.head(url, follow_redirects=True, timeout=10.0)
        if response.status_code == 405:
            response = httpx.get(
                url, headers={"Range": "bytes=0-1023"}, follow_redirects=True, timeout=10.0
            )
    except httpx.HTTPError as e:
        raise PreflightError(f"Image URL unreachable in {filename}: {url} ({e})") from e

    if response.status_code != 200:
        raise PreflightError(
            f"Image URL returned status {response.status_code} in {filename}: {url}"
        )

    content_type = response.headers.get("content-type", "")
    if not content_type.lower().startswith("image/"):
        raise PreflightError(
            f"Image URL returned content-type '{content_type}', expected image/* in {filename}: {url}"
        )

    content_length = response.headers.get("content-length")
    if content_length is not None:
        try:
            length = int(content_length)
        except ValueError as e:
            raise PreflightError(
                f"Image URL has invalid content-length in {filename}: {url}"
            ) from e
        if not 0 < length <= MAX_IMAGE_BYTES:
            raise PreflightError(
                f"Image URL content-length {length} outside 0..{MAX_IMAGE_BYTES} bytes in {filename}: {url}"
            )

    cache[url] = True
    logger.info(f"Image URL OK ({content_type}, {content_length or 'no length'} bytes): {url}")


def _check_model_vision(config: Dict[str, Any], client: OpenRouter) -> None:
    """Assert the configured model accepts image input."""
    model_id = config["model"]

    response = client.models.list()
    if response is None:
        raise PreflightError("models.list() returned no response for vision check")

    model = next((m for m in response.result.data if m.id == model_id), None)
    if model is None:
        raise PreflightError(f"Model '{model_id}' not found in OpenRouter model list")

    if "image" not in model.architecture.input_modalities:
        raise PreflightError(
            f"Model '{model_id}' does not accept image input "
            f"(input_modalities={list(model.architecture.input_modalities)})"
        )

    logger.info(f"Model '{model_id}' accepts image input")
