"""Pre-API validation. Everything validatable runs before the first API call
and before any output directory exists."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List
import httpx
from openrouter import OpenRouter
from loguru import logger

from .md_input_parser import parse_md_file, _parse_checkbox_line, ParsedMdInput
from .checkbox_validator import validate_checkboxes

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


def _check_groundings(filename: str, parsed: ParsedMdInput, plan_mode: bool) -> None:
    """Phase-1 traceability checks for files that declare assets (§1.3 + Q1/Q2).

    Q1: once an assets block exists, every ref image must be declared.
    Q2: every checkbox entry must carry a grounding list; every id in braces
        must exist in the assets block. Braces-divergence warnings (Q3/Q4)
        apply to checked shots with a shot sheet.
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

    if plan_mode:
        return

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

    if parsed.shot_sheet is None:
        return

    assets_by_subject = {s.id: s.asset for s in parsed.shot_sheet.subjects}
    entries_by_id = {e.id: e for e in parsed.shot_entries or []}
    for shot_id, ground_ids in parsed.checked_shot_bindings:
        entry = entries_by_id.get(shot_id)
        if entry is None:
            continue
        bound = {
            assets_by_subject[sid]
            for sid in entry.subject_ids
            if assets_by_subject.get(sid)
        }
        braces = set(ground_ids or [])
        if bound - braces:
            logger.warning(
                f"{filename}: '{shot_id}' — bound subject asset(s) "
                f"{sorted(bound - braces)} not in grounds; master-only grounding "
                "accepted as a deliberate override"
            )
        if braces - bound:
            logger.warning(
                f"{filename}: '{shot_id}' — grounds {sorted(braces - bound)} "
                "not bound to any subject in the shot plan; braces remain "
                "authoritative"
            )


def run_preflight(
    config: Dict[str, Any],
    md_files: List[Path],
    client: OpenRouter,
    plan_mode: bool = False,
) -> PreflightReport:
    """    Run all preflight checks in order. Raises on the first failure.

    plan_mode: checkbox validation is skipped (Q19 — --plan accepts files
    without a checkbox section); URL/vision/config checks still run. The
    Q2/brace grammar checks are rewrite-mode only; the Q1 declaration check
    and asset URL checks run in both modes.
    """
    parsed_files = []
    for md_path in md_files:
        parsed = parse_md_file(md_path)
        if not plan_mode:
            if parsed.shot_entries is None:
                raise PreflightError(
                    f"{md_path.name}: no shot-plan block — run --plan on this "
                    "file first to generate the shot list (Q7: legacy template "
                    "files must be re-planned)"
                )
            validate_checkboxes(
                parsed.all_checkbox_lines,
                {e.id for e in parsed.shot_entries},
                md_path.name,
            )
        _check_groundings(md_path.name, parsed, plan_mode)
        parsed_files.append((md_path.name, parsed))

    url_cache: Dict[str, bool] = {}
    for filename, parsed in parsed_files:
        asset_urls = [a.url for a in parsed.assets] if parsed.assets is not None else []
        for url in [parsed.original_image, *asset_urls, *parsed.ref_images]:
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
