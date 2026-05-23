#!/usr/bin/env python3
"""Strict configuration validator with NO DEFAULTS policy."""

from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
import yaml
from .config_reporter import ConfigReporter


class ConfigurationValidator:
    """Validates configuration with zero tolerance for defaults or conflicts."""

    def __init__(self):
        """Initialize the validator with required field definitions."""
        # Track config sources for better error messages
        self.config_sources = {}
        # Define all required fields by configuration source
        self.required_base_config = {
            "model",
            "max_tokens",
            "temperature",
            "stream",
            "processing_options",
            "retry_config",
            "batch_config",
            "avg_output_tokens"
        }

        self.required_processing_options = {
            "trim_prompts",
            "normalize_spaces",
            "max_prompt_length",
            "include_filename"
        }

        self.required_retry_config = {
            "max_retries",
            "timeout"
        }

        self.required_batch_config = {
            "max_requests_per_batch",
            "batch_request_dir",
            "save_batch_request_file"
        }

    # UNUSED METHOD - Commented out pending removal
    # This method was defined but never called in the codebase.
    # It appears to have been intended for tracking config sources but was never implemented.
    # Last verified unused: 2026-03-05
    # If needed in the future, uncomment and implement the tracking logic.
    #
    # def track_config_source(self, key: str, value: Any, source_file: Path, line_number: Optional[int] = None):
    #     """Track where each configuration value came from.
    #
    #     Args:
    #         key: Configuration key
    #         value: Configuration value
    #         source_file: File where this config was defined
    #         line_number: Optional line number in source file
    #     """
    #     self.config_sources[key] = {
    #         'value': value,
    #         'source': str(source_file),
    #         'line': line_number
    #     }


    def validate_yaml_file(self, file_path: Path) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """
        Validate a YAML file - check it exists, is not empty, and has valid syntax.

        Args:
            file_path: Path to YAML file

        Returns:
            Tuple of (is_valid, parsed_data, error_message)
        """
        # Check file exists
        if not file_path.exists():
            return False, None, f"File not found: {file_path}"

        # Check file is not empty
        if file_path.stat().st_size == 0:
            return False, None, f"Empty file: {file_path}"

        # Parse YAML (let parser errors bubble up as requested by user)
        try:
            with open(file_path, 'r') as f:
                content = f.read()

                # Check if file only has comments/whitespace
                lines = content.split('\n')
                has_content = any(line.strip() and not line.strip().startswith('#')
                                 for line in lines)
                if not has_content:
                    return False, None, f"File contains only comments/whitespace: {file_path}"

                # Parse the YAML
                data = yaml.safe_load(content)

                # Ensure we got actual data (not None)
                if data is None:
                    return False, None, f"File parsed as empty: {file_path}"

                return True, data, None

        except yaml.YAMLError as e:
            # User wants raw parser errors (option 1)
            raise

    def check_conflicts(self, config_data: Dict[str, Any], profile_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Check for conflicts between configuration sources.
        User selected option 2: Fail immediately - no conflicts allowed.

        Args:
            config_data: Data from 01.CONFIG
            profile_data: Data from 03.PROFILES

        Returns:
            Tuple of (has_conflicts, list_of_conflicting_keys)
        """
        conflicts = []

        # Get all top-level keys
        config_keys = set(config_data.keys())
        profile_keys = set(profile_data.keys())

        # Find overlapping keys (excluding metadata which is expected in profiles)
        overlapping = config_keys & profile_keys - {"metadata", "enabled"}

        # Check each overlapping key
        for key in overlapping:
            # Some keys are expected to be overridden by profiles
            override_allowed = {"model", "temperature", "max_tokens", "batch_mode", "parameters"}
            if key not in override_allowed:
                conflicts.append(key)

        return len(conflicts) > 0, conflicts

    def _validate_base_fields(self, config: Dict[str, Any]) -> List[str]:
        """Validate top-level required fields.
        
        Args:
            config: Configuration dictionary
            
        Returns:
            List of missing field names
        """
        missing = []
        for field in self.required_base_config:
            if field not in config:
                missing.append(field)
        return missing
    
    def _validate_processing_options(self, config: Dict[str, Any]) -> List[str]:
        """Validate processing_options section.
        
        Args:
            config: Configuration dictionary
            
        Returns:
            List of missing field names with prefix
        """
        missing = []
        if "processing_options" in config:
            for field in self.required_processing_options:
                if field not in config["processing_options"]:
                    missing.append(f"processing_options.{field}")
        return missing
    
    def _validate_retry_config(self, config: Dict[str, Any]) -> List[str]:
        """Validate retry_config section.
        
        Args:
            config: Configuration dictionary
            
        Returns:
            List of missing field names with prefix
        """
        missing = []
        if "retry_config" in config:
            for field in self.required_retry_config:
                if field not in config["retry_config"]:
                    missing.append(f"retry_config.{field}")
        return missing
    
    def _validate_batch_config(self, config: Dict[str, Any]) -> List[str]:
        """Validate batch_config section.
        
        Args:
            config: Configuration dictionary
            
        Returns:
            List of missing field names with prefix
        """
        missing = []
        if "batch_config" in config:
            for field in self.required_batch_config:
                if field not in config["batch_config"]:
                    missing.append(f"batch_config.{field}")
        return missing
    
    def _validate_cache_config(self, config: Dict[str, Any]) -> List[str]:
        """Validate cache_config section if present.
        
        Args:
            config: Configuration dictionary
            
        Returns:
            List of missing field names with prefix
        """
        missing = []
        if "cache_config" in config:
            cache_config = config["cache_config"]
            if "enabled" not in cache_config:
                missing.append("cache_config.enabled")
                return missing
            if cache_config["enabled"]:
                required_cache = {"cache_system_prompt", "cache_ttl", "report_cache_metrics"}
                for field in required_cache:
                    if field not in cache_config:
                        missing.append(f"cache_config.{field}")
                    elif not cache_config[field] and cache_config[field] is not False:
                        missing.append(f"cache_config.{field} (empty value)")
        return missing

    def validate_required_fields(self, config: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate that all required fields are present.

        Args:
            config: Merged configuration dictionary

        Returns:
            Tuple of (is_valid, list_of_missing_fields)
        """
        missing_fields = []
        missing_fields.extend(self._validate_base_fields(config))
        missing_fields.extend(self._validate_processing_options(config))
        missing_fields.extend(self._validate_retry_config(config))
        missing_fields.extend(self._validate_batch_config(config))
        missing_fields.extend(self._validate_cache_config(config))
        
        return len(missing_fields) == 0, missing_fields

    def validate_configuration_paths(self) -> Tuple[bool, List[str]]:
        """
        Validate that required configuration directories exist.

        Returns:
            Tuple of (all_exist, list_of_missing_paths)
        """
        missing_paths = []

        base_path = Path("USER-FILES")
        required_dirs = [
            base_path / "01.CONFIG",
            base_path / "03.PROFILES"
        ]

        for dir_path in required_dirs:
            if not dir_path.exists():
                missing_paths.append(str(dir_path))

        return len(missing_paths) == 0, missing_paths

    def validate_all(self, config: Dict[str, Any],
                    config_source: Path,
                    profile_source: Optional[Path] = None) -> Tuple[bool, List[str]]:
        """
        Perform comprehensive validation of all configuration.

        Args:
            config: Merged configuration dictionary
            config_source: Path to base config file
            profile_source: Optional path to profile file

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []

        # 1. Validate paths exist
        paths_valid, missing_paths = self.validate_configuration_paths()
        if not paths_valid:
            errors.append(f"Missing configuration directories: {', '.join(missing_paths)}")

        # 2. Validate required fields
        fields_valid, missing_fields = self.validate_required_fields(config)
        if not fields_valid:
            errors.append(f"Missing required fields: {', '.join(missing_fields)}")

        # 3. Validate no empty values
        empty_fields = self._find_empty_values(config)
        if empty_fields:
            errors.append(f"Empty/None values found: {', '.join(empty_fields)}")

        return len(errors) == 0, errors

    def _find_empty_values(self, config: Dict[str, Any], prefix: str = "") -> List[str]:
        """
        Recursively find fields with empty or None values.

        Args:
            config: Configuration dictionary
            prefix: Current path prefix for nested fields

        Returns:
            List of field paths with empty values
        """
        empty_fields = []

        for key, value in config.items():
            field_path = f"{prefix}.{key}" if prefix else key

            # Skip metadata and some optional fields
            if key in {"metadata", "enabled", "prompt_suffix", "fields_to_remove"}:
                continue

            if value is None or value == "":
                empty_fields.append(field_path)
            elif isinstance(value, dict):
                # Recurse into nested dicts
                nested_empty = self._find_empty_values(value, field_path)
                empty_fields.extend(nested_empty)

        return empty_fields


    def generate_error_report(self, errors: List[str]) -> str:
        """
        Generate a detailed error report for configuration issues.

        Args:
            errors: List of error messages

        Returns:
            Formatted error report
        """
        # Delegate to ConfigReporter for report generation
        reporter = ConfigReporter()
        return reporter.generate_error_report(errors)