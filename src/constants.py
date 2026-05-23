"""
Constants and configuration values used throughout the application.
Centralized location for magic numbers and default values.
"""

# File size limits (lines)
SOFT_LINE_LIMIT = 250
HARD_LINE_LIMIT = 400

# Batch processing constants
BATCH_CHUNK_SIZE = 100
MAX_BATCH_REQUESTS = 100_000
BATCH_CHECK_INTERVAL_MINUTES = 30
MAX_BATCH_WAIT_HOURS = 24

# Token estimation defaults
TOKEN_ESTIMATE_INPUT = 1500
TOKEN_ESTIMATE_OUTPUT = 800
TOKEN_COUNT_TIMEOUT = 5

# Cost calculation
MILLION = 1_000_000

# Progress logging
PROGRESS_LOG_INTERVAL = 10

# Default configuration values
DEFAULT_TEMPERATURE = 0.3
DEFAULT_MAX_TOKENS = 1200
DEFAULT_TOP_P = 0.95

# Directory structure
INPUT_DIR = "USER-FILES/04.INPUT"
OUTPUT_DIR = "USER-FILES/05.OUTPUT"
PROFILES_DIR = "USER-FILES/03.PROFILES"
CONFIG_DIR = "USER-FILES/01.CONFIG"
TEMP_DIR = "USER-FILES/07.TEMP"

# File naming patterns
TIMESTAMP_FORMAT = "%y%m%d_%H%M%S"
TIMESTAMP_FORMAT_FULL = "%Y-%m-%d %H:%M:%S"

# API retry settings
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 1
RETRY_BACKOFF_FACTOR = 2

# Report formatting
MAX_ERROR_MESSAGE_LENGTH = 50
MAX_FAILURES_IN_REPORT = 10

# CLI display
SEPARATOR_LINE = "=" * 50
SEPARATOR_LINE_LONG = "=" * 70

# Model identifiers
DEFAULT_MODEL = "claude-opus-4-1"

# Batch pricing discounts
BATCH_DISCOUNT_FACTOR = 0.5