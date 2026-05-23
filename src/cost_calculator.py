#!/usr/bin/env python3
"""Cost calculation logic for API usage."""

from typing import Dict, List, Any
from dataclasses import dataclass, field

CACHE_SAVINGS_BASE_RATE = 3.0


@dataclass
class UsageStats:
    """Track usage statistics for API calls."""
    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_tokens: int = 0
    cache_read_tokens: int = 0
    file_costs: List[Dict[str, Any]] = field(default_factory=list)
    
    def add_usage(self, usage_data: Dict[str, Any], cost: float):
        """Add usage data from a single API call."""
        self.input_tokens += usage_data.get('input_tokens', 0)
        self.output_tokens += usage_data.get('output_tokens', 0)
        self.cache_creation_tokens += usage_data.get('cache_creation_input_tokens', 0)
        self.cache_read_tokens += usage_data.get('cache_read_input_tokens', 0)
        
        # Track per-file costs with cache details
        self.file_costs.append({
            'filename': usage_data.get('filename'),
            'input_tokens': usage_data.get('input_tokens', 0),
            'output_tokens': usage_data.get('output_tokens', 0),
            'cache_creation_tokens': usage_data.get('cache_creation_input_tokens', 0),
            'cache_read_tokens': usage_data.get('cache_read_input_tokens', 0),
            'cost': cost
})
    
    @property
    def total_input_tokens(self) -> int:
        """Total input tokens including cache operations."""
        return self.input_tokens + self.cache_creation_tokens + self.cache_read_tokens
    
    @property
    def cache_hit_rate(self) -> float:
        """Calculate cache hit rate as percentage."""
        total_cache = self.cache_creation_tokens + self.cache_read_tokens
        if total_cache == 0:
            return 0.0
        return (self.cache_read_tokens / total_cache) * 100
    
    @property
    def cache_savings_estimate(self) -> float:
        """Estimate savings from cache usage (rough calculation)."""
        if self.cache_read_tokens > 0:
            normal_cost = (self.cache_read_tokens / 1_000_000) * CACHE_SAVINGS_BASE_RATE
            cache_cost = normal_cost * 0.1
            return normal_cost - cache_cost
        return 0.0


def _calculate_tiered_input_cost(tokens: int, model_pricing: Dict, total_input: int) -> float:
    """Calculate cost for tiered input pricing.
    
    Args:
        tokens: Input tokens
        model_pricing: Model pricing dict
        total_input: Total input tokens including cache
        
    Returns:
        Cost in USD
    """
    if total_input <= 200000:
        rate = model_pricing['input']['under_200k']
    else:
        rate = model_pricing['input']['over_200k']
    return (tokens / 1_000_000) * rate


def _calculate_simple_input_cost(tokens: int, model_pricing: Dict) -> float:
    """Calculate cost for simple input pricing.
    
    Args:
        tokens: Input tokens
        model_pricing: Model pricing dict
        
    Returns:
        Cost in USD
    """
    rate = model_pricing['input']
    return (tokens / 1_000_000) * rate


def _calculate_output_cost(tokens: int, model_pricing: Dict) -> float:
    """Calculate cost for output tokens.
    
    Args:
        tokens: Output tokens
        model_pricing: Model pricing dict
        
    Returns:
        Cost in USD
    """
    rate = model_pricing['output']
    return (tokens / 1_000_000) * rate


def _calculate_cache_costs(usage_data: Dict[str, Any], model_pricing: Dict) -> float:
    """Calculate total cache costs.
    
    Args:
        usage_data: Usage data with cache tokens
        model_pricing: Model pricing dict
        
    Returns:
        Cost in USD
    """
    cost = 0.0
    cache_creation = usage_data.get('cache_creation_input_tokens', 0)
    cache_read = usage_data.get('cache_read_input_tokens', 0)
    
    if cache_creation > 0 and 'cache' in model_pricing:
        cost += _calculate_cache_cost(cache_creation, model_pricing, 'write')
    
    if cache_read > 0 and 'cache' in model_pricing:
        cost += _calculate_cache_cost(cache_read, model_pricing, 'read')
    
    return cost


def calculate_cost(usage_data: Dict[str, Any], config: Dict[str, Any], model: str, batch_mode: bool = False) -> float:
    """
    Calculate cost for a single API call based on usage and pricing.
    
    Args:
        usage_data: Token usage from API response
        config: Full config with pricing section from profile
        model: Model name being used (can be nickname or full name)
        batch_mode: Whether to use batch pricing (50% discount)
        
    Returns:
        Cost in USD
    """
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


def get_input_rate(pricing: Dict, total_tokens: int) -> float:
    """Get the input rate based on token count.
    
    Args:
        pricing: Model pricing dict (single model's pricing)
        total_tokens: Total number of tokens
        
    Returns:
        Rate per million tokens
    """
    if not pricing:
        return 0.0
    
    input_pricing = pricing.get('input')
    
    if isinstance(input_pricing, dict):
        if total_tokens <= 200000:
            return input_pricing.get('under_200k', 0.0)
        else:
            return input_pricing.get('over_200k', 0.0)
    else:
        return input_pricing if input_pricing else 0.0


def _calculate_cache_cost(tokens: int, model_pricing: Dict, operation: str) -> float:
    """Calculate cache operation cost.
    
    Args:
        tokens: Number of tokens
        model_pricing: Model-specific pricing
        operation: 'read' or 'write'
        
    Returns:
        Cost in USD
    """
    if 'cache' not in model_pricing:
        return 0.0
    
    cache_pricing = model_pricing['cache']
    if isinstance(cache_pricing, dict):
        if 'under_200k' in cache_pricing:
            # Tiered cache pricing (Sonnet)
            if tokens <= 200000:
                rate = cache_pricing['under_200k'][operation]
            else:
                rate = cache_pricing['over_200k'][operation]
        else:
            # Simple cache pricing (Opus, Haiku)
            rate = cache_pricing.get(operation, 0)
    else:
        rate = 0
    
    return (tokens / 1_000_000) * rate