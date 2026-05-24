"""Dry run cost estimation for multi-angle processing."""

from typing import Dict, Any, List
from pathlib import Path
from openrouter import OpenRouter
from loguru import logger

from .dry_run_report_formatter import DryRunReportFormatter
from .md_input_parser import parse_md_file
from .angle_loader import load_angle_templates
from .api_client import build_system_prompt_with_scene


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

    def estimate_md_file_cost(
        self, md_path: Path, angles: Dict[str, str]
    ) -> Dict[str, Any]:
        """Estimate cost for one MD file across all angles.

        Args:
            md_path: Path to MD file
            angles: Dict of angle_name -> template content

        Returns:
            Dictionary with token counts and estimated cost
        """
        parsed = parse_md_file(md_path)

        system_prompt = build_system_prompt_with_scene(self.config["system_prompt"], parsed.scene)
        system_tokens = len(system_prompt) // 4

        angles_to_use = {k: v for k, v in angles.items() if k in parsed.checked_angles} if parsed.checked_angles else angles
        angle_tokens = sum(len(t) // 4 for t in angles_to_use.values())

        if "avg_output_tokens" not in self.config:
            raise ValueError("Missing 'avg_output_tokens' in configuration")
        avg_output = self.config["avg_output_tokens"]

        total_input = system_tokens + angle_tokens
        total_output = avg_output * len(angles_to_use)

        return {
            "input_tokens": total_input,
            "output_tokens": total_output,
            "num_angles": len(angles_to_use),
        }

    def estimate_all_md_files(self, md_files: List[Path]) -> Dict[str, Any]:
        """Estimate costs for all MD files.

        Args:
            md_files: List of MD file paths

        Returns:
            Dictionary with estimation results
        """
        angle_dir = Path("USER-FILES/01.CONFIG/angle-templates")
        angles = load_angle_templates(angle_dir)

        results = {
            "estimated_files": 0,
            "total_estimated_cost": 0.0,
            "total_angles": 0,
            "file_estimates": [],
        }

        for md_file in md_files:
            try:
                usage_data = self.estimate_md_file_cost(md_file, angles)

                from .cost_calculator import calculate_cost

                cost = calculate_cost(
                    usage_data,
                    self.config,
                    self.config["model"],
                    self.config["batch_mode"],
                )

                results["file_estimates"].append(
                    {
                        "filename": md_file.name,
                        "input_tokens": usage_data["input_tokens"],
                        "output_tokens": usage_data["output_tokens"],
                        "num_angles": usage_data["num_angles"],
                        "estimated_cost": cost,
                    }
                )

                results["estimated_files"] += 1
                results["total_angles"] += usage_data["num_angles"]
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
        return DryRunReportFormatter.generate_cost_report(results, self.config, output_dir)
