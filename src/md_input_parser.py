"""MD file parser for multi-angle reframing feature."""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple
from natsort import natsorted
from loguru import logger

from .assets import Asset, extract_assets_block
from .shot_plan import ShotEntry, extract_shot_plan
from .shot_sheet import ShotSheet, extract_shot_sheet

MD_IMAGE_PATTERN = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
MD_LINK_PATTERN = re.compile(r"!?\[[^\]]*\]\([^)]+\)")
URL_PATTERN = re.compile(r"https?://|www\.", re.IGNORECASE)
CHECKBOX_PATTERN = re.compile(r"^-\s\[[ xX]\]\s.+$")
GROUNDS_PATTERN = re.compile(r"\s*\{([^}]*)\}\s*$")


@dataclass
class ParsedMdInput:
    """Parsed MD file contents."""

    scene: str
    original_image: str
    ref_images: List[str]
    checked_shots: List[str]
    all_checkbox_lines: List[str]
    shot_sheet: Optional[ShotSheet] = None
    shot_sheet_text: Optional[str] = None
    shot_entries: Optional[List[ShotEntry]] = None
    checked_shot_bindings: List[Tuple[str, Optional[List[str]]]] = field(
        default_factory=list
    )
    assets: Optional[List[Asset]] = None


def discover_md_files(input_dir: Path) -> List[Path]:
    """Discover all MD files in input directory using natsort.

    Args:
        input_dir: Path to input directory

    Returns:
        List of MD file paths in natural sorted order

    Raises:
        FileNotFoundError: If no MD files found
    """
    md_files = list(input_dir.rglob("*.md"))

    if not md_files:
        logger.error(f"No MD files found in {input_dir}")
        raise FileNotFoundError(f"No MD files found in {input_dir}")

    sorted_files = natsorted(md_files)
    logger.info(f"Found {len(sorted_files)} MD files")

    return sorted_files


def _is_checkbox_line(line: str) -> bool:
    """Check if a line is a valid checkbox."""
    return bool(CHECKBOX_PATTERN.match(line.strip()))


def _parse_checkbox_line(line: str) -> tuple[str, Optional[List[str]], bool]:
    """Parse a checkbox line into (shot_id, ground_ids, is_checked).

    Labels lead with the shot id (phase_2 §2.3): "SH01 — CU on the woman {A1}".
    The display text after the em dash is cosmetic — the shot-plan block is
    authoritative for label and intent.

    A trailing grounding list (phase_1 §1.3) is stripped:
        "SH01 — CU on the woman {A1}"  -> ground_ids ["A1"]
        "SH07 — XCU on the radio {}"   -> ground_ids []
        "SH01 — CU on the woman"       -> ground_ids None (no list present)

    Args:
        line: Raw checkbox line like '- [x] SH01 — CU on the woman {A1}'

    Returns:
        Tuple of (shot_id, ground_ids, is_checked)
    """
    stripped = line.strip()
    is_checked = stripped.startswith("- [x]") or stripped.startswith("- [X]")
    label = stripped[5:].strip()

    ground_ids: Optional[List[str]] = None
    grounds_match = GROUNDS_PATTERN.search(label)
    if grounds_match:
        ground_ids = [g.strip() for g in grounds_match.group(1).split(",") if g.strip()]
        label = label[: grounds_match.start()].rstrip()

    if " — " in label:
        shot_id = label.split(" — ", 1)[0].strip()
    else:
        shot_id = label.strip()

    return shot_id, ground_ids, is_checked


def _is_skippable_line(line: str) -> bool:
    """Check if a line matches a markdown embed/link or URL pattern."""
    return bool(MD_LINK_PATTERN.search(line) or URL_PATTERN.search(line))


def parse_md_file(file_path: Path) -> ParsedMdInput:
    """Parse MD file into scene, original image, ref images, and checked angles.

    Expected format:
        Optional ```yaml assets fenced block near the top (phase_1 §1.1)
        Lines before first image: scene description (Dataset A); lines
            matching embeds/links/URLs are skipped and logged
        First image line: ![original](url) (Dataset B)
        Optional ```yaml shot-sheet and ```yaml shot-plan blocks
        Then checkbox lines - [ ] / - [x] leading with shot ids (phase_2 §2.3)
        Then ![ref](url) lines (Dataset C)

    Args:
        file_path: Path to MD file

    Returns:
        ParsedMdInput dataclass

    Raises:
        ValueError: If file structure is invalid
    """
    content = file_path.read_text(encoding="utf-8")
    stripped_content = content.strip()
    assets, assets_fence = extract_assets_block(stripped_content, file_path.name)
    lines = stripped_content.splitlines()

    if not lines or not lines[0].strip():
        raise ValueError(f"Empty or missing scene description in {file_path.name}")

    def _in_assets_fence(i: int) -> bool:
        return assets_fence is not None and assets_fence[0] <= i <= assets_fence[1]

    images = []
    image_line_indices = []
    for i, line in enumerate(lines):
        if _in_assets_fence(i):
            continue
        match = MD_IMAGE_PATTERN.search(line)
        if match:
            images.append(match.group(2))
            image_line_indices.append(i)

    if not images:
        raise ValueError(f"No images found in {file_path.name}")

    first_image_idx = image_line_indices[0]
    scene_lines = []
    for i, line in enumerate(lines[:first_image_idx]):
        if _in_assets_fence(i):
            continue
        if _is_skippable_line(line):
            logger.info(f"Skipping line in {file_path.name} (embed/URL): {line.strip()}")
            continue
        scene_lines.append(line.strip())

    if not any(line.strip() for line in scene_lines):
        raise ValueError(f"Scene is empty after filtering in {file_path.name}")

    scene = "\n".join(scene_lines).strip()

    original_image = images[0]

    lines_after_first_image = lines[first_image_idx + 1:]

    checkbox_lines = []
    ref_image_lines = []
    in_checkbox_section = True

    for line in lines_after_first_image:
        stripped = line.strip()
        if not stripped:
            continue
        if in_checkbox_section and _is_checkbox_line(stripped):
            checkbox_lines.append(stripped)
        elif MD_IMAGE_PATTERN.search(stripped):
            in_checkbox_section = False
            ref_image_lines.append(stripped)
        elif _is_checkbox_line(stripped):
            checkbox_lines.append(stripped)
        else:
            in_checkbox_section = False

    checked_shots = []
    all_checkbox_labels = []
    checked_shot_bindings = []
    for cb_line in checkbox_lines:
        shot_id, ground_ids, is_checked = _parse_checkbox_line(cb_line)
        all_checkbox_labels.append(shot_id)
        if is_checked:
            checked_shots.append(shot_id)
            checked_shot_bindings.append((shot_id, ground_ids))

    ref_images = []
    for line in ref_image_lines:
        match = MD_IMAGE_PATTERN.search(line)
        if match:
            ref_images.append(match.group(2))

    shot_sheet, shot_sheet_text = extract_shot_sheet(content, file_path.name)

    declared_assets = {a.id for a in assets} if assets is not None else None
    roster = {s.id for s in shot_sheet.subjects} if shot_sheet else None
    shot_entries = extract_shot_plan(
        content, file_path.name, roster=roster, declared_assets=declared_assets
    )

    if assets is None:
        logger.info(
            f"{file_path.name}: no assets block — every shot receives all "
            f"{len(ref_images)} references"
        )

    logger.info(
        f"Parsed {file_path.name}: scene={len(scene)} chars, "
        f"original_image=1, checkboxes={len(checkbox_lines)}, "
        f"checked={len(checked_shots)}, ref_images={len(ref_images)}, "
        f"shot_sheet={'yes' if shot_sheet else 'no'}, "
        f"shot_plan={'yes' if shot_entries is not None else 'no'}, "
        f"assets={'yes' if assets is not None else 'no'}"
    )

    return ParsedMdInput(
        scene=scene,
        original_image=original_image,
        ref_images=ref_images,
        checked_shots=checked_shots,
        all_checkbox_lines=checkbox_lines,
        shot_sheet=shot_sheet,
        shot_sheet_text=shot_sheet_text,
        shot_entries=shot_entries,
        checked_shot_bindings=checked_shot_bindings,
        assets=assets,
    )
