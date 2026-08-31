#!/usr/bin/env python3
"""Base orchestrator class with shared logic for processing orchestrators."""

from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Tuple, Optional
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

    def setup_processing(self, output_dir: Path, dry_run: bool = False) -> Tuple[Optional[OpenRouter], Dict[str, Any]]:
        """
        Set up processing environment.

        Args:
            output_dir: Output directory for results
            dry_run: If True, skip client initialization

        Returns:
            Tuple of (API client or None, setup metadata)
        """
        from .reporting import setup_logging as _setup_logging

        _setup_logging(output_dir)

        metadata = {
            "start_time": datetime.now(),
            "dry_run": dry_run,
            "output_dir": output_dir
        }

        if dry_run:
            logger.info("🔍 DRY RUN MODE - No API calls will be made")
            logger.info(f"System prompt ({len(self.config['system_prompt'])} chars):")
            logger.info(self.config['system_prompt'][:500] + "...")
            return None, metadata

        client = self._initialize_api_client()
        return client, metadata

    def setup_logging(self, output_dir: Path) -> None:
        """Point run logging at the given directory (staging, during real runs)."""
        from .reporting import setup_logging

        setup_logging(output_dir)

    def _initialize_api_client(self) -> OpenRouter:
        """Initialize and configure the OpenRouter API client."""
        api_key = get_api_key()
        return OpenRouter(api_key=api_key)

    @abstractmethod
    def process_batch(self, files: list, client: OpenRouter, output_dir: Path) -> Dict[str, Any]:
        """
        Process a batch of files.

        Args:
            files: List of files to process
            client: OpenRouter API client
            output_dir: Output directory

        Returns:
            Processing statistics
        """
        pass

    @abstractmethod
    def generate_processing_reports(self, output_dir: Path, stats: Dict[str, Any],
                                  metadata: Dict[str, Any], duration: float) -> None:
        """
        Generate processing reports.

        Args:
            output_dir: Output directory
            stats: Processing statistics
            metadata: Processing metadata
            duration: Processing duration in seconds
        """
        pass
