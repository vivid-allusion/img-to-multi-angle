"""Shot planner: one vision call per input file producing dynamic cinematic shots."""

import json
from typing import Any, Dict, List, Optional, Tuple
from openrouter import OpenRouter
from loguru import logger

from .api_client import process_text
from .banned_words import find_banned
from .fences import strip_outer_fences
from .md_input_parser import ParsedMdInput
from .shot_plan import MANDATORY_SHOT_TYPES, ShotEntry, shot_entries_from_list
from .shot_plan_spec import PLAN_INSTRUCTION, PLAN_RETRY_NOTE, PLAN_SYSTEM_PROMPT, RESPONSE_FORMAT
from .shot_sheet import ShotSheet, shot_sheet_from_dict
from .payload_builder import build_user_content
from .reporting import short_name
from .shot_generator import accumulate_usage


def _clean_json_text(text: str) -> str:
    """Clean markdown code fences and whitespace from JSON response.

    A fenced response under strict json_schema means structured output is not
    being enforced by the provider — log it, don't silently repair it.
    """
    s = text.strip()
    if s.startswith("```"):
        logger.warning("Provider returned a fenced JSON response — structured output not enforced")
        s = strip_outer_fences(s)
    return s


class PlanRejected(RuntimeError):
    """The plan parsed but is wrong — retry with the reason fed back."""


def _check_subject_assets(sheet: ShotSheet, declared_ids: set) -> None:
    """An undeclared asset binding is not correctable — abort without retry."""
    for subject in sheet.subjects:
        if subject.asset and subject.asset not in declared_ids:
            raise RuntimeError(
                f"subject {subject.id} bound to undeclared asset "
                f"'{subject.asset}' — aborting plan (declared: {sorted(declared_ids)})"
            )


def _check_mandatory_coverage(sheet: ShotSheet, entries: List[ShotEntry]) -> None:
    if not sheet.subjects:
        return
    missing = MANDATORY_SHOT_TYPES - {e.shot_type for e in entries}
    if missing:
        raise PlanRejected(
            f"plan covers {len(sheet.subjects)} human subject(s) but is missing "
            f"mandatory coverage {sorted(missing)} — "
            f"proposed: {sorted({e.shot_type for e in entries})}"
        )


def _check_banned_intents(entries: List[ShotEntry]) -> None:
    for entry in entries:
        hits = find_banned(entry.intent)
        if hits:
            raise PlanRejected(
                f"shot {entry.id} intent uses forbidden word(s) {hits} — "
                "intents must describe only what a camera can capture"
            )


def _parse_plan(data: Any, parsed: ParsedMdInput, filename: str) -> Tuple[ShotSheet, List[ShotEntry]]:
    """Validate one plan response. Correctable content errors raise PlanRejected;
    an undeclared-asset binding raises RuntimeError and aborts without retry."""
    if not isinstance(data, dict):
        raise PlanRejected("plan call returned a non-object JSON value")

    try:
        sheet = shot_sheet_from_dict(data)
    except (KeyError, TypeError, ValueError) as e:
        raise PlanRejected(f"plan call returned an invalid shot sheet: {e}") from e

    declared_ids = {a.id for a in parsed.assets} if parsed.assets is not None else set()
    _check_subject_assets(sheet, declared_ids)

    roster = {s.id for s in sheet.subjects}
    asset_check = declared_ids if parsed.assets is not None else None
    try:
        entries = shot_entries_from_list(
            data["shots"], filename, roster=roster, declared_assets=asset_check
        )
    except (KeyError, TypeError, ValueError) as e:
        raise PlanRejected(f"plan call returned an invalid shot list: {e}") from e

    _check_mandatory_coverage(sheet, entries)
    _check_banned_intents(entries)

    return sheet, entries


def plan_file(
    parsed: ParsedMdInput, filename: str, client: OpenRouter, config: Dict[str, Any]
) -> Tuple[ShotSheet, List[ShotEntry], Dict[str, Any]]:
    """One vision call → (ShotSheet, shot list, usage totals).

    Only PlanRejected content errors retry, with the rejection reason fed back
    in the instruction; every other exception propagates untouched. Rejected
    attempts were billed, so usage accumulates across them all.
    """
    if parsed.assets is not None:
        ref_images = parsed.assets
    else:
        ref_images = parsed.ref_images

    max_retries = config["retry_config"]["max_retries"]
    total_attempts = max_retries + 1
    total_usage: Dict[str, Any] = {}
    last_error: Optional[PlanRejected] = None

    for attempt in range(1, total_attempts + 1):
        instruction = PLAN_INSTRUCTION
        if attempt > 1:
            instruction += PLAN_RETRY_NOTE.format(error=last_error)

        user_content = build_user_content(
            scene=parsed.scene,
            original_image=parsed.original_image,
            ref_images=ref_images,
            angle_text=instruction,
        )

        try:
            response_text, usage_data = process_text(
                user_content,
                client=client,
                config=config,
                system_prompt=PLAN_SYSTEM_PROMPT,
                skip_token_floor=True,
                response_format=RESPONSE_FORMAT,
            )
            accumulate_usage(total_usage, usage_data)

            cleaned_text = _clean_json_text(response_text)
            try:
                data = json.loads(cleaned_text)
            except json.JSONDecodeError as e:
                raise PlanRejected(f"plan call returned invalid JSON: {e}") from e

            sheet, entries = _parse_plan(data, parsed, filename)
        except PlanRejected as e:
            last_error = e
            suffix = " — retrying..." if attempt < total_attempts else ""
            logger.warning(
                f"Plan attempt {attempt}/{total_attempts} for {short_name(filename)} rejected: {e}{suffix}"
            )
        else:
            logger.info(f"Planned {len(entries)} cinematic shots for {short_name(filename)}")
            return sheet, entries, total_usage

    raise RuntimeError(
        f"{filename}: plan call failed after {total_attempts} attempts: {last_error}"
    ) from last_error
