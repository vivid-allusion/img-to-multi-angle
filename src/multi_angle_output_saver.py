"""Output saver for multi-angle reframing feature."""

from pathlib import Path
from typing import Dict, List
from loguru import logger

from .reporting import short_name


def copy_raw_md_file(input_path: Path, output_dir: Path) -> Path:
    """Copy raw MD file verbatim to output directory.

    Used when a file has zero checked angles.

    Args:
        input_path: Path to input MD file
        output_dir: Output directory

    Returns:
        Path to copied file
    """
    dest = output_dir / input_path.name
    dest.write_text(input_path.read_text(encoding="utf-8"), encoding="utf-8")
    logger.info(f"Copied raw MD file: {dest.relative_to(output_dir)}")
    return dest


def _slug(label: str) -> str:
    """Filename-safe slug from a shot label (Q10)."""
    kept = "".join(c if c.isalnum() else "_" for c in label.strip())
    return "_".join(part for part in kept.split("_") if part).lower()


def save_angle_outputs(
    output_dir: Path,
    input_name: str,
    angle_results: Dict[str, str],
    dataset_b: str,
    grounds_by_angle: Dict[str, List[str]],
    labels_by_shot: Dict[str, str],
) -> List[Path]:
    """Save all shot outputs for one input file.

    Creates subdirectory for input file, then one .md file per shot named
    `{input}_{shot_id}_{label-slug}.md` (Q10). Each shot embeds the master
    plus only its grounding refs (phase_1 §1.4); legacy files pass the full
    ref list for every shot. Output format is otherwise identical to before:
    prompt, blank line, then image embeds.

    Args:
        output_dir: Base output directory
        input_name: Input filename without extension
        angle_results: Dict mapping shot_id -> reframing_prompt (Dataset F)
        dataset_b: Original image URL
        grounds_by_angle: Dict mapping shot_id -> grounding ref URLs
        labels_by_shot: Dict mapping shot_id -> shot label (for filenames)

    Returns:
        List of saved file paths

    Raises:
        KeyError: If a result has no grounding or label entry — a silent ref
            loss must not ship.
    """
    sub_dir = output_dir / input_name
    sub_dir.mkdir(parents=True, exist_ok=True)

    saved = []
    for shot_id, prompt_f in angle_results.items():
        if shot_id not in grounds_by_angle or shot_id not in labels_by_shot:
            raise KeyError(f"no grounding/label entry for result '{shot_id}'")
        ref_images = "\n\n".join(
            f"![image]({url})" for url in grounds_by_angle[shot_id]
        )
        content = f"{prompt_f}\n\n![image]({dataset_b})"
        if ref_images:
            content += f"\n\n{ref_images}"
        content += "\n"
        slug = _slug(labels_by_shot[shot_id])
        filename = f"{input_name}_{shot_id}_{slug}.md" if slug else f"{input_name}_{shot_id}.md"
        output_path = sub_dir / filename
        output_path.write_text(content, encoding="utf-8")
        saved.append(output_path)
        logger.info(f"  ✓ Saved: {shot_id}_{slug}.md")

    logger.success(f"Generated {len(saved)} shot files for {short_name(input_name)}")

    return saved
