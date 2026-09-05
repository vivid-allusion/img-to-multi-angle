"""Shot-sheet model: dataclasses, YAML-block extraction, and dict conversion.

The shot sheet holds scene subject definitions and asset bindings.
"""

import re
from dataclasses import dataclass, field
from typing import List, Optional

from .fences import extract_fenced_block

SHOT_SHEET_FENCE = "```yaml shot-sheet"


@dataclass
class ShotSubject:
    """One subject in a scene roster.

    `asset` is the binding to a declared asset (A1, A2, ...), or None.
    """

    id: str
    description: str
    asset: Optional[str] = None
    position: str = ""
    facing: str = ""
    face_visible: bool = True
    occluded: bool = False


@dataclass
class ShotProp:
    """Notable prop in a scene."""

    id: str
    description: str
    position: str = ""


@dataclass
class ShotSheet:
    """Scene subject roster and metadata."""

    subjects: List[ShotSubject]
    scene_type: str = ""
    shot_size: str = ""
    camera_height: str = ""
    subject_count: int = 0
    props: List[ShotProp] = field(default_factory=list)
    lighting: str = ""
    notes: str = ""


def extract_shot_sheet(content: str, filename: str) -> Optional[ShotSheet]:
    """Extract the ```yaml shot-sheet fenced block, if present.

    Absent block → None. Present but malformed → ValueError (fail fast).
    """
    data, _ = extract_fenced_block(content, SHOT_SHEET_FENCE, filename, "shot-sheet")
    if data is None:
        return None

    if not isinstance(data, dict):
        raise ValueError(f"{filename}: shot-sheet block must be a YAML mapping")

    try:
        sheet = shot_sheet_from_dict(data)
    except (KeyError, TypeError, ValueError) as e:
        raise ValueError(f"{filename}: invalid shot-sheet block: {e}") from e

    return sheet


def shot_sheet_from_dict(data: dict) -> ShotSheet:
    """Build a ShotSheet from a parsed YAML mapping."""
    subjects = []
    for s in data.get("subjects", []):
        asset = s.get("asset")
        if asset is not None and not re.match(r"^A\d+$", str(asset)):
            raise ValueError(f"subject {s['id']}: asset '{asset}' must match ^A\\d+$")
        subjects.append(
            ShotSubject(
                id=str(s["id"]),
                description=str(s["description"]),
                asset=str(asset) if asset is not None else None,
                position=str(s.get("position", "")),
                facing=str(s.get("facing", "")),
                face_visible=bool(s.get("face_visible", True)),
                occluded=bool(s.get("occluded", False)),
            )
        )
    props = [
        ShotProp(
            id=str(p["id"]),
            description=str(p["description"]),
            position=str(p.get("position", "")),
        )
        for p in data.get("props", [])
    ]
    return ShotSheet(
        subjects=subjects,
        scene_type=str(data.get("scene_type", "")),
        shot_size=str(data.get("shot_size", "")),
        camera_height=str(data.get("camera_height", "")),
        subject_count=int(data.get("subject_count", len(subjects))),
        props=props,
        lighting=str(data.get("lighting", "")),
        notes=str(data.get("notes", "")),
    )
