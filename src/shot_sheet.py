"""Shot-sheet model: dataclasses, YAML-block extraction, and dict conversion.

The shot sheet is produced by --plan's vision call (shot_planner) and consumed
by the rewrite pipeline (md_input_parser → orchestrator). Schema per plan §3.3
+ Q13 (`occluded`). The shot list lives in shot_plan.py (phase_2 §2.2).
"""

import re
from dataclasses import dataclass
from typing import List, Optional, Tuple

from loguru import logger

import yaml

SHOT_SHEET_FENCE = "```yaml shot-sheet"


@dataclass
class ShotSubject:
    """One subject in a shot sheet roster.

    `asset` is the planner's binding to a declared asset (phase_1 §1.2), or
    None when no asset clearly depicts the subject.
    """

    id: str
    description: str
    position: str
    facing: str
    face_visible: bool
    occluded: bool
    asset: Optional[str] = None


@dataclass
class ShotProp:
    """One notable prop in a shot sheet."""

    id: str
    description: str
    position: str


@dataclass
class ShotSheet:
    """Parsed shot-sheet block (§3.3 schema + Q13 `occluded`)."""

    scene_type: str
    shot_size: str
    camera_height: str
    subject_count: int
    subjects: List[ShotSubject]
    props: List[ShotProp]
    lighting: str
    notes: str


def extract_shot_sheet(content: str, filename: str) -> Tuple[Optional[ShotSheet], Optional[str]]:
    """Extract the ```yaml shot-sheet fenced block, if present.

    Absent block → (None, None). Present but malformed → ValueError (Q22: hard-fail).
    """
    lines = content.splitlines()
    fence_idx = None
    for i, line in enumerate(lines):
        if line.strip() == SHOT_SHEET_FENCE:
            fence_idx = i
            break

    if fence_idx is None:
        return None, None

    block_lines = []
    for line in lines[fence_idx + 1:]:
        if line.strip() == "```":
            break
        block_lines.append(line)

    block_text = "\n".join(block_lines)
    try:
        data = yaml.safe_load(block_text)
    except yaml.YAMLError as e:
        raise ValueError(f"{filename}: malformed shot-sheet block: {e}") from e

    if not isinstance(data, dict):
        raise ValueError(f"{filename}: shot-sheet block must be a YAML mapping")

    try:
        sheet = shot_sheet_from_dict(data)
    except (KeyError, TypeError, ValueError) as e:
        raise ValueError(f"{filename}: invalid shot-sheet block: {e}") from e

    logger.info(f"{filename}: shot-sheet block parsed (scene_type={sheet.scene_type})")
    return sheet, block_text


def shot_sheet_from_dict(data: dict) -> ShotSheet:
    """Build a ShotSheet from a parsed YAML mapping (schema per §3.3 + Q13)."""
    subjects = []
    for s in data["subjects"]:
        asset = s.get("asset")
        if asset is not None and not re.match(r"^A\d+$", str(asset)):
            raise ValueError(f"subject {s['id']}: asset '{asset}' must match ^A\\d+$")
        subjects.append(
            ShotSubject(
                id=str(s["id"]),
                description=str(s["description"]),
                position=str(s["position"]),
                facing=str(s["facing"]),
                face_visible=bool(s["face_visible"]),
                occluded=bool(s.get("occluded", False)),
                asset=str(asset) if asset is not None else None,
            )
        )
    props = [
        ShotProp(id=str(p["id"]), description=str(p["description"]), position=str(p["position"]))
        for p in data.get("props", [])
    ]
    return ShotSheet(
        scene_type=str(data["scene_type"]),
        shot_size=str(data["shot_size"]),
        camera_height=str(data["camera_height"]),
        subject_count=int(data.get("subject_count", len(subjects))),
        subjects=subjects,
        props=props,
        lighting=str(data.get("lighting", "")),
        notes=str(data.get("notes", "")),
    )
