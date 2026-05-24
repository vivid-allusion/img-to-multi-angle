"""Multi-angle orchestrator for MD-to-Multi-Angle processing."""

from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List
from openrouter import OpenRouter
from loguru import logger

from .base_orchestrator import BaseOrchestrator
from .md_input_parser import parse_md_file
from .angle_loader import load_angle_templates
from .user_message_template import load_user_message_template, render_user_message
from .api_client import process_text, build_system_prompt, build_system_prompt_with_scene
from .multi_angle_output_saver import save_angle_outputs
from .data_models import ProcessingResult, UsageData
from .cost_calculator import calculate_cost


class MultiAngleOrchestrator(BaseOrchestrator):
    """Orchestrates MD file multi-angle processing workflow."""

    def __init__(self, config: Dict[str, Any], input_dir: Path):
        """Initialize orchestrator.

        Args:
            config: Configuration dictionary
            input_dir: Input directory path
        """
        super().__init__(config)
        self.input_dir = input_dir
        self.angle_template_dir = Path("USER-FILES/01.CONFIG/angle-templates")
        self.user_message_path = Path("USER-FILES/01.CONFIG/user_message.md")
        self.angles: Dict[str, str] = {}
        self.um_template: str = ""
        self.use_cache: bool = False

    def process_batch(
        self, files: List[Path], client: OpenRouter, output_dir: Path
    ) -> Dict[str, Any]:
        """Process all MD files sequentially, generating multi-angle outputs.

        Args:
            files: List of MD file paths
            client: OpenRouter API client
            output_dir: Output directory

        Returns:
            Processing statistics
        """
        stats = {
            "processed": 0,
            "failed": 0,
            "total": len(files),
            "total_cost": 0.0,
            "results": [],
            "errors": [],
        }

        self.angles = load_angle_templates(self.angle_template_dir)
        self.um_template = load_user_message_template(self.user_message_path)
        cache_config = self.config.get("cache_config", {})
        self.use_cache = cache_config.get("enabled", False) and len(self.angles) >= 2

        for md_path in files:
            result = self._process_single_file(md_path, client, output_dir)

            if result.success:
                stats["processed"] += 1
                stats["total_cost"] += result.cost
            else:
                stats["failed"] += 1
                if result.error:
                    stats["errors"].append(f"{result.filename}: {result.error}")

            stats["results"].append(result)

        return stats

    def _process_single_file(
        self,
        md_path: Path,
        client: OpenRouter,
        output_dir: Path,
    ) -> ProcessingResult:
        """Process one MD file across all angles.

        Args:
            md_path: Path to MD file
            client: OpenRouter API client
            output_dir: Output directory

        Returns:
            ProcessingResult with success/failure info
        """
        input_name = md_path.stem
        logger.info(f"Processing: {md_path.name} ({len(self.angles)} angles)")

        try:
            dataset_a, dataset_b, dataset_c = parse_md_file(md_path)

            system_prompt = build_system_prompt_with_scene(build_system_prompt(self.config), dataset_a)

            angle_results = {}
            total_usage = {}
            for angle_name, angle_text in self.angles.items():
                user_msg = render_user_message(self.um_template, dataset_b, dataset_c, angle_text)

                response_text, usage_data = process_text(
                    user_msg, client, self.config, self.use_cache, system_prompt=system_prompt
                )

                angle_results[angle_name] = response_text

                if usage_data:
                    total_usage = usage_data

            saved_files = save_angle_outputs(output_dir, input_name, angle_results, dataset_b, dataset_c)

            usage = UsageData(
                input_tokens=total_usage.get("input_tokens", 0),
                output_tokens=total_usage.get("output_tokens", 0),
                filename=md_path.name,
                model=self.config.get("model"),
            )

            cost = calculate_cost(
                usage_data=total_usage,
                config=self.config,
                model=str(self.config.get("model", "")),
                batch_mode=self.config.get("batch_mode", False),
            )

            return ProcessingResult(
                filename=md_path.name,
                success=True,
                output_path=saved_files[0] if saved_files else None,
                usage=usage,
                cost=cost,
            )

        except Exception as e:
            logger.error(f"Failed to process {md_path.name}: {e}")
            return ProcessingResult(filename=md_path.name, success=False, error=str(e))

    def generate_processing_reports(
        self, output_dir: Path, stats: Dict[str, Any], metadata: Dict[str, Any], duration: float
    ) -> None:
        """Generate processing reports.

        Args:
            output_dir: Output directory
            stats: Processing statistics
            metadata: Processing metadata
            duration: Processing duration in seconds
        """
        from .reporting import generate_summary

        generate_summary(
            output_dir=output_dir,
            stats=stats,
            config=self.config,
            duration=duration,
            total_cost=stats.get("total_cost", 0.0),
        )


def process_all_md_files(
    md_files: List[Path],
    config: Dict[str, Any],
    output_dir: Path,
    input_dir: Path,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Process all MD files using orchestrator.

    Args:
        md_files: List of MD file paths
        config: Configuration dictionary
        output_dir: Output directory
        input_dir: Input directory
        dry_run: If True, skip API calls

    Returns:
        Processing statistics
    """
    orchestrator = MultiAngleOrchestrator(config, input_dir)

    client, metadata = orchestrator.setup_processing(output_dir, dry_run)

    start_time = metadata["start_time"]

    if dry_run:
        stats = {
            "processed": 0,
            "failed": 0,
            "skipped": 0,
            "total": len(md_files),
            "total_cost": 0.0,
            "results": [],
            "errors": [],
        }
    else:
        assert client is not None, "Client should not be None in non-dry-run mode"
        stats = orchestrator.process_batch(md_files, client, output_dir)

    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    metadata["end_time"] = end_time

    orchestrator.generate_processing_reports(output_dir, stats, metadata, duration)

    return stats
