"""Shot-plan model: the planner's shot list (phase_2 §2.2, full record per Q8).

Each entry's `intent` is concrete prose — subject ids never appear in it (Q9);
`subject_ids` is metadata for validation and the Phase-1 WARN checks. `grounds`
holds the asset ids that ground the shot ([] = master only, the master itself
is implicit and never listed).
"""

import re
from dataclasses import dataclass
from typing import List, Optional, Set

from loguru import logger

import yaml

SHOT_PLAN_FENCE = "```yaml shot-plan"

SHOT_ID_PATTERN = re.compile(r"^SH\d+$")


@dataclass
class ShotEntry:
    """One proposed shot from the planner."""

    id: str
    label: str
    intent: str
    subject_ids: List[str]
    grounds: List[str]
    recommended: bool
    reason: str


def shot_entries_from_list(
    data: List[dict],
    filename: str,
    roster: Optional[Set[str]] = None,
    declared_assets: Optional[Set[str]] = None,
) -> List[ShotEntry]:
    """Build ShotEntry list from a parsed YAML list (schema per §2.2 + Q8).

    Structural checks (id pattern, duplicates) always run. When `roster` is
    given, subject ids must resolve; when `declared_assets` is given, grounds
    ids must resolve (an undeclared ground aborts — plan §0.4 traceability).
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
                subject_ids=subject_ids,
                grounds=grounds,
                recommended=bool(item["recommended"]),
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

    Absent block → None. Present but malformed → ValueError (fail fast, Q22
    pattern). Cross-checks (roster/declared assets) run when the sets are
    supplied.
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

    logger.info(f"{filename}: shot-plan block parsed ({len(entries)} shots)")
    return entries
