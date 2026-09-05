"""Shot planner: one vision call per input file producing dynamic cinematic shots."""

import json
from typing import Any, Dict, List, Optional, Tuple
from openrouter import OpenRouter
from loguru import logger

from .api_client import process_text
from .banned_words import find_banned
from .md_input_parser import ParsedMdInput
from .shot_plan import MANDATORY_SHOT_TYPES, SHOT_TYPES, ShotEntry, shot_entries_from_list
from .shot_sheet import ShotSheet, shot_sheet_from_dict
from .payload_builder import build_user_content
from .reporting import short_name
from .shot_generator import accumulate_usage

PLAN_SYSTEM_PROMPT = (
    "You are a master film director and cinematographer. Given an original scene image and "
    "description, identify the subjects and propose a 5 to 6 shot coverage package.\n\n"
    "Identify the key human subjects in the scene with an id (S1, S2, ...) and description. "
    "If reference images labelled as assets are provided, bind each subject's 'asset' field "
    "to the matching asset id (e.g., A1), or leave it null if unconfident.\n\n"
    "COVERAGE HIERARCHY. Drama lives in faces, gaze, and what hands are doing. When the scene "
    "contains people, propose shots in this order of priority and set each shot's 'shot_type' "
    "to the slot it fills:\n"
    "1. face_cu — the primary character's face, close enough to read the eyes, the direction "
    "of the gaze, and the expression.\n"
    "2. face_cu — the second key character or adversary, same treatment (only if two or more "
    "people are present; a single-subject scene simply has one fewer shot).\n"
    "3. medium_action — a character from the waist or chest up, showing posture, wardrobe, and "
    "physical stance in the immediate environment.\n"
    "4. hands_insert — tight on what a character is physically doing with their hands or body: "
    "gloved hands hauling a rope taut, fingers closing on a crate handle, a boot pressing into "
    "snow.\n"
    "5. wide_master — the establishing view, figures visible head to boots, the full geography "
    "of the location.\n"
    "6. dynamic_vantage — an over-the-shoulder reverse past a foreground figure, or a ground-level "
    "tilt looking up at the key character.\n\n"
    "A plan for a scene with people MUST include at least one face_cu, one hands_insert, and one "
    "wide_master. A plan missing any of the three is rejected.\n\n"
    "FORBIDDEN FOCUS. When human subjects are present, do not spend a shot on a close-up of an "
    "inanimate object — a wall, a lantern, a crate, a tree — unless a character's hands are on it "
    "in that exact moment (which makes it a hands_insert, not an object_insert). A prop close-up "
    "while a person stands uncovered is a wasted shot.\n\n"
    "If the scene contains no people at all, the hierarchy above does not apply: cover the "
    "vehicle, structure, or landscape with the boldest angles available, and object_insert is "
    "then a legitimate shot_type.\n\n"
    "For every shot:\n"
    "- Propose real perspective shifts and 3D camera placements (reverse angles, low/high tilts, "
    "off-axis profiles, unseen viewpoints) rather than flat 2D crops.\n"
    "- Give every shot an id (SH01, SH02, ...), a clear label, and an intent written as concrete "
    "visual prose describing the camera vantage point, the framing boundary on the body, and the "
    "focal point. Write intents as physical description only — never name a mood, an atmosphere, "
    "or how intensely someone is doing something.\n"
    "- List any bound asset ids in 'grounds' (use [] if master only).\n"
    "Return the result conforming strictly to the JSON schema."
)

PLAN_INSTRUCTION = (
    "Analyse the provided scene and return the subjects and 5 to 6 cinematic camera shots as JSON."
)

PLAN_RETRY_NOTE = (
    "\n\nYour previous plan was rejected: {error}\n"
    "Return a corrected plan that fixes exactly that problem."
)

SHOT_SHEET_SCHEMA = {
    "type": "object",
    "properties": {
        "subjects": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string", "pattern": "^S[0-9]+$"},
                    "description": {"type": "string"},
                    "asset": {"type": ["string", "null"], "pattern": "^A[0-9]+$"},
                },
                "required": ["id", "description", "asset"],
                "additionalProperties": False,
            },
        },
        "shots": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string", "pattern": "^SH[0-9]+$"},
                    "label": {"type": "string"},
                    "intent": {"type": "string"},
                    "shot_type": {"type": "string", "enum": list(SHOT_TYPES)},
                    "subject_ids": {
                        "type": "array",
                        "items": {"type": "string", "pattern": "^S[0-9]+$"},
                    },
                    "grounds": {
                        "type": "array",
                        "items": {"type": "string", "pattern": "^A[0-9]+$"},
                    },
                },
                "required": ["id", "label", "intent", "shot_type", "subject_ids", "grounds"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["subjects", "shots"],
    "additionalProperties": False,
}

RESPONSE_FORMAT = {
    "type": "json_schema",
    "json_schema": {"name": "shot_plan", "strict": True, "schema": SHOT_SHEET_SCHEMA},
}


def _clean_json_text(text: str) -> str:
    """Clean markdown code fences and whitespace from JSON response.

    A fenced response under strict json_schema means structured output is not
    being enforced by the provider — log it, don't silently repair it.
    """
    s = text.strip()
    if s.startswith("```"):
        logger.warning("Provider returned a fenced JSON response — structured output not enforced")
        lines = s.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        s = "\n".join(lines).strip()
    return s


class PlanRejected(RuntimeError):
    """The plan parsed but is wrong — retry with the reason fed back."""


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
    for subject in sheet.subjects:
        if subject.asset and subject.asset not in declared_ids:
            raise RuntimeError(
                f"subject {subject.id} bound to undeclared asset "
                f"'{subject.asset}' — aborting plan (declared: {sorted(declared_ids)})"
            )

    roster = {s.id for s in sheet.subjects}
    asset_check = declared_ids if parsed.assets is not None else None
    try:
        entries = shot_entries_from_list(
            data["shots"], filename, roster=roster, declared_assets=asset_check
        )
    except (KeyError, TypeError, ValueError) as e:
        raise PlanRejected(f"plan call returned an invalid shot list: {e}") from e

    if sheet.subjects:
        missing = MANDATORY_SHOT_TYPES - {e.shot_type for e in entries}
        if missing:
            raise PlanRejected(
                f"plan covers {len(sheet.subjects)} human subject(s) but is missing "
                f"mandatory coverage {sorted(missing)} — "
                f"proposed: {sorted({e.shot_type for e in entries})}"
            )

    for entry in entries:
        hits = find_banned(entry.intent)
        if hits:
            raise PlanRejected(
                f"shot {entry.id} intent uses forbidden word(s) {hits} — "
                "intents must describe only what a camera can capture"
            )

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
                client,
                config,
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
