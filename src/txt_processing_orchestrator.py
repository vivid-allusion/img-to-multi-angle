#!/usr/bin/env python3
"""TXT processing orchestrator for real-time and batch workflows."""

from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List
from openrouter import OpenRouter
from loguru import logger

from .base_orchestrator import BaseOrchestrator
from .txt_reader import discover_txt_files, read_txt_file
from .txt_writer import create_output_directory, save_txt_output
from .api_client import process_text
from .data_models import ProcessingResult, UsageData
from .cost_calculator import calculate_cost


class TxtProcessingOrchestrator(BaseOrchestrator):
    """Orchestrates TXT file processing workflow."""

    def __init__(self, config: Dict[str, Any], input_dir: Path):
        """
        Initialize orchestrator with config and input directory.

        Args:
            config: Configuration dictionary
            input_dir: Input directory path (for calculating relative paths)
        """
        super().__init__(config)
        self.input_dir = input_dir

    def process_batch(self, files: List[Path], client: OpenRouter, output_dir: Path) -> Dict[str, Any]:
        """
        Process a batch of TXT files sequentially.

        Args:
            files: List of TXT file paths
            client: OpenRouter API client
            output_dir: Output directory

        Returns:
            Processing statistics
        """
        timestamp = datetime.now()
        stats = {
            "processed": 0,
            "failed": 0,
            "skipped": 0,
            "total": len(files),
            "total_cost": 0.0,
            "results": [],
            "errors": []
        }

        cache_config = self.config.get("cache_config", {})
        use_cache = cache_config.get("enabled", False) and len(files) >= 2

        for file_path in files:
            result = self._process_single_file(file_path, client, output_dir, timestamp, use_cache)
            
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
        file_path: Path,
        client: OpenRouter,
        output_dir: Path,
        timestamp: datetime,
        use_cache: bool = False
    ) -> ProcessingResult:
        """
        Process a single TXT file.

        Args:
            file_path: Path to TXT file
            client: OpenRouter API client
            output_dir: Output directory
            timestamp: Timestamp for output filename

        Returns:
            ProcessingResult with success/failure info
        """
        filename = file_path.stem
        relative_path = file_path.relative_to(self.input_dir)
        logger.info(f"Processing: {relative_path}")

        try:
            content = read_txt_file(file_path)
            response_text, usage_data = process_text(content, client, self.config, use_cache)

            output_path = save_txt_output(
                response_text, 
                output_dir, 
                filename, 
                timestamp,
                relative_path
            )

            usage = UsageData(
                input_tokens=usage_data.get("input_tokens", 0),
                output_tokens=usage_data.get("output_tokens", 0),
                filename=file_path.name,
                model=self.config.get("model")
            )

            model_name = str(self.config.get("model", ""))
            cost = calculate_cost(
                usage_data=usage_data,
                config=self.config,
                model=model_name,
                batch_mode=self.config.get("batch_mode", False)
            )

            return ProcessingResult(
                filename=file_path.name,
                success=True,
                output_path=output_path,
                usage=usage,
                cost=cost
            )

        except Exception as e:
            logger.error(f"Failed to process {file_path.name}: {e}")
            return ProcessingResult(
                filename=file_path.name,
                success=False,
                error=str(e)
            )

    def generate_processing_reports(
        self,
        output_dir: Path,
        stats: Dict[str, Any],
        metadata: Dict[str, Any],
        duration: float
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
            total_cost=stats.get("total_cost", 0.0)
        )


def process_all_txts(
    txt_files: List[Path],
    config: Dict[str, Any],
    output_dir: Path,
    input_dir: Path,
    dry_run: bool = False
) -> Dict[str, Any]:
    """
    Process all TXT files using orchestrator.

    Args:
        txt_files: List of TXT file paths
        config: Configuration dictionary
        output_dir: Output directory
        input_dir: Input directory (for calculating relative paths)
        dry_run: If True, skip API calls

    Returns:
        Processing statistics
    """
    orchestrator = TxtProcessingOrchestrator(config, input_dir)
    
    client, metadata = orchestrator.setup_processing(output_dir, dry_run)
    
    start_time = metadata["start_time"]

    if dry_run:
        stats = {
            "processed": 0,
            "failed": 0,
            "skipped": 0,
            "total": len(txt_files),
            "total_cost": 0.0,
            "results": [],
            "errors": []
        }
    else:
        assert client is not None, "Client should not be None in non-dry-run mode"
        stats = orchestrator.process_batch(txt_files, client, output_dir)

    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    metadata["end_time"] = end_time

    orchestrator.generate_processing_reports(output_dir, stats, metadata, duration)

    return stats
