"""--plan mode: one vision call per input file producing a strict shot sheet
(§3.2/§3.3). Owns the plan-mode orchestration: preflight, staging, atomic
promotion (Q16 — the prime directive covers --plan too)."""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from openrouter import OpenRouter
from loguru import logger

from .auth import get_api_key
from .api_client import process_text
from .angle_loader import load_angle_template_objects
from .md_input_parser import ParsedMdInput, parse_md_file
from .shot_sheet import ShotSheet, shot_sheet_from_dict
from .payload_builder import build_user_content
from .shot_feasibility import build_shot_entries

ANGLE_TEMPLATE_DIR = Path("USER-FILES/01.CONFIG/angle-templates")

PLAN_SYSTEM_PROMPT = (
    "You are a film production assistant. Given the original scene image, produce a factual "
    "shot sheet describing exactly what is visible: the scene type, the frame size, the "
    "camera height, every human subject (id, description, position, facing, face visible, "
    "occlusion), notable props, lighting, and occlusion notes. Invent nothing that is not "
    "in the image. Reference images labelled as assets may also be provided. Bind a "
    "subject's 'asset' field to the asset id that best depicts that subject, and only when "
    "you are confident it is the same person or object; otherwise leave it null. A wrong "
    "binding is worse than none."
)

PLAN_INSTRUCTION = (
    "Analyse the provided image and return the shot sheet for this scene as JSON."
)

SHOT_SHEET_SCHEMA = {
    "type": "object",
    "properties": {
        "scene_type": {
            "type": "string",
            "enum": ["dialogue_2", "dialogue_3plus", "solo", "crowd_speaker",
                     "vehicle_interior", "vehicle_exterior", "landscape", "insert"],
        },
        "shot_size": {"type": "string", "enum": ["EWS", "WS", "MWS", "MS", "MCU", "CU", "ECU"]},
        "camera_height": {"type": "string", "enum": ["low", "eye", "high", "overhead"]},
        "subject_count": {"type": "integer"},
        "subjects": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string", "pattern": "^S[0-9]+$"},
                    "description": {"type": "string"},
                    "position": {"type": "string"},
                    "facing": {"type": "string"},
                    "face_visible": {"type": "boolean"},
                    "occluded": {"type": "boolean"},
                    "asset": {"type": ["string", "null"], "pattern": "^A[0-9]+$"},
                },
                "required": ["id", "description", "position", "facing", "face_visible", "occluded"],
                "additionalProperties": False,
            },
        },
        "props": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "description": {"type": "string"},
                    "position": {"type": "string"},
                },
                "required": ["id", "description", "position"],
                "additionalProperties": False,
            },
        },
        "lighting": {"type": "string"},
        "notes": {"type": "string"},
    },
    "required": ["scene_type", "shot_size", "camera_height", "subject_count",
                 "subjects", "props", "lighting", "notes"],
    "additionalProperties": False,
}

RESPONSE_FORMAT = {
    "type": "json_schema",
    "json_schema": {"name": "shot_sheet", "strict": True, "schema": SHOT_SHEET_SCHEMA},
}


def plan_file(
    parsed: ParsedMdInput, filename: str, client: OpenRouter, config: Dict[str, Any]
) -> ShotSheet:
    """One vision call → ShotSheet. Plan calls are exempt from the token floor (Q4).

    With declared assets the plan call receives every asset as a labelled
    image part (phase_1 §1.2); legacy files pass bare ref URLs as before.
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

    return sheet


def run_plan_mode(
    config: Dict[str, Any], md_files: List[Path], output_dir: Path
) -> Dict[str, Any]:
    """Run --plan for all input files with staging + atomic promotion.

    Any failure → zero enriched MDs + FAILURE_REPORT.md + non-zero exit (Q16).
    """
    from .preflight import run_preflight
    from .output_staging import create_staging_dir, promote_staging, fail_run
    from .reporting import setup_logging

    client = OpenRouter(api_key=get_api_key())
    run_preflight(config, md_files, client, plan_mode=True)

    staging_dir = create_staging_dir(output_dir)
    setup_logging(staging_dir)

    templates = load_angle_template_objects(ANGLE_TEMPLATE_DIR)
    start_time = datetime.now()

    try:
        for md_path in md_files:
            logger.info(f"Planning: {md_path.name}")
            parsed = parse_md_file(md_path)
            sheet = plan_file(parsed, md_path.name, client, config)
            entries = build_shot_entries(templates, sheet)

            from .plan_output_writer import write_enriched_md

            write_enriched_md(md_path, staging_dir, sheet, entries)
            logger.success(
                f"Planned {md_path.name}: {sheet.scene_type}, {sheet.shot_size}, "
                f"{len(entries)} shots"
            )
    except Exception as e:
        fail_run(staging_dir, output_dir, f"# FAILURE REPORT\n\n- Error: {e}\n")
        logger.error(f"Plan run aborted — no deliverables written: {e}")
        sys.exit(1)

    promote_staging(staging_dir, output_dir)

    duration = (datetime.now() - start_time).total_seconds()
    logger.success(f"Plan complete: {len(md_files)} files in {duration:.1f}s → {output_dir}")
    return {"processed": len(md_files), "output_dir": output_dir}
