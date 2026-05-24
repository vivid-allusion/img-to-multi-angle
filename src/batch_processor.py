"""Batch processor for multi-angle OpenRouter API batch operations."""

import json
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime
from loguru import logger
from openrouter import OpenRouter

from .batch_request_builder import BatchRequestBuilder
from .config import require_batch_config


class BatchProcessor:
    """Handles batch request creation and submission for multi-angle processing."""

    def __init__(self, client: OpenRouter, config: Dict[str, Any]):
        """Initialize batch processor.

        Args:
            client: OpenRouter API client
            config: Configuration dictionary with model settings
        """
        self.client = client
        self.config = config
        self.batch_config = require_batch_config(config)

    def create_batch_requests(
        self, md_items: List[Dict[str, Any]], angles: Dict[str, str], um_template: str
    ) -> List[Dict[str, Any]]:
        """Convert MD items + angles to batch request format.

        Args:
            md_items: List of dicts with filename, dataset_a, dataset_b, dataset_c
            angles: Dict mapping angle_name -> template content
            um_template: User message template string

        Returns:
            List of batch request objects
        """
        cache_config = self.config.get("cache_config", {})
        use_cache = cache_config.get("enabled", False) and len(angles) >= 2
        builder = BatchRequestBuilder(self.config, use_cache)
        return builder.create_batch_requests(md_items, angles, um_template)

    def submit_batch(self, requests: List[Dict[str, Any]]) -> str:
        """Submit batch to OpenRouter API.

        Args:
            requests: List of batch request objects

        Returns:
            Batch ID for monitoring
        """
        try:
            if "max_requests_per_batch" not in self.batch_config:
                raise ValueError("Missing 'max_requests_per_batch' in batch_config")
            max_requests = self.batch_config["max_requests_per_batch"]
            if len(requests) > max_requests:
                logger.warning(f"Batch has {len(requests)} requests, exceeding limit of {max_requests}")
                logger.info("Consider splitting into multiple batches")

            logger.info(f"Submitting batch with {len(requests)} requests...")

            formatted_requests = []
            for req in requests:
                formatted_requests.append(
                    {
                        "custom_id": req.get("custom_id", ""),
                        "method": "POST",
                        "url": "/v1/chat/completions",
                        "body": req.get("body", req.get("params", req)),
                    }
                )

            batch = self.client.chat.completions.batch.create(requests=formatted_requests)

            batch_id = batch.id
            logger.success(f"Batch submitted successfully! ID: {batch_id}")
            logger.info(f"Processing status: {batch.processing_status}")
            logger.info(f"Created at: {batch.created_at}")

            self._save_batch_info(batch_id, len(requests))

            return batch_id

        except Exception as e:
            logger.error(f"Error submitting batch: {e}")
            raise

    def _save_batch_info(self, batch_id: str, request_count: int) -> None:
        """Save batch information for tracking."""
        if "batch_request_dir" not in self.batch_config:
            raise ValueError("Missing 'batch_request_dir' in batch_config")
        output_dir = Path(self.batch_config["batch_request_dir"])
        output_dir.mkdir(parents=True, exist_ok=True)

        batch_info = {
            "batch_id": batch_id,
            "request_count": request_count,
            "submitted_at": datetime.now().isoformat(),
            "model": self.config["model"],
            "estimated_cost": self._estimate_batch_cost(request_count),
        }

        info_file = output_dir / f"{batch_id}_info.json"
        with open(info_file, "w") as f:
            json.dump(batch_info, f, indent=2)

        logger.info(f"Batch info saved to {info_file}")

    def _estimate_batch_cost(self, request_count: int) -> Dict[str, Any]:
        """Estimate cost for batch processing."""
        if "pricing" not in self.config:
            logger.error("No pricing configuration found")
            return {"estimated_total_cost": 0, "error": "Missing pricing configuration"}

        pricing = self.config["pricing"]
        avg_input_tokens = 2000
        avg_output_tokens = self.config.get("avg_output_tokens", 1000)

        if "input" not in pricing or "output" not in pricing:
            logger.error("Incomplete pricing configuration")
            return {"estimated_total_cost": 0, "error": "Incomplete pricing configuration"}

        input_pricing = pricing["input"]
        if isinstance(input_pricing, dict):
            if "under_200k" not in input_pricing:
                return {"estimated_total_cost": 0, "error": "Missing pricing tier"}
            input_cost_per_mtok = input_pricing["under_200k"]
        else:
            input_cost_per_mtok = input_pricing

        output_cost_per_mtok = pricing["output"]

        total_input_tokens = request_count * avg_input_tokens
        total_output_tokens = request_count * avg_output_tokens

        input_cost = (total_input_tokens / 1_000_000) * input_cost_per_mtok
        output_cost = (total_output_tokens / 1_000_000) * output_cost_per_mtok

        return {
            "estimated_input_cost": round(input_cost, 4),
            "estimated_output_cost": round(output_cost, 4),
            "estimated_total_cost": round(input_cost + output_cost, 4),
            "cost_per_request": round((input_cost + output_cost) / request_count, 4),
        }

    def save_batch_requests(
        self,
        requests: List[Dict[str, Any]],
        batch_id: Optional[str] = None,
        original_items: Optional[List[Dict[str, Any]]] = None,
    ) -> Optional[Path]:
        """Save batch requests to JSONL file for debugging/reference."""
        if "save_batch_request_file" not in self.batch_config:
            raise ValueError("Missing 'save_batch_request_file' in batch_config")
        if not self.batch_config["save_batch_request_file"]:
            return None

        if "batch_request_dir" not in self.batch_config:
            raise ValueError("Missing 'batch_request_dir' in batch_config")
        output_dir = Path(self.batch_config["batch_request_dir"])
        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%y%m%d_%H%M%S")
        filename = f"batch_requests_{timestamp}.jsonl"
        if batch_id:
            filename = f"{batch_id}_requests.jsonl"

        filepath = output_dir / filename

        with open(filepath, "w") as f:
            for request in requests:
                f.write(json.dumps(request) + "\n")

        if original_items and batch_id:
            items_mapping = {}
            for item in original_items:
                if "filename" not in item:
                    raise ValueError("Missing 'filename' in item")
                items_mapping[item["filename"]] = item

            mapping_file = output_dir / f"{batch_id}_original_items.json"
            with open(mapping_file, "w") as f:
                json.dump(items_mapping, f, indent=2)
            logger.info(f"Original items mapping saved to {mapping_file}")

        logger.info(f"Batch requests saved to {filepath}")
        return filepath
