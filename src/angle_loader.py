"""Angle template loader for multi-angle reframing feature.

Templates are Markdown files with YAML frontmatter. Plain `.txt` files without
frontmatter load with permissive defaults. `NEW.md` is the owner's brainstorming
pad and is always skipped.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List
from natsort import natsorted
from loguru import logger

import yaml

SKIP_NAMES = {"new.md"}

DEFAULT_FRONTMATTER = {
    "families": ["all"],
    "transform": "subtractive",
    "min_source_size": "",
    "subject_bound": False,
    "azimuth_delta": 0,
    "height_delta": 0,
    "shot_size": "",
    "subject_arity": 1,
}


@dataclass
class AngleTemplate:
    """One angle template with its planning metadata."""

    name: str
    label: str
    body: str
    families: List[str] = field(default_factory=lambda: ["all"])
    transform: str = "subtractive"
    min_source_size: str = ""
    subject_bound: bool = False
    azimuth_delta: int = 0
    height_delta: int = 0
    shot_size: str = ""
    subject_arity: int = 1


def _template_files(template_dir: Path) -> List[Path]:
    """Glob template files (md + txt), skip the owner's pad, natsort."""
    if not template_dir.exists():
        logger.error(f"Angle templates directory not found: {template_dir}")
        raise FileNotFoundError(f"Angle templates directory not found: {template_dir}")

    files = list(template_dir.glob("*.md")) + list(template_dir.glob("*.txt"))
    files = [f for f in files if f.name.lower() not in SKIP_NAMES]

    if not files:
        logger.error(f"No angle templates found in {template_dir}")
        raise FileNotFoundError(f"No angle templates found in {template_dir}")

    return natsorted(files, key=lambda p: p.name)


def get_available_angle_names(template_dir: Path) -> List[str]:
    """Get list of available angle names (filename stems) in natural order."""
    names = [tf.stem for tf in _template_files(template_dir)]
    logger.info(f"Found {len(names)} available angles in {template_dir}")
    return names


def _split_frontmatter(content: str, filename: str) -> tuple[Dict, str]:
    """Split frontmatter from body. Returns (frontmatter_dict, body)."""
    if not content.startswith("---\n"):
        return {}, content.strip()

    yaml_block, sep, body = content[4:].partition("\n---\n")
    if not sep:
        logger.warning(f"{filename}: unterminated frontmatter — treating whole file as body")
        return {}, content.strip()

    try:
        meta = yaml.safe_load(yaml_block) or {}
    except yaml.YAMLError as e:
        raise ValueError(f"{filename}: invalid frontmatter YAML: {e}") from e

    if not isinstance(meta, dict):
        raise ValueError(f"{filename}: frontmatter must be a YAML mapping")

    return meta, body.strip()


def load_angle_template_objects(template_dir: Path) -> Dict[str, AngleTemplate]:
    """Load templates with frontmatter metadata. Plain txt files get defaults."""
    templates = {}
    for tf in _template_files(template_dir):
        meta, body = _split_frontmatter(tf.read_text(encoding="utf-8"), tf.name)

        merged = dict(DEFAULT_FRONTMATTER)
        merged.update(meta)

        angle_name = tf.stem
        label = str(merged.get("label") or angle_name.replace("_", " "))

        templates[angle_name] = AngleTemplate(
            name=angle_name,
            label=label,
            body=body,
            families=list(merged["families"]),
            transform=str(merged["transform"]),
            min_source_size=str(merged["min_source_size"] or ""),
            subject_bound=bool(merged["subject_bound"]),
            azimuth_delta=int(merged["azimuth_delta"]),
            height_delta=int(merged["height_delta"]),
            shot_size=str(merged["shot_size"] or ""),
            subject_arity=int(merged["subject_arity"]),
        )

    logger.info(f"Loaded {len(templates)} angle templates from {template_dir}")
    return templates


def load_angle_templates(template_dir: Path) -> Dict[str, str]:
    """Load template bodies keyed by angle name (legacy callers)."""
    return {name: t.body for name, t in load_angle_template_objects(template_dir).items()}
