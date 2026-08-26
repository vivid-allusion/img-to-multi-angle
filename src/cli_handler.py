"""CLI command handlers for multi-angle MD processor."""

from pathlib import Path
from typing import Dict, Any, List
from loguru import logger

from .config import get_output_directory
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


class BatchCommand:
    """Handles batch-related operations."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config

    def execute(self, args) -> bool:
        """Handle batch-related operations.

        Returns:
            True if operation was handled, False otherwise
        """
        if not (args.list_batches or args.batch_id):
            return False

        from .auth import get_api_key
        from .batch_monitor import BatchMonitor
        from openrouter import OpenRouter

        api_key = get_api_key()
        client = OpenRouter(api_key=api_key)
        monitor = BatchMonitor(client, self.config)

        if args.list_batches:
            self._list_batches(monitor)
            return True

        if args.batch_id:
            self._handle_batch_id(args, client, monitor)
            return True

        return False

    def _list_batches(self, monitor) -> None:
        """List recent batches."""
        logger.info("Recent batches:")
        batches = monitor.list_batches(limit=10)
        for batch in batches:
            status = batch["processing_status"]
            created = batch["created_at"]
            count = batch.get("request_count", "unknown")
            logger.info(f"  {batch['id']}: {status} (created: {created}, requests: {count})")

    def _handle_batch_id(self, args, client, monitor) -> None:
        """Handle operations for a specific batch ID."""
        status = monitor.check_batch_status(args.batch_id)

        logger.info(f"Batch {args.batch_id}:")
        logger.info(f"  Status: {status['processing_status']}")
        logger.info(f"  Requests: {status.get('request_count', 'unknown')}")
        logger.info(f"  Completed: {status.get('completed_count', 0)}")
        logger.info(f"  Failed: {status.get('failed_count', 0)}")

        if status["is_complete"]:
            self._fetch_batch_results(args.batch_id, client)
        elif args.wait:
            self._wait_for_batch(args.batch_id, client, monitor)

    def _fetch_batch_results(self, batch_id: str, client) -> None:
        """Fetch and save batch results."""
        from .batch_result_parser import BatchResultParser

        parser = BatchResultParser(client, self.config)
        logger.info("Fetching batch results...")
        results = parser.parse_results(batch_id)
        saved_files = parser.save_results(results)
        logger.success(f"Results saved to: {saved_files.get('summary', 'output directory')}")

    def _wait_for_batch(self, batch_id: str, client, monitor) -> None:
        """Wait for batch completion and fetch results."""
        logger.info("Waiting for batch to complete...")
        final_status = monitor.wait_for_completion(batch_id)

        if final_status["is_complete"]:
            self._fetch_batch_results(batch_id, client)


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
    """Handles file processing commands (batch submission and real-time)."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.batch_mode = config.get("batch_mode", False)

    def handle_batch_submission(self, md_files: List[Path], args) -> None:
        """Handle batch mode submission."""
        logger.info("Running in BATCH MODE - 50% discount on API costs!")

        from .auth import get_api_key
        from .batch_processor import BatchProcessor
        from .batch_monitor import BatchMonitor
        from .md_input_parser import parse_md_file
        from .angle_loader import load_angle_templates
        from .user_message_template import load_user_message_template
        from openrouter import OpenRouter

        api_key = get_api_key()
        client = OpenRouter(api_key=api_key)

        angle_dir = Path("USER-FILES/01.CONFIG/angle-templates")
        um_path = Path("USER-FILES/01.CONFIG/user_message.md")
        angles = load_angle_templates(angle_dir)
        um_template = load_user_message_template(um_path)

        md_items = []
        for md_file in md_files:
            parsed = parse_md_file(md_file)
            md_items.append({
                "filename": md_file.stem,
                "dataset_a": parsed.scene,
                "dataset_b": parsed.original_image,
                "dataset_c": parsed.ref_images,
                "checked_angles": parsed.checked_angles,
                "checkbox_lines": parsed.all_checkbox_lines,
                "parsed": parsed,
            })

        from .checkbox_validator import validate_checkboxes
        available_angles = set(angles.keys())
        for item in md_items:
            roster = {s.id for s in item["parsed"].shot_sheet.subjects} if item["parsed"].shot_sheet else None
            validate_checkboxes(item["checkbox_lines"], available_angles, item["filename"], roster=roster)

        logger.info(f"Loaded {len(md_items)} MD files, {len(angles)} angles")

        processor = BatchProcessor(client, self.config)
        requests = processor.create_batch_requests(md_items, angles, um_template)

        if not requests:
            logger.error("No valid batch requests created")
            return

        processor.save_batch_requests(requests)

        try:
            batch_id = processor.submit_batch(requests)
            processor.save_batch_requests(requests, batch_id, md_items)
            self._log_batch_submission(batch_id, len(requests))

            if args.wait:
                self._wait_and_fetch(batch_id, client)

        except Exception as e:
            logger.error(f"Error submitting batch: {e}")

    def handle_realtime_processing(
        self, md_files: List[Path], output_dir: Path, input_dir: Path, dry_run: bool
    ) -> None:
        """Handle real-time (non-batch) processing."""
        stats = process_all_md_files(md_files, self.config, output_dir, input_dir, dry_run)

        logger.info("")
        logger.info("=" * 50)
        logger.info("Processing complete!")
        logger.info(f"Processed: {stats['processed']} | Failed: {stats['failed']} | Skipped: {stats.get('skipped', 0)}")

    def _log_batch_submission(self, batch_id: str, request_count: int) -> None:
        """Log batch submission details."""
        logger.info("")
        logger.info("=" * 50)
        logger.info("Batch submitted successfully!")
        logger.info(f"Batch ID: {batch_id}")
        logger.info(f"Requests: {request_count}")
        logger.info("")
        logger.info("To check status:")
        logger.info(f"  python -m src.main --batch-id {batch_id}")
        logger.info("")
        logger.info("To wait for completion and fetch results:")
        logger.info(f"  python -m src.main --batch-id {batch_id} --wait")
        logger.info("=" * 50)

    def _wait_and_fetch(self, batch_id: str, client) -> None:
        """Wait for batch completion and fetch results."""
        from .batch_monitor import BatchMonitor
        from .batch_result_parser import BatchResultParser

        output_dir = get_output_directory(self.config)
        monitor = BatchMonitor(client, self.config)
        logger.info("Waiting for batch to complete...")
        final_status = monitor.wait_for_completion(batch_id)

        if final_status["is_complete"]:
            parser = BatchResultParser(client, self.config)
            results = parser.parse_results(batch_id)
            parser.save_results(results, output_dir)
            logger.success(f"Results saved to: {output_dir}")


class CLIHandler:
    """Routes CLI commands to focused command handlers."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.batch_mode = config.get("batch_mode", False)

    def handle_profile_listing(self) -> None:
        ProfileCommand.execute()

    def handle_batch_operations(self, args) -> bool:
        return BatchCommand(self.config).execute(args)

    def handle_cost_estimation(self, md_files: List[Path], output_dir: Path) -> None:
        CostCommand(self.config).execute(md_files, output_dir)

    def handle_batch_submission(self, md_files: List[Path], args) -> None:
        ProcessCommand(self.config).handle_batch_submission(md_files, args)

    def handle_realtime_processing(
        self, md_files: List[Path], output_dir: Path, input_dir: Path, dry_run: bool
    ) -> None:
        ProcessCommand(self.config).handle_realtime_processing(md_files, output_dir, input_dir, dry_run)
