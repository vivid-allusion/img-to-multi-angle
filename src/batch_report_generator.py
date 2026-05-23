"""
Batch report generator for creating summary reports.
Extracted from batch_result_parser.py to maintain file size limits.
"""

from typing import Dict, Any
from datetime import datetime


class BatchReportGenerator:
    """Generates markdown reports for batch processing results."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize report generator.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        
    def create_summary_report(self, results: Dict[str, Any]) -> str:
        """
        Create a markdown summary report for batch results.
        
        Args:
            results: Parsed results dictionary with succeeded/failed lists
            
        Returns:
            Markdown report string
        """
        report = self._create_header(results)
        report += self._create_configuration_section()
        report += self._create_token_usage_section(results)
        report += self._create_cost_analysis_section(results)
        report += self._create_failure_section(results)
        report += self._create_notes_section()
        
        return report
        
    def _create_header(self, results: Dict[str, Any]) -> str:
        """Create report header with overview statistics."""
        total = results['total_count']
        success = results['success_count']
        failed = results['failure_count']
        
        success_rate = (success / total * 100) if total > 0 else 0
        failure_rate = (failed / total * 100) if total > 0 else 0
        
        return f"""# Batch Processing Summary

## Overview
- **Batch ID**: {results['batch_id']}
- **Total Requests**: {total}
- **Successful**: {success} ({success_rate:.1f}%)
- **Failed**: {failed} ({failure_rate:.1f}%)
- **Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

"""
        
    def _create_configuration_section(self) -> str:
        """Create configuration section of report."""
        return f"""## Configuration
- **Model**: {self.config['model']}
- **Temperature**: {self.config['temperature']}
- **Max Tokens**: {self.config['max_tokens']}

"""
        
    def _create_token_usage_section(self, results: Dict[str, Any]) -> str:
        """Create token usage statistics section."""
        if not results["succeeded"]:
            return "## Token Usage\n*No successful results to analyze*\n\n"
            
        # Check for _api_usage (from batch results) or usage (from real-time)
        total_input = sum(s.get("_api_usage", s.get("usage", {})).get("input_tokens", 0) for s in results["succeeded"])
        total_output = sum(s.get("_api_usage", s.get("usage", {})).get("output_tokens", 0) for s in results["succeeded"])
        count = len(results['succeeded'])
        
        avg_input = total_input / count if count > 0 else 0
        avg_output = total_output / count if count > 0 else 0
        
        return f"""## Token Usage
- **Total Input Tokens**: {total_input:,}
- **Total Output Tokens**: {total_output:,}
- **Average Input per File**: {avg_input:.0f}
- **Average Output per File**: {avg_output:.0f}

"""
        
    def _create_cost_analysis_section(self, results: Dict[str, Any]) -> str:
        """Create cost analysis section with batch pricing."""
        if not results["succeeded"]:
            return "## Cost Analysis\n*No successful results to analyze*\n\n"
            
        # Check for _api_usage (from batch results) or usage (from real-time)
        total_input = sum(s.get("_api_usage", s.get("usage", {})).get("input_tokens", 0) for s in results["succeeded"])
        total_output = sum(s.get("_api_usage", s.get("usage", {})).get("output_tokens", 0) for s in results["succeeded"])
        
        # Get batch pricing using model resolver
        from .cost_calculator import calculate_cost
        
        # NO DEFAULTS - model must be in config
        model = self.config["model"]
        
        # Calculate cost using the cost calculator for consistency
        usage_data = {
            'input_tokens': total_input,
            'output_tokens': total_output
        }
        total_cost = calculate_cost(usage_data, self.config, model, batch_mode=True)
        
        # Calculate individual cost components for display
        # Note: total_cost already includes batch discount
        cost_per_file = total_cost / results['success_count'] if results['success_count'] > 0 else 0
        realtime_cost = total_cost * 2  # Batch is 50% of real-time
        savings = realtime_cost - total_cost
        
        return f"""## Cost Analysis (Batch Pricing - 50% Discount)
- **Total Cost**: ${total_cost:.4f}
- **Cost per File**: ${cost_per_file:.4f}
- **Real-time Cost Would Be**: ${realtime_cost:.4f}
- **Savings vs Real-time**: ${savings:.4f} (50% discount applied)

"""
        
    def _create_failure_section(self, results: Dict[str, Any]) -> str:
        """Create failure details section if any failures exist."""
        if not results["failed"]:
            return ""
            
        section = """## Failed Requests

| File | Error Type | Error Message |
|-------|------------|---------------|
"""
        
        # Show first 10 failures
        for failure in results["failed"][:10]:
            filename = failure.get("filename", failure.get("custom_id", "unknown"))
            error_type = failure.get("error_type", "unknown")
            error_msg = failure.get("error_message", "No message")[:50]
            section += f"| {filename} | {error_type} | {error_msg} |\n"
            
        if len(results["failed"]) > 10:
            section += f"\n*... and {len(results['failed']) - 10} more failures. See batch_failures.json for details.*\n"
            
        section += "\n"
        return section
        
    def _create_notes_section(self) -> str:
        """Create notes section with helpful information."""
        return """## Notes
- Batch processing provides 50% discount on all API costs
- Results delivered within 24 hours (often faster)
- Failed requests can be retried in a new batch
"""