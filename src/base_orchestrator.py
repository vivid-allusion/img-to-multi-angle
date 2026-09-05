#!/usr/bin/env python3
"""Base orchestrator class with shared logic for processing orchestrators."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any
from openrouter import OpenRouter
from loguru import logger

from .auth import get_api_key


class BaseOrchestrator(ABC):
    """Abstract base class for processing orchestrators."""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the orchestrator.

        Args:
            config: Configuration dictionary
        """
        self.config = config

    def setup_processing(self, output_dir: Path) -> None:
        """Set up the dry-run environment (no client, no API calls).

        Real runs wire their own client and staging logging through
        `process_all_md_files`; this helper serves the dry-run branch.
        """
        self.setup_logging(output_dir)

        logger.info("🔍 DRY RUN MODE - No API calls will be made")
        logger.info(f"System prompt ({len(self.config['system_prompt'])} chars):")
        logger.info(self.config['system_prompt'][:500] + "...")

    def setup_logging(self, output_dir: Path) -> None:
        """Point run logging at the given directory (staging, during real runs)."""
        from .reporting import setup_logging

        setup_logging(output_dir)

    def _initialize_api_client(self) -> OpenRouter:
        """Initialize and configure the OpenRouter API client."""
        api_key = get_api_key()
        timeout_ms = int(self.config["retry_config"]["timeout"] * 1000)
        return OpenRouter(api_key=api_key, timeout_ms=timeout_ms)

    @abstractmethod
    def process_batch(self, parsed_files: list, client: OpenRouter, output_dir: Path) -> Dict[str, Any]:
        """
        Process a batch of files.

        Args:
            parsed_files: List of (md_path, ParsedMdInput) tuples
            client: OpenRouter API client
            output_dir: Output directory

        Returns:
            Processing statistics
        """
        pass

    @abstractmethod
    def generate_processing_reports(self, output_dir: Path, stats: Dict[str, Any],
                                    duration: float) -> None:
        """
        Generate processing reports.

        Args:
            output_dir: Output directory
            stats: Processing statistics
            duration: Processing duration in seconds
        """
        pass
