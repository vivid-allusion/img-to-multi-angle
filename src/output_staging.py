"""Staging directory lifecycle for atomic output promotion.

The final output directory is only created by `promote_staging`. Until then
all artifacts live in a hidden sibling staging directory.
"""

import os
from pathlib import Path
from loguru import logger


def create_staging_dir(final_output_dir: Path) -> Path:
    """Create a staging directory as a sibling of the final output directory."""
    parent = final_output_dir.parent
    parent.mkdir(parents=True, exist_ok=True)
    staging = parent / f".{final_output_dir.name}.staging"
    staging.mkdir()
    logger.info(f"Created staging directory: {staging}")
    return staging


def promote_staging(staging: Path, final_output_dir: Path) -> None:
    """Atomically rename staging to the final output directory."""
    os.replace(staging, final_output_dir)
    logger.info(f"Promoted staging to: {final_output_dir}")


def fail_run(staging: Path, final_output_dir: Path, report: str) -> None:
    """Rename staging to _FAILED and write the failure report."""
    failed_dir = final_output_dir.parent / f"{final_output_dir.name}_FAILED"
    os.replace(staging, failed_dir)
    (failed_dir / "FAILURE_REPORT.md").write_text(report, encoding="utf-8")
    logger.error(f"Run failed — artifacts moved to: {failed_dir}")
