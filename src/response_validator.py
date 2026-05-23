#!/usr/bin/env python3
"""Response validation for text API responses."""

from typing import Dict, Any, Optional, Tuple
from loguru import logger


class ResponseValidator:
    """Validates text API responses for expected structure."""

    @staticmethod
    def validate_text_response(
        response: Any,
        text_id: str = "unknown"
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate text response structure.

        Args:
            response: API response object
            text_id: Text file identifier being processed

        Returns:
            Tuple[bool, Optional[str]]: (is_valid, error_message)
        """
        # Check stop reason
        valid_stop_reasons = ["end_turn", "max_tokens", "stop_sequence"]
        if hasattr(response, 'stop_reason'):
            if response.stop_reason not in valid_stop_reasons:
                logger.warning(f"Unexpected stop reason for {text_id}: {response.stop_reason}")

        # Check content structure
        if not response.content:
            return False, "Response has no content"

        # Check for text content
        has_text = False
        for block in response.content:
            if hasattr(block, 'text'):
                has_text = True
                break

        if not has_text:
            return False, "Response has no text content"

        return True, None

    @staticmethod
    def validate_usage_data(usage_data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Validate usage data from API response.

        Args:
            usage_data: Usage data dictionary

        Returns:
            Tuple[bool, Optional[str]]: (is_valid, error_message)
        """
        required_fields = ['input_tokens', 'output_tokens']

        for field in required_fields:
            if field not in usage_data:
                return False, f"Missing required field: {field}"

            if not isinstance(usage_data[field], (int, float)):
                return False, f"Field {field} must be numeric, got: {type(usage_data[field])}"

            if usage_data[field] < 0:
                return False, f"Field {field} cannot be negative: {usage_data[field]}"

        # Optional cache fields
        cache_fields = ['cache_creation_input_tokens', 'cache_read_input_tokens']
        for field in cache_fields:
            if field in usage_data:
                if not isinstance(usage_data[field], (int, float)):
                    return False, f"Field {field} must be numeric"
                if usage_data[field] < 0:
                    return False, f"Field {field} cannot be negative"

        return True, None