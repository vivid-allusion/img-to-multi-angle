#!/usr/bin/env python3
"""Local cost estimation for pre-run estimates (--cost-only). Real-run reports
use the provider-reported `usage.cost` (Q24)."""

from typing import Dict, Any


def _calculate_tiered_input_cost(tokens: int, model_pricing: Dict, total_input: int) -> float:
    """Calculate cost for tiered input pricing."""
    if total_input <= 200000:
        rate = model_pricing['input']['under_200k']
    else:
        rate = model_pricing['input']['over_200k']
    return (tokens / 1_000_000) * rate


def _calculate_simple_input_cost(tokens: int, model_pricing: Dict) -> float:
    """Calculate cost for simple input pricing."""
    rate = model_pricing['input']
    return (tokens / 1_000_000) * rate


def _calculate_output_cost(tokens: int, model_pricing: Dict) -> float:
    """Calculate cost for output tokens."""
    rate = model_pricing['output']
    return (tokens / 1_000_000) * rate


def _calculate_cache_costs(usage_data: Dict[str, Any], model_pricing: Dict) -> float:
    """Calculate total cache costs."""
    cost = 0.0
    cache_creation = usage_data.get('cache_creation_input_tokens', 0)
    cache_read = usage_data.get('cache_read_input_tokens', 0)
    
    if cache_creation > 0 and 'cache' in model_pricing:
        cost += _calculate_cache_cost(cache_creation, model_pricing, 'write')
    
    if cache_read > 0 and 'cache' in model_pricing:
        cost += _calculate_cache_cost(cache_read, model_pricing, 'read')
    
    return cost


def calculate_cost(usage_data: Dict[str, Any], config: Dict[str, Any]) -> float:
    """Calculate cost for a single API call based on usage and pricing."""
    if 'pricing' not in config:
        return 0.0
    
    model_pricing = config['pricing']
    
    if not model_pricing:
        return 0.0
    
    cost = 0.0
    input_tokens = usage_data.get('input_tokens', 0)
    
    if input_tokens > 0:
        if isinstance(model_pricing.get('input'), dict):
            total_input = input_tokens + usage_data.get('cache_creation_input_tokens', 0) + usage_data.get('cache_read_input_tokens', 0)
            cost += _calculate_tiered_input_cost(input_tokens, model_pricing, total_input)
        else:
            cost += _calculate_simple_input_cost(input_tokens, model_pricing)
    
    output_tokens = usage_data.get('output_tokens', 0)
    if output_tokens > 0:
        cost += _calculate_output_cost(output_tokens, model_pricing)
    
    cost += _calculate_cache_costs(usage_data, model_pricing)
    
    return cost


def _calculate_cache_cost(tokens: int, model_pricing: Dict, operation: str) -> float:
    """Calculate cache operation cost."""
    if 'cache' not in model_pricing:
        return 0.0
    
    cache_pricing = model_pricing['cache']
    if isinstance(cache_pricing, dict):
        if 'under_200k' in cache_pricing:
            if tokens <= 200000:
                rate = cache_pricing['under_200k'][operation]
            else:
                rate = cache_pricing['over_200k'][operation]
        else:
            rate = cache_pricing.get(operation, 0)
    else:
        rate = 0
    
    return (tokens / 1_000_000) * rate
