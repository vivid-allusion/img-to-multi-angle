#!/usr/bin/env python3
"""Configuration examples and templates for the text processing tool."""

FIELD_EXAMPLES = {
    'model': 'claude-3-5-sonnet-latest',
    'max_tokens': 800,
    'temperature': 0.3,
    'stream': False,
    'avg_output_tokens': 800,
    'trim_prompts': True,
    'normalize_spaces': True,
    'max_prompt_length': 5900,
    'include_filename': False,
    'max_retries': 2,
    'timeout': 600.0,
    'cache_ttl': '5m'
}
