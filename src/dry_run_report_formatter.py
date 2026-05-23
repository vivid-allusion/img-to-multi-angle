#!/usr/bin/env python3
"""Formatter for dry run cost estimation reports."""

from typing import Dict, Any
from pathlib import Path
from datetime import datetime
from loguru import logger


class DryRunReportFormatter:
    """Formats and generates cost estimation reports."""

    @staticmethod
    def generate_cost_report(results: Dict[str, Any], config: Dict[str, Any], output_dir: Path) -> Path:
        """
        Generate a markdown cost estimation report.

        Args:
            results: Estimation results
            config: Configuration dictionary
            output_dir: Directory to save report

        Returns:
            Path to the generated report
        """
        report_path = output_dir / "COST_ESTIMATE.md"

        with open(report_path, 'w') as f:
            DryRunReportFormatter._write_header(f, config)
            DryRunReportFormatter._write_summary(f, results)
            DryRunReportFormatter._write_configuration(f, config)
            DryRunReportFormatter._write_file_estimates(f, results)
            DryRunReportFormatter._write_notes(f)

        logger.info(f"💰 Cost estimation report saved to {report_path}")
        return report_path

    @staticmethod
    def _write_header(f, config: Dict[str, Any]):
        """Write report header."""
        batch_mode = config['batch_mode']
        pricing_mode = "**BATCH PRICING (50% discount)**" if batch_mode else "Real-time pricing"

        f.write("# 💰 Cost Estimation Report (Dry Run)\n\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("Mode: **DRY RUN** - No API calls made\n")
        f.write(f"Pricing: {pricing_mode}\n\n")

    @staticmethod
    def _write_summary(f, results: Dict[str, Any]):
        """Write summary section."""
        f.write("## Summary\n\n")
        f.write(f"- Total Text Files: {len(results.get('file_estimates', []))}\n")
        f.write(f"- Successfully Estimated: {results['estimated_files']}\n")
        f.write(f"- **Estimated Total Cost: ${results['total_estimated_cost']:.4f}**\n\n")

    @staticmethod
    def _write_configuration(f, config: Dict[str, Any]):
        """Write configuration section."""
        f.write("## Configuration\n\n")
        f.write(f"- Model: {config['model']}\n")
        f.write(f"- Temperature: {config['temperature']}\n")
        f.write(f"- Max Tokens: {config['max_tokens']}\n")
        cache_config = config.get('cache_config') if 'cache_config' in config else None
        f.write(f"- Cache Enabled: {cache_config.get('enabled') if cache_config else False}\n")
        f.write(f"- Batch Mode: {config['batch_mode']}\n")
        f.write(f"- Avg Output Tokens (estimated): {config['avg_output_tokens']}\n")
        f.write("\n")

    @staticmethod
    def _write_file_estimates(f, results: Dict[str, Any]):
        """Write per-file estimates table."""
        f.write("## Per-File Estimates\n\n")
        f.write("| File | Input Tokens | Est. Output | Est. Cost |\n")
        f.write("|------|-------------|-------------|----------|\n")

        for estimate in results.get('file_estimates', []):
            f.write(f"| {estimate['filename']} | "
                   f"{estimate['input_tokens']:,} | "
                   f"{estimate['output_tokens']:,} | "
                   f"${estimate['estimated_cost']:.4f} |\n")

    @staticmethod
    def _write_notes(f):
        """Write notes section."""
        f.write("\n## Notes\n\n")
        f.write("- This is an ESTIMATE based on token counting API\n")
        f.write("- Output tokens are estimated based on historical averages\n")
        f.write("- Actual costs may vary depending on response length\n")
        f.write("- Cache savings are included if caching is enabled\n")