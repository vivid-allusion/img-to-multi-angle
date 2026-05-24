#!/usr/bin/env python3
"""Batch status formatting and display utilities."""

import time
from typing import Dict, Any
from loguru import logger


class BatchStatusFormatter:
    """Formats batch status information for display."""

    @staticmethod
    def log_status_change(status: Dict[str, Any], verbose: bool):
        """Log batch status changes."""
        if not verbose:
            return

        processing_status = status["processing_status"]

        if processing_status == "in_progress":
            completed = status.get("completed_count", 0)
            total = status.get("request_count", 0)
            if total > 0:
                progress = (completed / total) * 100
                logger.info(f"Processing: {completed}/{total} requests ({progress:.1f}%)")
            else:
                logger.info("Batch is processing...")

        elif processing_status == "canceling":
            logger.warning("Batch is being canceled...")

        elif processing_status == "canceled":
            logger.warning("Batch was canceled")

        elif processing_status == "failed":
            logger.error("Batch failed")

        else:
            logger.info(f"Status: {processing_status}")

    @staticmethod
    def log_completion_stats(status: Dict[str, Any], start_time: float):
        """Log batch completion statistics."""
        elapsed = time.time() - start_time
        hours = elapsed / 3600

        logger.info(f"Processing time: {hours:.2f} hours")

        if status.get("request_count"):
            total = status["request_count"]
            succeeded = status.get("completed_count", 0)
            failed = status.get("failed_count", 0)

            logger.info(f"Results: {succeeded}/{total} succeeded")

            if failed > 0:
                logger.warning(f"{failed} requests failed")

            success_rate = (succeeded / total) * 100 if total > 0 else 0
            logger.info(f"Success rate: {success_rate:.1f}%")

    @staticmethod
    def format_progress_message(check_interval: float, remaining_time: float) -> str:
        """Format progress monitoring message."""
        return (f"Next check in {check_interval/60:.1f} minutes. "
                f"Timeout in {remaining_time/3600:.1f} hours.")
