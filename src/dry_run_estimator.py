"""Dry run cost estimation for multi-angle processing."""

from typing import Dict, Any, List
from pathlib import Path
from openrouter import OpenRouter
from loguru import logger

from .dry_run_report_formatter import DryRunReportFormatter
from .md_input_parser import parse_md_file


class DryRunEstimator:
    """Estimates costs without making actual API calls."""

    def __init__(self, config: Dict[str, Any], api_key: str = "sk-dummy-for-counting"):
        """Initialize the dry run estimator.

        Args:
            config: Configuration dictionary
            api_key: API key (can be dummy for token counting only)
        """
        self.config = config
        self.client = OpenRouter(api_key=api_key)

    def estimate_md_file_cost(self, md_path: Path) -> Dict[str, Any]:
        """Estimate cost for one MD file across all checked shots.

        Args:
            md_path: Path to MD file

        Returns:
            Dictionary with token counts and estimated cost
        """
        parsed = parse_md_file(md_path)

        if parsed.shot_entries is None:
            raise ValueError(f"{md_path.name}: no shot-plan block — run --plan first")

        entries_by_id = {e.id: e for e in parsed.shot_entries}
        shots = []
        for shot_id in parsed.checked_shots:
            entry = entries_by_id.get(shot_id)
            if entry is None:
                raise ValueError(
                    f"{md_path.name}: ticked shot '{shot_id}' not in the shot-plan block"
                )
            shots.append(entry)

        system_tokens = len(self.config["system_prompt"]) // 4
        scene_tokens = len(parsed.scene) // 4

        shot_tokens = sum((len(e.label) + len(e.intent)) // 4 for e in shots)

        if "avg_output_tokens" not in self.config:
            raise ValueError("Missing 'avg_output_tokens' in configuration")
        avg_output = self.config["avg_output_tokens"]

        # §3.8: one --plan vision call per file (image tokens excluded, see warning)
        from .shot_planner import PLAN_INSTRUCTION

        plan_input = len(PLAN_INSTRUCTION) // 4
        plan_output = avg_output

        total_input = system_tokens + scene_tokens + shot_tokens + plan_input
        total_output = avg_output * len(shots) + plan_output

        return {
            "input_tokens": total_input,
            "output_tokens": total_output,
            "num_shots": len(shots),
        }

    def estimate_all_md_files(self, md_files: List[Path]) -> Dict[str, Any]:
        """Estimate costs for all MD files.

        Args:
            md_files: List of MD file paths

        Returns:
            Dictionary with estimation results
        """
        logger.warning(
            "Image input tokens are NOT included in this estimate — real costs will be higher"
        )

        results = {
            "estimated_files": 0,
            "total_estimated_cost": 0.0,
            "total_shots": 0,
            "file_estimates": [],
        }

        for md_file in md_files:
            try:
                usage_data = self.estimate_md_file_cost(md_file)

                from .cost_calculator import calculate_cost

                cost = calculate_cost(usage_data, self.config, self.config["model"])

                results["file_estimates"].append(
                    {
                        "filename": md_file.name,
                        "input_tokens": usage_data["input_tokens"],
                        "output_tokens": usage_data["output_tokens"],
                        "num_shots": usage_data["num_shots"],
                        "estimated_cost": cost,
                    }
                )

                results["estimated_files"] += 1
                results["total_shots"] += usage_data["num_shots"]
                results["total_estimated_cost"] += cost

            except Exception as e:
                logger.error(f"Error estimating {md_file}: {e}")

        return results

    def generate_cost_report(self, results: Dict[str, Any], output_dir: Path) -> Path:
        """Generate a markdown cost estimation report.

        Args:
            results: Estimation results
            output_dir: Directory to save report

        Returns:
            Path to the generated report
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        return DryRunReportFormatter.generate_cost_report(results, self.config, output_dir)
