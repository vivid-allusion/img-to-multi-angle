#!/usr/bin/env python3
"""Configuration examples and templates for the text processing tool."""

# Example values for different configuration fields
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

# Complete example configuration
EXAMPLE_CONFIG = """# Example Configuration File
# All fields must be explicitly defined - NO DEFAULTS

# Core API settings
model: claude-3-5-sonnet-latest
max_tokens: 800
temperature: 0.3
stream: false
avg_output_tokens: 800

# Processing options
processing_options:
  trim_text: true
  normalize_spaces: true
  max_response_length: 40000
  include_filename: false

# Retry configuration
retry_config:
  max_retries: 2
  timeout: 600

# Batch configuration
batch_config:
  max_requests_per_batch: 10000
  batch_request_dir: USER-FILES/05.OUTPUT/batch_requests
  save_batch_request_file: true
  check_interval_minutes: 5
  max_wait_hours: 24

# Cache configuration (optional but must be complete if present)
cache_config:
  enabled: true
  cache_system_prompt: true
  cache_ttl: 5m
  report_cache_metrics: true
"""

# Profile example
EXAMPLE_PROFILE = """# Example Profile File
metadata:
  name: production
  version: 1.0.0
  description: Production text processing profile

# Override model settings
model: claude-3-5-sonnet-latest
temperature: 0.3
max_tokens: 1000

# Override processing options
processing_options:
  trim_text: true
  normalize_spaces: true
  include_filename: true
"""


def get_example_value(field_name: str):
    """
    Get example value for a configuration field.

    Args:
        field_name: Name of the field

    Returns:
        Example value or '<value>' placeholder
    """
    return FIELD_EXAMPLES.get(field_name, '<value>')


def get_example_configuration() -> str:
    """
    Get complete example configuration.

    Returns:
        Example configuration as string
    """
    return EXAMPLE_CONFIG


def get_example_profile() -> str:
    """
    Get example profile configuration.

    Returns:
        Example profile as string
    """
    return EXAMPLE_PROFILE