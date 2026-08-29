"""Enriched MD writer for --plan output (Q17: verbatim copy + checkbox replacement).

Phase 2 §2.3: the new section is the shot-sheet block + shot-plan block +
Recommended/Possible checkbox sections (Q12: neutral "Possible" heading; Q8:
the shot-plan block carries the full record).
"""

import re
from pathlib import Path
from typing import List

import yaml

from .md_input_parser import CHECKBOX_PATTERN
from .assets import ASSETS_FENCE
from .shot_plan import SHOT_PLAN_FENCE, ShotEntry
from .shot_sheet import SHOT_SHEET_FENCE, ShotSheet

MD_IMAGE_PATTERN = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
HEADING_PATTERN = re.compile(r"^#{1,6}\s")
FENCE_NAMES = (ASSETS_FENCE, SHOT_SHEET_FENCE, SHOT_PLAN_FENCE)

HEADING_RECOMMENDED = "### Recommended"
HEADING_POSSIBLE = "### Possible"


def _render_shot_sheet_block(sheet: ShotSheet) -> str:
    """Serialize the shot sheet back into its fenced YAML block."""
    data = {
        "scene_type": sheet.scene_type,
        "shot_size": sheet.shot_size,
        "camera_height": sheet.camera_height,
        "subject_count": sheet.subject_count,
        "subjects": [
            {
                "id": s.id,
                "description": s.description,
                "position": s.position,
                "facing": s.facing,
                "face_visible": s.face_visible,
                "occluded": s.occluded,
                "asset": s.asset,
            }
            for s in sheet.subjects
        ],
        "props": [{"id": p.id, "description": p.description, "position": p.position} for p in sheet.props],
        "lighting": sheet.lighting,
        "notes": sheet.notes,
    }
    body = yaml.safe_dump(data, sort_keys=False, allow_unicode=True).rstrip("\n")
    return f"{SHOT_SHEET_FENCE}\n{body}\n```"


def _render_shot_plan_block(entries: List[ShotEntry]) -> str:
    """Serialize the shot list back into its fenced YAML block (full record, Q8)."""
    data = [
        {
            "id": e.id,
            "label": e.label,
            "intent": e.intent,
            "subject_ids": e.subject_ids,
            "grounds": e.grounds,
            "recommended": e.recommended,
            "reason": e.reason,
        }
        for e in entries
    ]
    body = yaml.safe_dump(data, sort_keys=False, allow_unicode=True).rstrip("\n")
    return f"{SHOT_PLAN_FENCE}\n{body}\n```"


def _grounds_for(entry: ShotEntry) -> str:
    """Braces for one entry, derived from its declared grounds (phase_1 §1.3).

    The master is implicit and never listed; no grounds → "{}".
    """
    return "{" + ", ".join(entry.grounds) + "}"


def _new_section_lines(sheet: ShotSheet, entries: List[ShotEntry]) -> List[str]:
    """The shot-sheet + shot-plan blocks and checkbox sections that replace
    the old checkbox list."""
    lines = _render_shot_sheet_block(sheet).splitlines()
    lines.append("")
    lines.extend(_render_shot_plan_block(entries).splitlines())
    lines.append("")

    for heading, heading_entries in (
        (HEADING_RECOMMENDED, [e for e in entries if e.recommended]),
        (HEADING_POSSIBLE, [e for e in entries if not e.recommended]),
    ):
        if not heading_entries:
            continue
        lines.append(heading)
        for entry in heading_entries:
            mark = "x" if entry.recommended else " "
            lines.append(f"- [{mark}] {entry.id} — {entry.label} {_grounds_for(entry)}")
        lines.append("")

    while lines and lines[-1] == "":
        lines.pop()
    return lines


def _drop_indexes(lines: List[str]) -> set:
    """Indexes to remove: checkboxes, headings directly above them, and any
    prior shot-sheet or shot-plan blocks."""
    remove = set()

    in_block = False
    for i, line in enumerate(lines):
        if line.strip() in (SHOT_SHEET_FENCE, SHOT_PLAN_FENCE):
            in_block = True
            remove.add(i)
            continue
        if in_block:
            remove.add(i)
            if line.strip() == "```":
                in_block = False
            continue
        if CHECKBOX_PATTERN.match(line.strip()):
            remove.add(i)

    for i, line in enumerate(lines):
        if CHECKBOX_PATTERN.match(line.strip()):
            j = i - 1
            while j >= 0 and lines[j].strip() == "":
                j -= 1
            if j >= 0 and HEADING_PATTERN.match(lines[j]):
                remove.add(j)

    return remove


def build_enriched_md(original_text: str, sheet: ShotSheet, entries: List[ShotEntry]) -> str:
    """Copy the input MD verbatim, replacing the checkbox section with the
    shot-sheet + shot-plan blocks and the Recommended/Possible sections. If no
    checkbox section exists, the new section is inserted after the last image
    embed or fenced block (Q19; the §2.3 layout keeps blocks before checkboxes)."""
    lines = original_text.splitlines()
    remove = _drop_indexes(lines)
    kept = [line for i, line in enumerate(lines) if i not in remove]

    insert_at = None
    in_fence = False
    for i, line in enumerate(kept):
        stripped = line.strip()
        if not in_fence and stripped in FENCE_NAMES:
            in_fence = True
            continue
        if in_fence:
            if stripped == "```":
                in_fence = False
                insert_at = i
            continue
        if MD_IMAGE_PATTERN.search(line):
            insert_at = i

    if insert_at is None:
        insert_at = len(kept) - 1
    insert_at += 1
    while insert_at < len(kept) and kept[insert_at].strip() == "":
        insert_at += 1

    new_lines = _new_section_lines(sheet, entries)
    prefix = kept[:insert_at]
    while prefix and prefix[-1].strip() == "":
        prefix.pop()
    prefix.append("")
    result = prefix + new_lines + kept[insert_at:]
    return "\n".join(result).rstrip("\n") + "\n"


def write_enriched_md(
    input_path: Path, output_dir: Path, sheet: ShotSheet, entries: List[ShotEntry]
) -> Path:
    """Write the enriched MD into the output (staging) directory."""
    content = build_enriched_md(input_path.read_text(encoding="utf-8"), sheet, entries)
    dest = output_dir / input_path.name
    dest.write_text(content, encoding="utf-8")
    return dest
