#!/usr/bin/env python3
"""Cost reporting functionality for API usage."""

import json
from pathlib import Path
from typing import Dict, Any
from datetime import datetime

from .cost_calculator import UsageStats, get_input_rate


def generate_cost_report(usage_stats: UsageStats, config: Dict[str, Any], output_dir: Path, 
                         start_time: datetime, end_time: datetime) -> Path:
    """
    Generate a detailed cost report in Markdown format.
    
    Args:
        usage_stats: Accumulated usage statistics
        config: Configuration with pricing info
        output_dir: Directory to save the report
        start_time: Processing start time
        end_time: Processing end time
        
    Returns:
        Path to the generated report file
    """
    model = config['model']
    pricing = config.get('pricing', {})
    
    total_cost = sum(file['cost'] for file in usage_stats.file_costs)

    sorted_files = sorted(usage_stats.file_costs, key=lambda x: x['cost'], reverse=True)
    top_5_files = sorted_files[:5] if len(sorted_files) >= 5 else sorted_files

    num_files = len(usage_stats.file_costs)
    avg_cost_per_file = total_cost / num_files if num_files > 0 else 0
    avg_input_tokens = usage_stats.total_input_tokens / num_files if num_files > 0 else 0
    avg_output_tokens = usage_stats.output_tokens / num_files if num_files > 0 else 0
    
    processing_time = (end_time - start_time).total_seconds()
    
    report = _generate_report_content(
        model, total_cost, usage_stats, pricing, 
        processing_time, num_files, avg_cost_per_file,
        avg_input_tokens, avg_output_tokens, top_5_files
    )
    
    report_file = output_dir / "COST.md"
    report_file.write_text(report)
    
    report_data = {
        'model': model,
        'total_cost': total_cost,
        'processing_time': processing_time,
        'num_files': num_files
    }
    _save_usage_json(output_dir, usage_stats, report_data)
    
    return report_file


def _generate_header_section(model: str, total_cost: float, processing_time: float, num_files: int) -> str:
    """Generate report header section."""
    return f"""# API Cost Report

**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Model**: `{model}`
**Processing Time**: {processing_time:.1f} seconds
**Files Processed**: {num_files}

## 💰 Total Cost

### **${total_cost:.4f} USD**

"""


def _generate_token_usage_table(usage_stats: UsageStats, pricing: Dict, model: str, total_cost: float) -> str:
    """Generate token usage markdown table."""
    input_rate = get_input_rate(pricing, usage_stats.total_input_tokens)
    output_rate = pricing.get('output', 0)
    
    return f"""## 📊 Token Usage

| Token Type | Count | Cost (USD) | Notes |
|------------|-------|------------|-------|
| Input Tokens | {usage_stats.input_tokens:,} | ${(usage_stats.input_tokens / 1_000_000 * input_rate):.4f} | Regular input |
| Output Tokens | {usage_stats.output_tokens:,} | ${(usage_stats.output_tokens / 1_000_000 * output_rate):.4f} | Generated output |
| Cache Creation | {usage_stats.cache_creation_tokens:,} | ${_calculate_cache_display_cost(usage_stats.cache_creation_tokens, pricing, 'write'):.4f} | First use (25% premium) |
| Cache Read | {usage_stats.cache_read_tokens:,} | ${_calculate_cache_display_cost(usage_stats.cache_read_tokens, pricing, 'read'):.4f} | **90% savings!** |
| **Total** | **{usage_stats.total_input_tokens + usage_stats.output_tokens:,}** | **${total_cost:.4f}** | |

"""


def _generate_cache_performance_section(usage_stats: UsageStats, total_cost: float) -> str:
    """Generate cache performance section."""
    effective_discount = ((usage_stats.cache_savings_estimate / (total_cost + usage_stats.cache_savings_estimate)) * 100 if total_cost > 0 else 0)
    
    return f"""## 🚀 Cache Performance

| Metric | Value |
|--------|-------|
| Cache Hit Rate | {usage_stats.cache_hit_rate:.1f}% |
| Tokens Cached | {usage_stats.cache_read_tokens:,} |
| Estimated Savings | ${usage_stats.cache_savings_estimate:.4f} |
| Effective Discount | {effective_discount:.1f}% |

"""


def _generate_statistics_section(avg_cost_per_file: float, avg_input_tokens: float, 
                                  avg_output_tokens: float, total_cost: float, 
                                  processing_time: float, usage_stats: UsageStats) -> str:
    """Generate statistics section."""
    cost_per_second = (total_cost / processing_time if processing_time > 0 else 0)
    tokens_per_second = ((usage_stats.total_input_tokens + usage_stats.output_tokens) / processing_time if processing_time > 0 else 0)
    
    return f"""## 📈 Statistics

| Metric | Value |
|--------|-------|
| Average Cost per File | ${avg_cost_per_file:.4f} |
| Average Input Tokens per File | {avg_input_tokens:.0f} |
| Average Output Tokens per File | {avg_output_tokens:.0f} |
| Cost per Second | ${cost_per_second:.6f} |
| Tokens per Second | {tokens_per_second:.0f} |

"""


def _generate_optimization_tips(total_cost: float, usage_stats: UsageStats, pricing: Dict, model: str, top_5_files: list) -> str:
    """Generate optimization tips and most expensive files section."""
    report = """## 🏆 Most Expensive Files

| Rank | File | Input Tokens | Output Tokens | Cost (USD) |
|------|------|--------------|---------------|------------|
"""
    
    for i, file in enumerate(top_5_files, 1):
        report += f"| {i} | {file.get('filename', 'Unknown')} | {file['input_tokens']:,} | {file['output_tokens']:,} | ${file['cost']:.4f} |\n"
    
    report += f"""

## 💡 Cost Optimization Tips

1. **Batch Processing**: Consider using batch mode for 50% cost savings (current cost would be ~${total_cost * 0.5:.4f})
2. **Prompt Caching**: {_get_caching_advice(usage_stats)}

## 📋 Pricing Configuration

Current pricing (per million tokens) for {model}:
"""
    
    if pricing:
        input_pricing = pricing.get('input')
        if isinstance(input_pricing, dict):
            report += f"- Input (≤200K): ${input_pricing.get('under_200k', 0):.2f}\n"
            report += f"- Input (>200K): ${input_pricing.get('over_200k', 0):.2f}\n"
        else:
            report += f"- Input: ${input_pricing if input_pricing else 0:.2f}\n"
        report += f"- Output: ${pricing.get('output', 0):.2f}\n"
    
    report += """

---
*Report generated by the Text Processing pipeline*
*Pricing loaded from profile configuration*
"""
    
    return report


def _generate_report_content(model: str, total_cost: float, usage_stats: UsageStats,
                            pricing: Dict, processing_time: float, num_files: int,
                            avg_cost_per_file: float, avg_input_tokens: float,
                            avg_output_tokens: float, top_5_files: list) -> str:
    """Generate the markdown content for the cost report."""
    report = _generate_header_section(model, total_cost, processing_time, num_files)
    report += _generate_token_usage_table(usage_stats, pricing, model, total_cost)
    report += _generate_cache_performance_section(usage_stats, total_cost)
    report += _generate_statistics_section(avg_cost_per_file, avg_input_tokens, 
                                           avg_output_tokens, total_cost, 
                                           processing_time, usage_stats)
    report += _generate_optimization_tips(total_cost, usage_stats, pricing, model, top_5_files)
    
    return report


def _save_usage_json(output_dir: Path, usage_stats: UsageStats, report_data: Dict[str, Any]):
    """Save raw usage data as JSON for analysis.

    Args:
        output_dir: Directory to save the JSON file
        usage_stats: Usage statistics object
        report_data: Dictionary containing model, total_cost, processing_time, num_files
    """
    usage_json = {
        'timestamp': datetime.now().isoformat(),
        'model': report_data['model'],
        'total_cost_usd': report_data['total_cost'],
        'processing_time_seconds': report_data['processing_time'],
        'files_processed': report_data['num_files'],
        'token_usage': {
            'input': usage_stats.input_tokens,
            'output': usage_stats.output_tokens,
            'cache_creation': usage_stats.cache_creation_tokens,
            'cache_read': usage_stats.cache_read_tokens,
            'total': usage_stats.total_input_tokens + usage_stats.output_tokens
        },
        'per_file_costs': usage_stats.file_costs
    }
    
    usage_file = output_dir / "usage_data.json"
    with open(usage_file, 'w') as f:
        json.dump(usage_json, f, indent=2)


def _calculate_cache_display_cost(tokens: int, pricing: Dict, operation: str) -> float:
    """Calculate cache operation cost for display.

    This is a wrapper that adapts the pricing structure for display purposes.
    """
    if tokens == 0 or not pricing:
        return 0.0

    from .cost_calculator import _calculate_cache_cost

    return _calculate_cache_cost(tokens, pricing, operation)


def _get_caching_advice(usage_stats: UsageStats) -> str:
    """Provide caching advice based on usage patterns."""
    if usage_stats.cache_creation_tokens > 0 or usage_stats.cache_read_tokens > 0:
        cache_ratio = usage_stats.cache_read_tokens / (usage_stats.cache_creation_tokens + 1)
        if cache_ratio > 5:
            return "Caching is highly effective (high read-to-write ratio)"
        elif cache_ratio > 2:
            return "Caching is providing moderate benefits"
        else:
            return "Consider if caching is necessary (low reuse rate)"
    else:
        return "Not currently using prompt caching - consider enabling for repeated prompts"