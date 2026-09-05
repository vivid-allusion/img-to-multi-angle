#!/usr/bin/env python3
"""Reporting and logging functions for multi-angle MD processing."""

import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Any
from loguru import logger


def setup_cli_logging() -> None:
    """Set up clean console logging format."""
    logger.remove()
    logger.add(
        sys.stderr,
        format="<green>{time:HH:mm:ss}</green> | <level>{message}</level>",
        level="INFO",
    )


def setup_logging(output_dir: Path) -> None:
    """Set up logging configuration for processing run."""
    setup_cli_logging()
    logger.add(
        output_dir / "processing_log.txt",
        format="{time:HH:mm:ss} | {level} | {message}",
        level="INFO",
    )


def short_name(name: Any, max_len: int = 40) -> str:
    """Shorten long filenames for clean display."""
    s = Path(name).name if isinstance(name, Path) else str(name)
    if len(s) <= max_len:
        return s
    head = max_len // 2 - 2
    tail = max_len - head - 3
    return f"{s[:head]}...{s[-tail:]}"


def short_url(url: str, max_len: int = 50) -> str:
    """Shorten long URLs for clean display."""
    if len(url) <= max_len:
        return url
    return f"{url[:25]}...{url[-20:]}"


@dataclass
class RunSummary:
    """Everything a summary report needs in one bundle."""

    stats: Dict[str, Any]
    config: Dict[str, Any]
    duration: float


def generate_summary(output_dir: Path, summary: RunSummary) -> None:
    """Generate summary report in output directory.

    Args:
        output_dir: Directory to save the summary
        summary: RunSummary (stats, config, metadata, duration)
    """
    stats = summary.stats
    config = summary.config
    duration = summary.duration

    report = f"""# Processing Summary

**Run Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Duration**: {duration:.1f} seconds

## Results
- Files Processed: {stats['processed']}/{stats['total']}
- Skipped: {stats['skipped']}

## Cost Summary
- **Total Cost**: ${stats['total_cost']:.4f} USD
- **Average Cost per File**: ${(stats['total_cost'] / stats['processed'] if stats['processed'] > 0 else 0):.4f} USD

## Configuration
- Model: {config['model']}
- Temperature: {config['temperature']}
- Max Tokens: {config['max_tokens']}
"""

    if config.get('profile_metadata'):
        metadata = config['profile_metadata']
        report += "\n## Profile\n"
        report += f"- Name: {metadata.get('profile_name', 'Unknown')}\n"
        report += f"- Version: {metadata.get('version', '1.0')}\n"

    if stats['processed'] > 0:
        report += "\n## Statistics\n"
        report += f"- Average Processing Time: {duration/stats['processed']:.1f} seconds per file\n"

    summary_file = output_dir / "summary_report.md"
    summary_file.write_text(report)
    logger.info(f"Summary report saved to {summary_file}")
