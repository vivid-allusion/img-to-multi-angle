"""Pre-API validation. Everything validatable runs before the first API call
and before any output directory exists."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Tuple
import httpx
from openrouter import OpenRouter
from loguru import logger

from .md_input_parser import parse_md_file, _parse_checkbox_line, ParsedMdInput
from .checkbox_validator import validate_checkboxes
from .reporting import short_url

MAX_IMAGE_BYTES = 20_000_000


class PreflightError(RuntimeError):
    """Raised when any preflight check fails."""


@dataclass
class PreflightReport:
    """Summary of a passed preflight run, plus the parsed files the
    orchestrator generates from (no second parse per file)."""

    files_validated: int
    urls_checked: int
    model_id: str
    vision_capable: bool
    parsed_files: List[Tuple[Path, ParsedMdInput]] = field(default_factory=list)


def _check_groundings(filename: str, parsed: ParsedMdInput) -> None:
    """Traceability checks for files that declare assets.

    Once an assets block exists, every ref image must be declared.
    If checkbox entries exist, their grounding list braces must be valid.
    """
    if parsed.assets is None:
        return

    declared_ids = {a.id for a in parsed.assets}
    declared_urls = {a.url for a in parsed.assets}

    for url in parsed.ref_images:
        if url not in declared_urls:
            raise PreflightError(
                f"{filename}: ref image not declared in the assets block: {url} — "
                "declare every reference image once an assets block exists"
            )

    if parsed.all_checkbox_lines:
        for line in parsed.all_checkbox_lines:
            _, ground_ids, _ = _parse_checkbox_line(line)
            if ground_ids is None:
                raise PreflightError(
                    f"{filename}: checkbox entry has no grounding list — append braces "
                    f"(use {{}} for master-only): '{line.strip()}'"
                )
            unknown = [g for g in ground_ids if g not in declared_ids]
            if unknown:
                raise PreflightError(
                    f"{filename}: label '{line.strip()}' grounds on unknown asset id(s) "
                    f"{unknown} — declared: {sorted(declared_ids)}"
                )


def run_preflight(
    config: Dict[str, Any],
    md_files: List[Path],
    client: OpenRouter,
) -> PreflightReport:
    """Run all preflight checks in order. Raises on the first failure.

    Raw files (without a shot-plan block) pass preflight for automatic
    single-pass generation. Pre-checked files have checkboxes validated.
    URL reachability, asset declarations, and vision capability are checked upfront.
    """
    parsed_files = []
    for md_path in md_files:
        parsed = parse_md_file(md_path)
        if parsed.shot_entries is not None and parsed.all_checkbox_lines:
            validate_checkboxes(
                parsed.all_checkbox_lines,
                {e.id for e in parsed.shot_entries},
                md_path.name,
            )
        _check_groundings(md_path.name, parsed)
        parsed_files.append((md_path, parsed))

    url_cache: Dict[str, bool] = {}
    for _md_path, parsed in parsed_files:
        asset_urls = [a.url for a in parsed.assets] if parsed.assets is not None else []
        for url in [parsed.original_image, *asset_urls, *parsed.ref_images]:
            _check_image_url(url, _md_path.name, url_cache)

    _check_model_vision(config, client)

    return PreflightReport(
        files_validated=len(parsed_files),
        urls_checked=len(url_cache),
        model_id=config["model"],
        vision_capable=True,
        parsed_files=parsed_files,
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
    logger.info(f"Image verified: {short_url(url)}")


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

    logger.info(f"Model vision verified: {model_id}")
