"""Multi-angle orchestrator for MD-to-Multi-Angle processing."""

import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List
from openrouter import OpenRouter
from loguru import logger

from .base_orchestrator import BaseOrchestrator
from .md_input_parser import parse_md_file
from .angle_loader import load_angle_templates
from .user_message_template import load_user_message_template, render_user_message
from .payload_builder import build_user_content
from .api_client import process_text, build_system_prompt
from .subject_binding import substitute_subject
from .multi_angle_output_saver import save_angle_outputs
from .data_models import ProcessingResult, UsageData
from .exceptions import FileProcessingError


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
            "skipped": 0,
            "total": len(files),
            "total_cost": 0.0,
            "results": [],
            "errors": [],
        }

        self.angles = load_angle_templates(self.angle_template_dir)
        self.um_template = load_user_message_template(self.user_message_path)

        for md_path in files:
            result = self._process_single_file(md_path, client, output_dir)

            stats["processed"] += 1
            stats["total_cost"] += result.cost
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
            output_dir: Output directory (staging during real runs)

        Raises:
            FileProcessingError: If any angle call fails — the run must abort
        """
        input_name = md_path.stem

        parsed = parse_md_file(md_path)

        if not parsed.checked_angles:
            logger.warning(f"Skipping {md_path.name}: no angles selected")
            from .multi_angle_output_saver import copy_raw_md_file
            copy_raw_md_file(md_path, output_dir)
            return ProcessingResult(
                filename=md_path.name,
                success=True,
                output_path=output_dir / md_path.name,
                usage=UsageData(input_tokens=0, output_tokens=0, filename=md_path.name, model=self.config.get("model")),
                cost=0.0,
            )

        logger.info(f"Processing: {md_path.name} ({len(parsed.checked_angle_bindings)} of {len(self.angles)} angles)")

        cache_config = self.config.get("cache_config", {})
        use_cache = cache_config.get("enabled", False) and len(parsed.checked_angles) >= 2
        cache_ttl = cache_config.get("cache_ttl") if use_cache else None
        if use_cache:
            logger.info(f"Prompt caching active for {md_path.name} (TTL: {cache_ttl})")

        system_prompt = build_system_prompt(self.config)

        angle_results = {}
        total_usage: Dict[str, Any] = {}
        for angle_name, subject_ids in parsed.checked_angle_bindings:
            angle_text = substitute_subject(self.angles[angle_name], subject_ids, parsed.shot_sheet)
            user_msg = render_user_message(self.um_template, angle_text)

            try:
                user_content = build_user_content(
                    scene=parsed.scene,
                    original_image=parsed.original_image,
                    ref_images=parsed.ref_images,
                    angle_text=user_msg,
                    shot_sheet=parsed.shot_sheet_text,
                    cache_breakpoint=use_cache,
                    cache_ttl=cache_ttl,
                )
                response_text, usage_data = process_text(
                    user_content, client, self.config, system_prompt=system_prompt
                )
            except Exception as e:
                raise FileProcessingError(f"{md_path.name} angle '{angle_name}': {e}") from e

            result_key = (
                angle_name if not subject_ids else f"{angle_name}_{'_'.join(subject_ids)}"
            )
            angle_results[result_key] = response_text

            if usage_data:
                for key in (
                    "input_tokens",
                    "output_tokens",
                    "cache_creation_input_tokens",
                    "cache_read_input_tokens",
                    "cost",
                ):
                    total_usage[key] = total_usage.get(key, 0) + usage_data.get(key, 0)

        saved_files = save_angle_outputs(output_dir, input_name, angle_results, parsed.original_image, parsed.ref_images)

        usage = UsageData(
            input_tokens=total_usage.get("input_tokens", 0),
            output_tokens=total_usage.get("output_tokens", 0),
            cache_creation_tokens=total_usage.get("cache_creation_input_tokens", 0),
            cache_read_tokens=total_usage.get("cache_read_input_tokens", 0),
            filename=md_path.name,
            model=self.config.get("model"),
        )

        return ProcessingResult(
            filename=md_path.name,
            success=True,
            output_path=saved_files[0] if saved_files else None,
            usage=usage,
            cost=total_usage.get("cost", 0.0),
        )

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

    Real runs: preflight first, then stage, then promote atomically. On any
    failure the staging dir is renamed to _FAILED and the run exits non-zero —
    the final output directory is never created.
    """
    orchestrator = MultiAngleOrchestrator(config, input_dir)

    start_time = datetime.now()

    if dry_run:
        output_dir.mkdir(parents=True, exist_ok=True)
        _, metadata = orchestrator.setup_processing(output_dir, dry_run=True)
        stats = {
            "processed": 0,
            "failed": 0,
            "skipped": 0,
            "total": len(md_files),
            "total_cost": 0.0,
            "results": [],
            "errors": [],
        }
        orchestrator.generate_processing_reports(output_dir, stats, metadata, 0.0)
        return stats

    from .preflight import run_preflight
    from .output_staging import create_staging_dir, promote_staging, fail_run

    client = orchestrator._initialize_api_client()
    run_preflight(config, md_files, client)

    staging_dir = create_staging_dir(output_dir)
    orchestrator.setup_logging(staging_dir)

    metadata = {"start_time": start_time, "dry_run": False, "output_dir": output_dir}

    try:
        stats = orchestrator.process_batch(md_files, client, staging_dir)
    except Exception as e:
        fail_run(staging_dir, output_dir, f"# FAILURE REPORT\n\n- Error: {e}\n")
        logger.error(f"Run aborted — no deliverables written: {e}")
        sys.exit(1)

    promote_staging(staging_dir, output_dir)

    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    metadata["end_time"] = end_time

    orchestrator.generate_processing_reports(output_dir, stats, metadata, duration)

    return stats
