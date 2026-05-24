"""Output saver for multi-angle reframing feature."""

from pathlib import Path
from typing import Dict, List
from loguru import logger


def save_angle_outputs(
    output_dir: Path,
    input_name: str,
    angle_results: Dict[str, str],
    dataset_b: str,
    dataset_c: List[str],
) -> List[Path]:
    """Save all angle outputs for one input file.

    Creates subdirectory for input file, then one .md file per angle.

    Args:
        output_dir: Base output directory
        input_name: Input filename without extension
        angle_results: Dict mapping angle_name -> reframing_prompt (Dataset F)
        dataset_b: Original image URL
        dataset_c: Character sheet reference URLs

    Returns:
        List of saved file paths
    """
    sub_dir = output_dir / input_name
    sub_dir.mkdir(parents=True, exist_ok=True)

    ref_images = "\n\n".join(f"![image]({url})" for url in dataset_c)

    saved = []
    for angle_name, prompt_f in angle_results.items():
        content = f"{prompt_f}\n\n![image]({dataset_b})\n\n{ref_images}\n"
        filename = f"{input_name}_{angle_name}.md"
        output_path = sub_dir / filename
        output_path.write_text(content, encoding="utf-8")
        saved.append(output_path)
        logger.info(f"Saved: {output_path.relative_to(output_dir)}")

    logger.success(f"Saved {len(saved)} angle outputs for {input_name}")

    return saved
