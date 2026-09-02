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
    """Clean markdown code fences and whitespace from JSON response."""
    s = text.strip()
    if s.startswith("```"):
        lines = s.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        s = "\n".join(lines).strip()
    return s


def plan_file(
    parsed: ParsedMdInput, filename: str, client: OpenRouter, config: Dict[str, Any]
) -> Tuple[ShotSheet, List[ShotEntry]]:
    """One vision call → (ShotSheet, shot list) with automatic retries.

    With declared assets the plan call receives every asset as a labelled
    image part; raw files pass bare ref URLs.
    """
    if parsed.assets is not None:
        ref_images = parsed.assets
    else:
        ref_images = parsed.ref_images

    user_content = build_user_content(
        scene=parsed.scene,
        original_image=parsed.original_image,
        ref_images=ref_images,
        angle_text=PLAN_INSTRUCTION,
    )

    retry_config = config.get("retry_config", {})
    max_retries = retry_config.get("max_retries", 2)
    total_attempts = max_retries + 1
    last_error: Optional[Exception] = None

    for attempt in range(1, total_attempts + 1):
        try:
            response_text, _ = process_text(
                user_content,
                client,
                config,
                system_prompt=PLAN_SYSTEM_PROMPT,
                skip_token_floor=True,
                response_format=RESPONSE_FORMAT,
            )

            cleaned_text = _clean_json_text(response_text)
            try:
                data = json.loads(cleaned_text)
            except json.JSONDecodeError as e:
                raise RuntimeError(f"plan call returned invalid JSON: {e}") from e

            if not isinstance(data, dict):
                raise RuntimeError("plan call returned a non-object JSON value")

            try:
                sheet = shot_sheet_from_dict(data)
            except (KeyError, TypeError, ValueError) as e:
                raise RuntimeError(f"plan call returned an invalid shot sheet: {e}") from e

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
                raise RuntimeError(f"plan call returned an invalid shot list: {e}") from e

            if sheet.subjects:
                missing = MANDATORY_SHOT_TYPES - {e.shot_type for e in entries}
                if missing:
                    raise RuntimeError(
                        f"plan covers {len(sheet.subjects)} human subject(s) but is missing "
                        f"mandatory coverage {sorted(missing)} — "
                        f"proposed: {sorted({e.shot_type for e in entries})}"
                    )

            for entry in entries:
                hits = find_banned(entry.intent)
                if hits:
                    raise RuntimeError(
                        f"shot {entry.id} intent uses forbidden word(s) {hits} — "
                        "intents must describe only what a camera can capture"
                    )

            logger.info(f"Planned {len(entries)} cinematic shots for {short_name(filename)}")
            return sheet, entries

        except Exception as e:
            last_error = e
            if attempt < total_attempts:
                logger.warning(
                    f"Plan attempt {attempt}/{total_attempts} for {short_name(filename)} failed: {e} — retrying..."
                )
            else:
                raise RuntimeError(
                    f"{filename}: plan call failed after {total_attempts} attempts: {last_error}"
                ) from last_error

    raise RuntimeError(f"{filename}: plan call failed after {total_attempts} attempts: {last_error}")
