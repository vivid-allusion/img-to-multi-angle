"""CLI command handlers for multi-angle MD processor."""

from pathlib import Path
from typing import Dict, Any, List
from loguru import logger

from .profile_manager import list_available_profiles
from .multi_angle_orchestrator import process_all_md_files


class ProfileCommand:
    """Handles profile listing command."""

    @staticmethod
    def execute() -> None:
        """List available profiles."""
        logger.info("\nAvailable profiles:")
        logger.info("=" * 70)
        profiles = list_available_profiles()
        if profiles:
            for profile in profiles:
                logger.info(profile)
        else:
            logger.info("  No profiles found in USER-FILES/03.PROFILES/")
        logger.info("=" * 70)
        logger.info("\nUsage: python -m src.main --profile <profile_name>")


class CostCommand:
    """Handles cost estimation command."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config

    def execute(self, md_files: List[Path], output_dir: Path) -> None:
        """Estimate costs without making API calls."""
        logger.info("Running in COST-ONLY mode - estimating costs without API calls")
        from .dry_run_estimator import DryRunEstimator
        from .auth import get_api_key

        api_key = get_api_key()
        estimator = DryRunEstimator(self.config, api_key)
        results = estimator.estimate_all_md_files(md_files)
        estimator.generate_cost_report(results, output_dir)

        logger.info("")
        logger.info("=" * 50)
        logger.info("Cost estimation complete!")
        logger.info(f"Estimated: {results['estimated_files']} files")
        logger.info(f"Total estimated cost: ${results['total_estimated_cost']:.4f}")
        logger.info(f"Report saved to: {output_dir / 'COST_ESTIMATE.md'}")


class ProcessCommand:
    """Handles real-time file processing."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config

    def handle_realtime_processing(
        self, md_files: List[Path], output_dir: Path, input_dir: Path, dry_run: bool
    ) -> None:
        """Handle real-time (non-batch) processing."""
        stats = process_all_md_files(md_files, self.config, output_dir, input_dir, dry_run)

        logger.info("")
        logger.info("=" * 50)
        logger.info("Processing complete!")
        logger.info(f"Processed: {stats['processed']} | Skipped: {stats.get('skipped', 0)} | Total Cost: ${stats.get('total_cost', 0.0):.4f}")


class CLIHandler:
    """Routes CLI commands to focused command handlers."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config

    def handle_profile_listing(self) -> None:
        ProfileCommand.execute()

    def handle_cost_estimation(self, md_files: List[Path], output_dir: Path) -> None:
        CostCommand(self.config).execute(md_files, output_dir)

    def handle_realtime_processing(
        self, md_files: List[Path], output_dir: Path, input_dir: Path, dry_run: bool
    ) -> None:
        ProcessCommand(self.config).handle_realtime_processing(md_files, output_dir, input_dir, dry_run)
