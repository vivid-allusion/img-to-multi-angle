"""
Batch result parser for OpenRouter API batch operations.
Fetches and processes batch results for multi-angle MD processing.
"""

import json
from typing import Dict, Any, Optional, Generator
from pathlib import Path
from loguru import logger
from openrouter import OpenRouter

from .response_utils import extract_response_text

PROGRESS_LOG_INTERVAL = 10


def _strip_custom_id_prefix(custom_id: str) -> str:
    """Remove the md_ prefix from a custom ID.

    Args:
        custom_id: Custom ID string starting with 'md_'

    Returns:
        Custom ID with prefix removed
    """
    return custom_id[3:] if custom_id.startswith("md_") else custom_id


class BatchResultParser:
    """Handles batch result fetching and parsing."""

    def __init__(self, client: OpenRouter, config: Dict[str, Any]):
        """Initialize batch result parser.

        Args:
            client: OpenRouter API client
            config: Configuration dictionary
        """
        self.client = client
        self.config = config

    def fetch_results(self, batch_id: str) -> Generator[Dict[str, Any], None, None]:
        """Fetch results from a completed batch.

        Args:
            batch_id: The batch ID to fetch results for

        Yields:
            Individual result entries
        """
        try:
            logger.info(f"Fetching results for batch {batch_id}...")

            result_stream = self.client.chat.completions.batch.results(batch_id)

            for entry in result_stream:
                yield entry

        except Exception as e:
            logger.error(f"Error fetching batch results: {e}")
            raise

    def _load_original_texts(self, batch_id: str) -> Optional[Dict[str, Any]]:
        """Load original items mapping for a batch.

        Args:
            batch_id: The batch ID

        Returns:
            Dictionary mapping filename to original item data, or None
        """
        try:
            batch_dir = self.config.get("batch_config", {}).get(
                "batch_request_dir", "USER-FILES/05.OUTPUT/batch_requests"
            )
            mapping_file = Path(batch_dir) / f"{batch_id}_original_items.json"

            if mapping_file.exists():
                with open(mapping_file, "r") as f:
                    items_mapping = json.load(f)
                logger.info(f"Loaded original items mapping from {mapping_file}")
                return items_mapping
            else:
                logger.warning(f"No original items mapping found for batch {batch_id}")
                return None

        except Exception as e:
            logger.error(f"Error loading original items: {e}")
            return None

    def parse_results(self, batch_id: str) -> Dict[str, Any]:
        """Parse batch results and organize by success/failure.

        Args:
            batch_id: The batch ID to parse results for

        Returns:
            Dictionary with parsed results organized by status
        """
        original_texts = self._load_original_texts(batch_id)

        results = {
            "batch_id": batch_id,
            "succeeded": [],
            "failed": [],
            "total_count": 0,
            "success_count": 0,
            "failure_count": 0,
            "original_texts": original_texts
        }

        try:
            for entry in self.fetch_results(batch_id):
                results["total_count"] += 1

                if hasattr(entry, 'response') and entry.response:
                    text_data = self._parse_successful_result(entry, original_texts)
                    results["succeeded"].append(text_data)
                    results["success_count"] += 1

                    if results["success_count"] % PROGRESS_LOG_INTERVAL == 0:
                        logger.info(f"Parsed {results['success_count']} successful results...")

                else:
                    failure_data = self._parse_failed_result(entry)
                    results["failed"].append(failure_data)
                    results["failure_count"] += 1

            logger.success(f"✅ Parsed {results['total_count']} results: "
                         f"{results['success_count']} succeeded, {results['failure_count']} failed")

        except Exception as e:
            logger.error(f"Error parsing results: {e}")
            results["error"] = str(e)

        return results

    def _parse_successful_result(self, entry: Any, original_texts: Dict[str, Any] = None) -> Dict[str, Any]:
        """Parse a successful batch result entry.

        Args:
            entry: Result entry from batch stream
            original_texts: Mapping of filename to original item data

        Returns:
            Result data with text response
        """
        try:
            custom_id = entry.custom_id if hasattr(entry, "custom_id") else "unknown"

            response = entry.response
            response_text = extract_response_text(response)

            input_name, angle_name = self._extract_names_from_custom_id(custom_id)

            result = {
                "filename": custom_id,
                "input_name": input_name,
                "angle_name": angle_name,
                "response": response_text,
                "usage": {
                    "input_tokens": response.usage.prompt_tokens if hasattr(response, "usage") and response.usage else 0,
                    "output_tokens": response.usage.completion_tokens if hasattr(response, "usage") and response.usage else 0,
                },
            }

            if original_texts and input_name in original_texts:
                item = original_texts[input_name]
                result["original_image"] = item.get("dataset_b", "")
                ref_images = item.get("dataset_c", [])
                result["ref_images"] = "\n\n".join(f"![image]({url})" for url in ref_images)

            return result

        except Exception as e:
            logger.error(f"Error parsing successful result: {e}")
            return {
                "custom_id": "parse_error",
                "error": str(e),
            }

    def _extract_names_from_custom_id(self, custom_id: str) -> tuple[str, str]:
        """Extract input filename and angle name from custom_id.

        Format: md_{filename}_{angle_name}

        Args:
            custom_id: The custom ID string (must start with 'md_')

        Returns:
            Tuple of (input_name, angle_name)
        """
        assert custom_id.startswith("md_"), f"Expected md_ prefix, got: {custom_id}"
        remainder = _strip_custom_id_prefix(custom_id)

        parts = remainder.rsplit("_", 1)
        if len(parts) == 2:
            return parts[0], parts[1]

        return remainder, ""

    def _parse_failed_result(self, entry: Any) -> Dict[str, Any]:
        """Parse a failed batch result entry.

        Args:
            entry: Failed result entry

        Returns:
            Failure information
        """
        try:
            custom_id = entry.custom_id if hasattr(entry, 'custom_id') else "unknown"

            error_info = {
                "custom_id": custom_id,
                "filename": _strip_custom_id_prefix(custom_id),
                "error_type": "failed",
            }

            if hasattr(entry, 'response') and entry.response:
                error_info["error_message"] = str(entry.response)

            return error_info

        except Exception as e:
            logger.error(f"Error parsing failed result: {e}")
            return {
                "custom_id": "parse_error",
                "error": str(e)
            }

    def save_results(self, results: Dict[str, Any], output_dir: Optional[Path] = None) -> Dict[str, Path]:
        """Save parsed results to output files.

        Args:
            results: Parsed results dictionary
            output_dir: Optional output directory override

        Returns:
            Dictionary of saved file paths
        """
        from .batch_result_saver import BatchResultSaver

        saver = BatchResultSaver(self.config)
        return saver.save_results(results, output_dir)
