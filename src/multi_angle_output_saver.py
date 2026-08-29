"""Output saver for multi-angle reframing feature."""

from pathlib import Path
from typing import Dict, List
from loguru import logger


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


def save_angle_outputs(
    output_dir: Path,
    input_name: str,
    angle_results: Dict[str, str],
    dataset_b: str,
    grounds_by_angle: Dict[str, List[str]],
) -> List[Path]:
    """Save all angle outputs for one input file.

    Creates subdirectory for input file, then one .md file per angle. Each
    shot embeds the master plus only its grounding refs (phase_1 §1.4);
    legacy files pass the full ref list for every angle. Output format is
    otherwise identical to before: prompt, blank line, then image embeds.

    Args:
        output_dir: Base output directory
        input_name: Input filename without extension
        angle_results: Dict mapping result_key -> reframing_prompt (Dataset F)
        dataset_b: Original image URL
        grounds_by_angle: Dict mapping result_key -> grounding ref URLs

    Returns:
        List of saved file paths

    Raises:
        KeyError: If a result has no grounding entry — a silent ref loss
            must not ship.
    """
    sub_dir = output_dir / input_name
    sub_dir.mkdir(parents=True, exist_ok=True)

    saved = []
    for angle_name, prompt_f in angle_results.items():
        if angle_name not in grounds_by_angle:
            raise KeyError(f"no grounding entry for result '{angle_name}'")
        ref_images = "\n\n".join(
            f"![image]({url})" for url in grounds_by_angle[angle_name]
        )
        content = f"{prompt_f}\n\n![image]({dataset_b})"
        if ref_images:
            content += f"\n\n{ref_images}"
        content += "\n"
        filename = f"{input_name}_{angle_name}.md"
        output_path = sub_dir / filename
        output_path.write_text(content, encoding="utf-8")
        saved.append(output_path)
        logger.info(f"Saved: {output_path.relative_to(output_dir)}")

    logger.success(f"Saved {len(saved)} angle outputs for {input_name}")

    return saved
