#!/usr/bin/env python3
"""Reporting and logging functions for multi-angle MD processing."""

import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any
from loguru import logger


def setup_logging(output_dir: Path) -> None:
    """Set up logging configuration for processing run.
    
    Args:
        output_dir: Directory to save log files
    """
    logger.remove()
    
    logger.add(
        sys.stderr,
        format="<green>{time:HH:mm:ss}</green> | <level>{message}</level>",
        level="INFO"
    )
    
    logger.add(
        output_dir / "processing_log.txt",
        format="{time:HH:mm:ss} | {level} | {message}",
        level="INFO"
    )


def generate_summary(output_dir: Path, stats: Dict[str, Any],
                    config: Dict[str, Any], duration: float, total_cost: float = 0.0) -> None:
    """Generate summary report in output directory.
    
    Args:
        output_dir: Directory to save the summary
        stats: Processing statistics
        config: Configuration dictionary
        duration: Processing duration in seconds
        total_cost: Total API cost in USD
    """
    report = f"""# Processing Summary

**Run Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Duration**: {duration:.1f} seconds

## Results
- Files Processed: {stats['processed']}/{stats['total']}
- Successful: {stats['processed']}
- Failed: {stats['failed']}
- Skipped: {stats['skipped']}

## Cost Summary
- **Total Cost**: ${total_cost:.4f} USD
- **Average Cost per File**: ${(total_cost / stats['processed'] if stats['processed'] > 0 else 0):.4f} USD
- **See COST.md for detailed breakdown**

## Configuration
- Model: {config['model']}
- Temperature: {config['temperature']}
- Max Tokens: {config['max_tokens']}
- Fields Removed: {', '.join(config.get('fields_to_remove', []))}
"""
    
    if config.get('prompt_suffix'):
        report += f"- Prompt Suffix: {config['prompt_suffix']}\n"
    
    if config.get('profile_metadata'):
        metadata = config['profile_metadata']
        report += "\n## Profile\n"
        report += f"- Name: {metadata.get('name', 'Unknown')}\n"
        report += f"- Version: {metadata.get('version', '1.0')}\n"
    
    if stats['errors']:
        report += "\n## Errors\n"
        for error in stats['errors']:
            report += f"- {error}\n"
    
    report += "\n## Statistics\n"
    report += f"- Total API Calls: {stats['processed']}\n"
    if stats['processed'] > 0:
        report += f"- Average Processing Time: {duration/stats['processed']:.1f} seconds per file\n"
    
    summary_file = output_dir / "summary_report.md"
    summary_file.write_text(report)
    logger.info(f"Summary report saved to {summary_file}")
