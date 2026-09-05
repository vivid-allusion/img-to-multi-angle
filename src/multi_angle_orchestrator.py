"""Multi-angle orchestrator for MD-to-Multi-Angle processing."""

import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from openrouter import OpenRouter
from loguru import logger

from .base_orchestrator import BaseOrchestrator
from .md_input_parser import ParsedMdInput
from .user_message_template import load_user_message_template
from .shot_generator import GenerationContext, ShotOutputs, accumulate_usage, generate_shots
from .multi_angle_output_saver import copy_raw_md_file, save_angle_outputs
from .exceptions import FileProcessingError
from .shot_plan import ShotEntry
from .reporting import short_name


def _empty_stats(total: int) -> Dict[str, Any]:
    """Fresh per-run stats dict. Failures raise → exit 1, so there is no
    partial-success path to count."""
    return {
        "processed": 0,
        "skipped": 0,
        "total": total,
        "total_cost": 0.0,
    }


class MultiAngleOrchestrator(BaseOrchestrator):
    """Orchestrates MD file multi-angle processing workflow."""

    def __init__(self, config: Dict[str, Any], input_dir: Path):
        super().__init__(config)
        self.input_dir = input_dir
        self.user_message_path = Path("USER-FILES/01.CONFIG/user_message.md")
        self.um_template: str = ""

    def process_batch(
        self,
        parsed_files: List[Tuple[Path, ParsedMdInput]],
        client: OpenRouter,
        output_dir: Path,
    ) -> Dict[str, Any]:
        """Process all MD files sequentially, generating multi-angle outputs."""
        stats = _empty_stats(len(parsed_files))

        self.um_template = load_user_message_template(self.user_message_path)

        for md_path, parsed in parsed_files:
            cost = self._process_single_file(md_path, parsed, client, output_dir)
            if cost is None:
                stats["skipped"] += 1
                continue
            stats["processed"] += 1
            stats["total_cost"] += cost

        return stats

    def _resolve_shots_to_run(
        self, parsed: ParsedMdInput, md_path: Path, client: OpenRouter
    ) -> Tuple[List[Tuple[ShotEntry, List[str]]], Dict[str, Any]]:
        """Return the shots to generate for one file: ticked shots as-is,
        otherwise one auto-planning call."""
        plan_usage: Dict[str, Any] = {}

        if parsed.checked_shots:
            entries_by_id = {e.id: e for e in parsed.shot_entries or []}
            shots_to_run: List[Tuple[ShotEntry, List[str]]] = []
            for shot_id, ground_ids in parsed.checked_shot_bindings:
                entry = entries_by_id.get(shot_id)
                if entry is None:
                    raise FileProcessingError(
                        f"{md_path.name}: ticked shot '{shot_id}' not found in shot-plan block"
                    )
                shots_to_run.append((entry, ground_ids or []))
            logger.info(f"Processing {short_name(md_path.name)}: {len(shots_to_run)} pre-selected shots")
            return shots_to_run, plan_usage

        logger.info(f"Auto-planning shots for {short_name(md_path.name)}...")
        from .shot_planner import plan_file

        sheet, entries, plan_usage = plan_file(parsed, md_path.name, client, self.config)
        shots_to_run = [(e, e.grounds) for e in entries]
        logger.info(f"Generating {len(shots_to_run)} auto-planned shots for {short_name(md_path.name)}")
        return shots_to_run, plan_usage

    def _process_single_file(
        self,
        md_path: Path,
        parsed: ParsedMdInput,
        client: OpenRouter,
        output_dir: Path,
    ) -> Optional[float]:
        """Process one MD file across all selected or auto-planned shots.

        Returns the provider-reported cost, or None when the file is skipped
        (checkboxes present but none checked — raw MD copied through).
        """
        if parsed.all_checkbox_lines and not parsed.checked_shots:
            logger.warning(f"Skipping {md_path.name}: checkboxes present but none checked")
            copy_raw_md_file(md_path, output_dir)
            return None

        shots_to_run, plan_usage = self._resolve_shots_to_run(parsed, md_path, client)

        ctx = GenerationContext(client=client, config=self.config, um_template=self.um_template)
        outputs: ShotOutputs = generate_shots(parsed, shots_to_run, md_path.name, ctx)
        accumulate_usage(outputs.usage, plan_usage)

        save_angle_outputs(output_dir, md_path.stem, outputs, parsed.original_image)

        return outputs.usage.get("cost", 0.0)

    def generate_processing_reports(
        self, output_dir: Path, stats: Dict[str, Any], duration: float
    ) -> None:
        """Generate processing reports."""
        from .reporting import RunSummary, generate_summary

        generate_summary(
            output_dir,
            RunSummary(stats=stats, config=self.config, duration=duration),
        )


def process_all_md_files(
    md_files: List[Path],
    config: Dict[str, Any],
    output_dir: Path,
    input_dir: Path,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Process all MD files using orchestrator with preflight and atomic staging."""
    orchestrator = MultiAngleOrchestrator(config, input_dir)
    start_time = datetime.now()

    if dry_run:
        output_dir.mkdir(parents=True, exist_ok=True)
        orchestrator.setup_processing(output_dir)
        stats = _empty_stats(len(md_files))
        orchestrator.generate_processing_reports(output_dir, stats, 0.0)
        return stats

    from .preflight import run_preflight
    from .output_staging import create_staging_dir, promote_staging, fail_run

    client = orchestrator._initialize_api_client()
    report = run_preflight(config, md_files, client)
    logger.info(
        f"Preflight passed: {report.files_validated} file(s), "
        f"{report.urls_checked} image URL(s), vision verified on {report.model_id}"
    )

    staging_dir = create_staging_dir(output_dir)
    orchestrator.setup_logging(staging_dir)

    try:
        stats = orchestrator.process_batch(report.parsed_files, client, staging_dir)
    except Exception as e:
        fail_run(staging_dir, output_dir, f"# FAILURE REPORT\n\n- Error: {e}\n")
        logger.error(f"Run aborted — no deliverables written: {e}")
        sys.exit(1)

    promote_staging(staging_dir, output_dir)

    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    orchestrator.generate_processing_reports(output_dir, stats, duration)
    return stats
