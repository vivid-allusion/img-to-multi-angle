"""Shot-plan model: the planner's shot list.

Each entry's `intent` is concrete prose describing the camera vantage point,
framing, depth of field, and focal emphasis. `grounds` holds the asset ids that
ground the shot ([] = master only).
"""

import re
from dataclasses import dataclass, field
from typing import List, Optional, Set

from loguru import logger
import yaml

SHOT_PLAN_FENCE = "```yaml shot-plan"

SHOT_ID_PATTERN = re.compile(r"^SH\d+$")

# The coverage slot each shot fills. Mandatory types for human-present scenes are
# enforced in shot_planner.plan_file(); this is the shared vocabulary.
SHOT_TYPES = (
    "face_cu",
    "medium_action",
    "hands_insert",
    "wide_master",
    "dynamic_vantage",
    "object_insert",
)

# Coverage a scene containing people must include (feature spec §2). Scenes with
# no human subjects are exempt — see shot_planner.plan_file().
MANDATORY_SHOT_TYPES = frozenset({"face_cu", "hands_insert", "wide_master"})


@dataclass
class ShotEntry:
    """One proposed shot from the planner."""

    id: str
    label: str
    intent: str
    shot_type: str = ""
    subject_ids: List[str] = field(default_factory=list)
    grounds: List[str] = field(default_factory=list)
    recommended: bool = True
    reason: str = ""


def shot_entries_from_list(
    data: List[dict],
    filename: str,
    roster: Optional[Set[str]] = None,
    declared_assets: Optional[Set[str]] = None,
) -> List[ShotEntry]:
    """Build ShotEntry list from a parsed YAML list.

    Structural checks (id pattern, duplicates) always run. When `roster` is
    given, subject ids must resolve; when `declared_assets` is given, grounds
    ids must resolve (an undeclared ground aborts).
    """
    entries: List[ShotEntry] = []
    seen: Set[str] = set()

    for item in data:
        shot_id = str(item["id"])
        if not SHOT_ID_PATTERN.match(shot_id):
            raise ValueError(f"{filename}: shot id '{shot_id}' must match ^SH\\d+$")
        if shot_id in seen:
            raise ValueError(f"{filename}: duplicate shot id '{shot_id}'")
        seen.add(shot_id)

        subject_ids = [str(s) for s in item.get("subject_ids", [])]
        unknown_subjects = [s for s in subject_ids if roster is not None and s not in roster]
        if unknown_subjects:
            raise ValueError(
                f"{filename}: shot {shot_id} names unknown subject id(s) "
                f"{unknown_subjects} — roster: {sorted(roster) if roster else 'none'}"
            )

        grounds = [str(g) for g in item.get("grounds", [])]
        if declared_assets is not None:
            undeclared = [g for g in grounds if g not in declared_assets]
            if undeclared:
                raise ValueError(
                    f"{filename}: shot {shot_id} grounds on undeclared asset id(s) "
                    f"{undeclared} — declared: {sorted(declared_assets)}"
                )

        shot_type = str(item.get("shot_type", "")).strip()
        if shot_type and shot_type not in SHOT_TYPES:
            raise ValueError(
                f"{filename}: shot {shot_id} has unknown shot_type '{shot_type}' — "
                f"expected one of {list(SHOT_TYPES)}"
            )

        intent = str(item["intent"]).strip()
        label = str(item["label"]).strip()
        if not intent:
            raise ValueError(f"{filename}: shot {shot_id} has an empty intent")
        if not label:
            raise ValueError(f"{filename}: shot {shot_id} has an empty label")

        entries.append(
            ShotEntry(
                id=shot_id,
                label=label,
                intent=intent,
                shot_type=shot_type,
                subject_ids=subject_ids,
                grounds=grounds,
                recommended=bool(item.get("recommended", True)),
                reason=str(item.get("reason", "")),
            )
        )

    return entries


def extract_shot_plan(
    content: str,
    filename: str,
    roster: Optional[Set[str]] = None,
    declared_assets: Optional[Set[str]] = None,
) -> Optional[List[ShotEntry]]:
    """Extract the ```yaml shot-plan fenced block, if present.

    Absent block → None. Present but malformed → ValueError (fail fast).
    """
    lines = content.splitlines()
    fence_idx = None
    for i, line in enumerate(lines):
        if line.strip() == SHOT_PLAN_FENCE:
            fence_idx = i
            break

    if fence_idx is None:
        return None

    block_lines = []
    for line in lines[fence_idx + 1:]:
        if line.strip() == "```":
            break
        block_lines.append(line)

    block_text = "\n".join(block_lines)
    try:
        data = yaml.safe_load(block_text)
    except yaml.YAMLError as e:
        raise ValueError(f"{filename}: malformed shot-plan block: {e}") from e

    if not isinstance(data, list):
        raise ValueError(f"{filename}: shot-plan block must be a YAML list")

    try:
        entries = shot_entries_from_list(data, filename, roster, declared_assets)
    except (KeyError, TypeError, ValueError) as e:
        raise ValueError(f"{filename}: invalid shot-plan block: {e}") from e

    return entries
