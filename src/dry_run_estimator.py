#!/usr/bin/env python3
"""Dry run cost estimation without making actual API calls."""

from typing import Dict, Any, List
from pathlib import Path
from openrouter import OpenRouter
from loguru import logger

from .cost_calculator import UsageStats
from .dry_run_report_formatter import DryRunReportFormatter


class DryRunEstimator:
    """Estimates costs without making actual API calls."""
    
    def __init__(self, config: Dict[str, Any], api_key: str = "sk-dummy-for-counting"):
        """
        Initialize the dry run estimator.
        
        Args:
            config: Configuration dictionary
            api_key: API key (can be dummy for token counting only)
        """
        self.config = config
        self.client = OpenRouter(api_key=api_key)
        self.usage_stats = UsageStats()
        
    def estimate_txt_cost(self, txt_content: str) -> Dict[str, Any]:
        """
        Estimate cost for a single TXT file.

        Args:
            txt_content: TXT content to estimate

        Returns:
            Dictionary with token counts and estimated cost
        """
        input_tokens = self._count_txt_tokens(txt_content)
        
        if "avg_output_tokens" not in self.config:
            raise ValueError("Missing 'avg_output_tokens' in configuration - must be defined in USER-FILES/01.CONFIG/")
        avg_output_tokens = self.config["avg_output_tokens"]
        
        usage_data = {
            'input_tokens': input_tokens,
            'output_tokens': avg_output_tokens
        }

        return usage_data

    def _count_txt_tokens(self, txt_content: str) -> int:
        """
        Count tokens for TXT content using character estimation.

        Args:
            txt_content: TXT to count tokens for

        Returns:
            Number of tokens (estimated)
        """
        try:
            if "system_prompt" not in self.config:
                raise ValueError("Missing 'system_prompt' in configuration")
            system = self.config["system_prompt"]
            
            total_chars = len(system) + len(txt_content)
            estimated_tokens = total_chars // 4
            return estimated_tokens
        except Exception as e:
            logger.warning(f"Failed to count tokens: {e}")
            return len(txt_content) // 4

    def estimate_all_txts(self, txt_files: List[Path]) -> Dict[str, Any]:
        """
        Estimate costs for all TXT files.

        Args:
            txt_files: List of TXT file paths

        Returns:
            Dictionary with estimation results
        """
        results = {
            'estimated_files': 0,
            'total_estimated_cost': 0.0,
            'file_estimates': []
        }

        for txt_file in txt_files:
            try:
                content = txt_file.read_text(encoding='utf-8')
                usage_data = self.estimate_txt_cost(content)

                from .cost_calculator import calculate_cost
                cost = calculate_cost(
                    usage_data,
                    self.config,
                    self.config['model'],
                    self.config['batch_mode']
                )

                results['file_estimates'].append({
                    'filename': txt_file.name,
                    'input_tokens': usage_data['input_tokens'],
                    'output_tokens': usage_data['output_tokens'],
                    'estimated_cost': cost
                })

                results['estimated_files'] += 1
                results['total_estimated_cost'] += cost

            except Exception as e:
                logger.error(f"Error estimating {txt_file}: {e}")

        return results
    
    
    def generate_cost_report(self, results: Dict[str, Any], output_dir: Path) -> Path:
        """
        Generate a markdown cost estimation report.

        Args:
            results: Estimation results
            output_dir: Directory to save report

        Returns:
            Path to the generated report
        """
        return DryRunReportFormatter.generate_cost_report(results, self.config, output_dir)
