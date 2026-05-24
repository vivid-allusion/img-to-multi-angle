"""Batch result file I/O handler for multi-angle processing."""

import json
from typing import Dict, Any, Optional
from pathlib import Path
from loguru import logger

from .config import get_output_directory


class BatchResultSaver:
    """Handles saving batch results to files."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize result saver.

        Args:
            config: Configuration dictionary
        """
        self.config = config

    def save_results(
        self, results: Dict[str, Any], output_dir: Optional[Path] = None
    ) -> Dict[str, Path]:
        """Save parsed results to output files.

        Args:
            results: Parsed results dictionary
            output_dir: Optional output directory override

        Returns:
            Dictionary of saved file paths
        """
        if output_dir is None:
            output_dir = self._create_output_directory()

        output_dir.mkdir(parents=True, exist_ok=True)

        saved_files = {}

        if results["succeeded"]:
            saved_files.update(self._save_multi_angle_results(results["succeeded"], output_dir))

        if results["failed"]:
            saved_files.update(
                self._save_failed_results(results["failed"], results["failure_count"], output_dir)
            )

        saved_files.update(self._save_summary_report(results, output_dir))

        return saved_files

    def _create_output_directory(self) -> Path:
        """Create timestamped output directory with multi-angle indicator."""
        return get_output_directory(self.config, suffix="MULTI-ANGLE-MD")

    def _save_multi_angle_results(self, succeeded: list, output_dir: Path) -> Dict[str, Path]:
        """Save multi-angle results with subdirectory structure.

        Args:
            succeeded: List of successful result dicts
            output_dir: Base output directory

        Returns:
            Dict of saved file paths
        """
        saved = {}

        success_file = output_dir / "batch_results.json"
        with open(success_file, "w") as f:
            json.dump(succeeded, f, indent=2)
        saved["results"] = success_file

        for result in succeeded:
            input_name = result.get("input_name", "unknown")
            angle_name = result.get("angle_name", "unknown")
            response = result.get("response", "")

            sub_dir = output_dir / input_name
            sub_dir.mkdir(parents=True, exist_ok=True)

            ref_images = result.get("ref_images", "")
            original_image = result.get("original_image", "")

            content = f"{response}\n\n![image]({original_image})\n\n{ref_images}\n"
            filename = f"{input_name}_{angle_name}.md"
            output_path = sub_dir / filename
            output_path.write_text(content, encoding="utf-8")

            logger.info(f"Saved: {output_path.relative_to(output_dir)}")

        return saved

    def _save_failed_results(self, failed: list, count: int, output_dir: Path) -> Dict[str, Path]:
        """Save failed batch results."""
        failure_file = output_dir / "batch_failures.json"
        with open(failure_file, "w") as f:
            json.dump(failed, f, indent=2)

        logger.warning(f"Saved {count} failed results to {failure_file}")

        return {"failures": failure_file}

    def _save_summary_report(self, results: Dict[str, Any], output_dir: Path) -> Dict[str, Path]:
        """Save batch summary report."""
        from .batch_report_generator import BatchReportGenerator

        generator = BatchReportGenerator(self.config)
        summary = generator.create_summary_report(results)

        summary_file = output_dir / "BATCH_SUMMARY.md"
        with open(summary_file, "w") as f:
            f.write(summary)

        logger.info(f"Saved batch summary to {summary_file}")

        return {"summary": summary_file}
