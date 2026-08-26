"""Enriched MD writer for --plan output (Q17: verbatim copy + checkbox replacement)."""

import re
from pathlib import Path
from typing import List

import yaml

from .md_input_parser import CHECKBOX_PATTERN
from .shot_sheet import ShotSheet, SHOT_SHEET_FENCE
from .shot_feasibility import ShotEntry, HEADING_COVERAGE, HEADING_STRETCH

MD_IMAGE_PATTERN = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
HEADING_PATTERN = re.compile(r"^#{1,6}\s")


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
            }
            for s in sheet.subjects
        ],
        "props": [{"id": p.id, "description": p.description, "position": p.position} for p in sheet.props],
        "lighting": sheet.lighting,
        "notes": sheet.notes,
    }
    body = yaml.safe_dump(data, sort_keys=False, allow_unicode=True).rstrip("\n")
    return f"{SHOT_SHEET_FENCE}\n{body}\n```"


def _new_section_lines(sheet: ShotSheet, entries: List[ShotEntry]) -> List[str]:
    """The shot-sheet block + Coverage/Stretch sections that replace checkboxes."""
    lines = _render_shot_sheet_block(sheet).splitlines()
    lines.append("")

    for heading, ticked_only in ((HEADING_COVERAGE, None), (HEADING_STRETCH, False)):
        heading_entries = [
            e for e in entries
            if e.heading == heading and (ticked_only is None or e.ticked == ticked_only)
        ]
        if not heading_entries:
            continue
        lines.append(heading)
        for entry in heading_entries:
            mark = "x" if entry.ticked else " "
            lines.append(f"- [{mark}] {entry.label}")
        lines.append("")

    while lines and lines[-1] == "":
        lines.pop()
    return lines


def _drop_indexes(lines: List[str]) -> set:
    """Indexes to remove: checkboxes, headings directly above them, and any
    prior shot-sheet block."""
    remove = set()

    in_sheet_block = False
    for i, line in enumerate(lines):
        if line.strip() == SHOT_SHEET_FENCE:
            in_sheet_block = True
            remove.add(i)
            continue
        if in_sheet_block:
            remove.add(i)
            if line.strip() == "```":
                in_sheet_block = False
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
    shot-sheet block + Coverage/Stretch sections. If no checkbox section
    exists, the new section is inserted after the last image embed (Q19)."""
    lines = original_text.splitlines()
    remove = _drop_indexes(lines)
    kept = [line for i, line in enumerate(lines) if i not in remove]

    last_image_idx = None
    for i, line in enumerate(kept):
        if MD_IMAGE_PATTERN.search(line):
            last_image_idx = i

    insert_at = (last_image_idx + 1) if last_image_idx is not None else len(kept)
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
