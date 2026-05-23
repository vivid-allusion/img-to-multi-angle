#!/usr/bin/env python3
"""Batch request builder for TXT processing operations."""

from typing import Dict, Any, List
from loguru import logger
from .api_client import build_system_prompt

MAX_CUSTOM_ID_LENGTH = 64


class BatchRequestBuilder:
    """Builds batch requests from TXT items."""

    def __init__(self, config: Dict[str, Any], use_cache: bool = False):
        """
        Initialize the batch request builder.

        Args:
            config: Configuration dictionary with model settings
            use_cache: Whether to mark system prompt with cache_control
        """
        self.config = config
        self.use_cache = use_cache
        self.system_prompt = build_system_prompt(config)

    def create_batch_requests(self, txt_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Convert TXT items to batch request format.

        Args:
            txt_items: List of TXT dictionaries with 'filename' and 'content'

        Returns:
            List of batch request objects
        """
        requests = []

        for txt_item in txt_items:
            try:
                request = self._build_single_request(txt_item)
                if request:
                    requests.append(request)
            except Exception as e:
                logger.error(f"Error creating batch request for TXT {txt_item.get('filename')}: {e}")
                continue

        logger.info(f"Created {len(requests)} batch requests from {len(txt_items)} TXT files")
        return requests

    def _build_single_request(self, txt_item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build a single batch request from a TXT item.

        Args:
            txt_item: Dictionary with 'filename' and 'content'

        Returns:
            Batch request object

        Raises:
            ValueError: If required fields are missing
        """
        if 'content' not in txt_item:
            raise ValueError("Missing 'content' in txt_item")
        if 'filename' not in txt_item:
            raise ValueError("Missing 'filename' in txt_item")

        text_content = txt_item['content']
        filename = txt_item['filename']

        custom_id = self._create_custom_id(filename)

        return {
            "custom_id": custom_id,
            "params": self._build_request_params(text_content)
        }

    def _create_custom_id(self, filename: str) -> str:
        """
        Create a valid custom_id from a filename.

        Args:
            filename: Original filename

        Returns:
            Valid custom_id (alphanumeric, underscore, hyphen only)
        """
        safe_filename = ''.join(c if c.isalnum() or c in '-_' else '_' for c in filename)
        return f"txt_{safe_filename}"[:MAX_CUSTOM_ID_LENGTH]

    def _build_request_params(self, text_content: str) -> Dict[str, Any]:
        """
        Build request parameters for API call.

        Args:
            text_content: The text to process

        Returns:
            Request parameters dictionary
        """
        if self.use_cache:
            system_param = [{
                "type": "text",
                "text": self.system_prompt,
                "cache_control": {"type": "ephemeral"}
            }]
        else:
            system_param = self.system_prompt

        return {
            "model": self.config["model"],
            "max_tokens": self.config["max_tokens"],
            "temperature": self.config["temperature"],
            "messages": [{"role": "user", "content": text_content}],
            "system": system_param
        }