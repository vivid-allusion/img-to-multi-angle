"""
CLI handler for TXT processor.
Separates command handling logic from main entry point.
"""

from pathlib import Path
from typing import Dict, Any, List
from loguru import logger

from .config import get_output_directory
from .profile_manager import list_available_profiles
from .txt_processing_orchestrator import process_all_txts


class CLIHandler:
    """Handles CLI commands and orchestrates processing."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize CLI handler.
        
        Args:
            config: Loaded configuration dictionary
        """
        self.config = config
        # NO DEFAULTS - batch_mode must be in config
        self.batch_mode = config["batch_mode"]
        
    def handle_profile_listing(self) -> None:
        """Handle --list-profiles command."""
        logger.info("\nAvailable profiles:")
        logger.info("="*70)
        profiles = list_available_profiles()
        if profiles:
            for profile in profiles:
                logger.info(profile)
        else:
            logger.info("  No profiles found in USER-FILES/03.PROFILES/")
        logger.info("="*70)
        logger.info("\nUsage: python -m src.main --profile <profile_name>")
        logger.info("Example: python -m src.main --profile profile_template.yaml")
        
    def handle_batch_operations(self, args) -> bool:
        """
        Handle batch-related operations.
        
        Args:
            args: Parsed command line arguments
            
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
        logger.info("📋 Recent batches:")
        batches = monitor.list_batches(limit=10)
        for batch in batches:
            status = batch['processing_status']
            created = batch['created_at']
            count = batch.get('request_count', 'unknown')
            logger.info(f"  {batch['id']}: {status} (created: {created}, requests: {count})")
            
    def _handle_batch_id(self, args, client, monitor) -> None:
        """Handle operations for a specific batch ID."""
        status = monitor.check_batch_status(args.batch_id)
        
        logger.info(f"Batch {args.batch_id}:")
        logger.info(f"  Status: {status['processing_status']}")
        logger.info(f"  Requests: {status.get('request_count', 'unknown')}")
        logger.info(f"  Completed: {status.get('completed_count', 0)}")
        logger.info(f"  Failed: {status.get('failed_count', 0)}")
        
        if status['is_complete']:
            self._fetch_batch_results(args.batch_id, client)
        elif args.wait:
            self._wait_for_batch(args.batch_id, client, monitor)
            
    def _fetch_batch_results(self, batch_id: str, client) -> None:
        """Fetch and save batch results."""
        from .batch_result_parser import BatchResultParser
        
        parser = BatchResultParser(client, self.config)
        logger.info("📥 Fetching batch results...")
        results = parser.parse_results(batch_id)
        saved_files = parser.save_results(results)
        logger.success(f"✅ Results saved to: {saved_files.get('summary', 'output directory')}")
        
    def _wait_for_batch(self, batch_id: str, client, monitor) -> None:
        """Wait for batch completion and fetch results."""
        logger.info("⏳ Waiting for batch to complete...")
        final_status = monitor.wait_for_completion(batch_id)
        
        if final_status['is_complete']:
            self._fetch_batch_results(batch_id, client)
            
    def handle_cost_estimation(self, txt_files: List[Path], output_dir: Path) -> None:
        """
        Handle --cost-only mode for cost estimation.

        Args:
            txt_files: List of TXT files to estimate
            output_dir: Output directory for reports
        """
        logger.info("💰 Running in COST-ONLY mode - estimating costs without API calls")
        from .dry_run_estimator import DryRunEstimator
        from .auth import get_api_key

        api_key = get_api_key()
        estimator = DryRunEstimator(self.config, api_key)
        results = estimator.estimate_all_txts(txt_files)
        estimator.generate_cost_report(results, output_dir)

        logger.info("")
        logger.info("="*50)
        logger.info("💰 Cost estimation complete!")
        logger.info(f"Estimated: {results['estimated_files']} files")
        logger.info(f"Total estimated cost: ${results['total_estimated_cost']:.4f}")
        logger.info(f"Report saved to: {output_dir / 'COST_ESTIMATE.md'}")
        
    def handle_batch_submission(self, txt_files: List[Path], args) -> None:
        """
        Handle batch mode submission.

        Args:
            txt_files: List of TXT files to process
            args: Command line arguments
        """
        logger.info("🚀 Running in BATCH MODE - 50% discount on API costs!")

        from .auth import get_api_key
        from .batch_processor import BatchProcessor
        from .batch_monitor import BatchMonitor
        from openrouter import OpenRouter

        api_key = get_api_key()
        client = OpenRouter(api_key=api_key)

        all_txts = self._load_txts(txt_files)
        logger.info(f"Loaded {len(all_txts)} TXT files for batch processing")

        processor = BatchProcessor(client, self.config)
        requests = processor.create_batch_requests(all_txts)

        if not requests:
            logger.error("No valid batch requests created")
            return

        processor.save_batch_requests(requests)

        try:
            batch_id = processor.submit_batch(requests)
            processor.save_batch_requests(requests, batch_id, all_txts)
            self._log_batch_submission(batch_id, len(requests))
            
            if args.wait:
                output_dir = get_output_directory(self.config)
                monitor = BatchMonitor(client, self.config)
                logger.info("⏳ Waiting for batch to complete...")
                final_status = monitor.wait_for_completion(batch_id)
                
                if final_status['is_complete']:
                    from .batch_result_parser import BatchResultParser
                    parser = BatchResultParser(client, self.config)
                    results = parser.parse_results(batch_id)
                    parser.save_results(results, output_dir)
                    logger.success(f"✅ Results saved to: {output_dir}")
                    
        except Exception as e:
            logger.error(f"Error submitting batch: {e}")
            
    def _load_txts(self, txt_files: List[Path]) -> List[Dict[str, Any]]:
        """Load all TXT files with their filenames."""
        all_txts = []

        for txt_file in txt_files:
            with open(txt_file, 'r', encoding='utf-8') as f:
                content = f.read()
                all_txts.append({
                    'filename': txt_file.name,
                    'content': content
                })

        return all_txts
        
    def _log_batch_submission(self, batch_id: str, request_count: int) -> None:
        """Log batch submission details."""
        logger.info("")
        logger.info("="*50)
        logger.info("✅ Batch submitted successfully!")
        logger.info(f"Batch ID: {batch_id}")
        logger.info(f"Requests: {request_count}")
        logger.info("")
        logger.info("To check status:")
        logger.info(f"  python -m src.main --batch-id {batch_id}")
        logger.info("")
        logger.info("To wait for completion and fetch results:")
        logger.info(f"  python -m src.main --batch-id {batch_id} --wait")
        logger.info("="*50)
        
    def handle_realtime_processing(self, txt_files: List[Path], output_dir: Path, input_dir: Path, dry_run: bool) -> None:
        """
        Handle real-time (non-batch) processing.

        Args:
            txt_files: List of TXT files to process
            output_dir: Output directory
            input_dir: Input directory (for calculating relative paths)
            dry_run: Whether to run in dry-run mode
        """
        stats = process_all_txts(txt_files, self.config, output_dir, input_dir, dry_run)

        logger.info("")
        logger.info("="*50)
        logger.info("✨ Processing complete!")
        logger.info(f"Processed: {stats['processed']} | Failed: {stats['failed']} | Skipped: {stats.get('skipped', 0)}")