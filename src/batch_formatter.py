#!/usr/bin/env python3
"""Batch status formatting and display utilities."""

from typing import Dict, Any
import time
from loguru import logger


class BatchStatusFormatter:
    """Formats batch status information for display."""

    @staticmethod
    def log_status_change(status: Dict[str, Any], verbose: bool):
        """Log batch status changes.

        Args:
            status: Batch status dictionary
            verbose: Whether to show detailed output
        """
        if not verbose:
            return

        processing_status = status["processing_status"]

        if processing_status == "in_progress":
            completed = status.get("completed_count", 0)
            total = status.get("request_count", 0)
            if total > 0:
                progress = (completed / total) * 100
                logger.info(f"📊 Processing: {completed}/{total} requests ({progress:.1f}%)")
            else:
                logger.info("📊 Batch is processing...")

        elif processing_status == "canceling":
            logger.warning("🚫 Batch is being canceled...")

        elif processing_status == "canceled":
            logger.warning("❌ Batch was canceled")

        elif processing_status == "failed":
            logger.error("❌ Batch failed")

        else:
            logger.info(f"Status: {processing_status}")

    @staticmethod
    def log_completion_stats(status: Dict[str, Any], start_time: float):
        """Log batch completion statistics.

        Args:
            status: Final batch status
            start_time: When monitoring started
        """
        elapsed = time.time() - start_time
        hours = elapsed / 3600

        logger.info(f"Processing time: {hours:.2f} hours")

        if status.get("request_count"):
            total = status["request_count"]
            succeeded = status.get("completed_count", 0)
            failed = status.get("failed_count", 0)

            logger.info(f"Results: {succeeded}/{total} succeeded")

            if failed > 0:
                logger.warning(f"⚠️ {failed} requests failed")

            success_rate = (succeeded / total) * 100 if total > 0 else 0
            logger.info(f"Success rate: {success_rate:.1f}%")

    @staticmethod
    def format_batch_info(batch_info: Dict[str, Any]) -> str:
        """Format batch information for display.

        Args:
            batch_info: Batch information dictionary

        Returns:
            Formatted string for display
        """
        status = batch_info.get("processing_status", "unknown")
        created = batch_info.get("created_at", "unknown")
        request_count = batch_info.get("request_count", 0)

        return (f"Batch ID: {batch_info.get('id', 'unknown')}\n"
                f"Status: {status}\n"
                f"Created: {created}\n"
                f"Requests: {request_count}")

    @staticmethod
    def format_progress_message(check_interval: float, remaining_time: float) -> str:
        """Format progress monitoring message.

        Args:
            check_interval: Seconds between checks
            remaining_time: Seconds until timeout

        Returns:
            Formatted progress message
        """
        return (f"Next check in {check_interval/60:.1f} minutes. "
                f"Timeout in {remaining_time/3600:.1f} hours.")