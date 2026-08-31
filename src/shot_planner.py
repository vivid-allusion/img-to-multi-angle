"""Shot planner: one vision call per input file producing dynamic cinematic shots."""

import json
from typing import Any, Dict, List, Tuple
from openrouter import OpenRouter
from loguru import logger

from .api_client import process_text
from .md_input_parser import ParsedMdInput
from .shot_plan import ShotEntry, shot_entries_from_list
from .shot_sheet import ShotSheet, shot_sheet_from_dict
from .payload_builder import build_user_content
from .reporting import short_name

PLAN_SYSTEM_PROMPT = (
    "You are a master film director and cinematographer. Given an original scene image and "
    "description, analyze the subjects and propose a comprehensive 5 to 6 shot cinematic "
    "coverage package for prestige drama (such as Establishing Master Wide, Over-The-Shoulder "
    "Reverse, Low-Angle Hero, High-Angle Vantage, Dynamic 3/4 Medium, Character Close-Up / Detail Shot).\n\n"
    "Identify the key human subjects in the scene with an id (S1, S2, ...) and description. "
    "If reference images labelled as assets are provided, bind each subject's 'asset' field "
    "to the matching asset id (e.g., A1), or leave it null if unconfident.\n\n"
    "Then propose 5 to 6 distinct, bold 3D camera angles that cover the scene dynamically:\n"
    "- Propose real perspective shifts and 3D camera placements (reverse angles, low/high tilts, "
    "off-axis profiles, unseen viewpoints) rather than flat 2D crops.\n"
    "- Give every shot an id (SH01, SH02, ...), a clear cinematic label, and an intent written "
    "as concrete visual prose describing the camera vantage point, framing, depth of field, "
    "and subject focal point.\n"
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
                    "subject_ids": {
                        "type": "array",
                        "items": {"type": "string", "pattern": "^S[0-9]+$"},
                    },
                    "grounds": {
                        "type": "array",
                        "items": {"type": "string", "pattern": "^A[0-9]+$"},
                    },
                },
                "required": ["id", "label", "intent", "subject_ids", "grounds"],
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


def plan_file(
    parsed: ParsedMdInput, filename: str, client: OpenRouter, config: Dict[str, Any]
) -> Tuple[ShotSheet, List[ShotEntry]]:
    """One vision call → (ShotSheet, shot list).

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

    response_text, _ = process_text(
        user_content,
        client,
        config,
        system_prompt=PLAN_SYSTEM_PROMPT,
        skip_token_floor=True,
        response_format=RESPONSE_FORMAT,
    )

    try:
        data = json.loads(response_text)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"{filename}: plan call returned invalid JSON: {e}") from e

    if not isinstance(data, dict):
        raise RuntimeError(f"{filename}: plan call returned a non-object JSON value")

    try:
        sheet = shot_sheet_from_dict(data)
    except (KeyError, TypeError, ValueError) as e:
        raise RuntimeError(f"{filename}: plan call returned an invalid shot sheet: {e}") from e

    declared_ids = {a.id for a in parsed.assets} if parsed.assets is not None else set()
    for subject in sheet.subjects:
        if subject.asset and subject.asset not in declared_ids:
            raise RuntimeError(
                f"{filename}: subject {subject.id} bound to undeclared asset "
                f"'{subject.asset}' — aborting plan (declared: {sorted(declared_ids)})"
            )

    roster = {s.id for s in sheet.subjects}
    asset_check = declared_ids if parsed.assets is not None else None
    try:
        entries = shot_entries_from_list(
            data["shots"], filename, roster=roster, declared_assets=asset_check
        )
    except (KeyError, TypeError, ValueError) as e:
        raise RuntimeError(f"{filename}: plan call returned an invalid shot list: {e}") from e

    logger.info(f"Planned {len(entries)} cinematic shots for {short_name(filename)}")
    return sheet, entries
