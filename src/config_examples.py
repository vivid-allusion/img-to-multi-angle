#!/usr/bin/env python3
"""Configuration examples and templates for the text processing tool."""

FIELD_EXAMPLES = {
    'model': 'claude-3-5-sonnet-latest',
    'max_tokens': 800,
    'temperature': 0.3,
    'stream': False,
    'avg_output_tokens': 800,
    'batch_mode': True,
    'trim_prompts': True,
    'normalize_spaces': True,
    'max_prompt_length': 5900,
    'include_filename': False,
    'max_retries': 2,
    'timeout': 600.0,
    'max_requests_per_batch': 10000,
    'batch_request_dir': 'USER-FILES/05.OUTPUT/batch_requests',
    'save_batch_request_file': True,
    'check_interval_minutes': 5,
    'max_wait_hours': 24,
    'cache_system_prompt': True,
    'cache_ttl': '5m',
    'report_cache_metrics': True
}
