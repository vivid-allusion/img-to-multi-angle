#!/usr/bin/env python3
"""Strict configuration validator with NO DEFAULTS policy."""

from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
import yaml
from .config_reporter import ConfigReporter


class YamlValidator:
    """Validates YAML file existence, content, and syntax."""

    @staticmethod
    def validate_yaml_file(file_path: Path) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """Validate a YAML file - check it exists, is not empty, and has valid syntax.

        Args:
            file_path: Path to YAML file

        Returns:
            Tuple of (is_valid, parsed_data, error_message)
        """
        if not file_path.exists():
            return False, None, f"File not found: {file_path}"

        if file_path.stat().st_size == 0:
            return False, None, f"Empty file: {file_path}"

        try:
            with open(file_path, 'r') as f:
                content = f.read()

            lines = content.split('\n')
            has_content = any(line.strip() and not line.strip().startswith('#') for line in lines)
            if not has_content:
                return False, None, f"File contains only comments/whitespace: {file_path}"

            data = yaml.safe_load(content)

            if data is None:
                return False, None, f"File parsed as empty: {file_path}"

            return True, data, None

        except yaml.YAMLError as e:
            return False, None, f"YAML syntax error in {file_path}: {e}"


class ConflictChecker:
    """Detects conflicts between configuration sources."""

    _OVERRIDE_ALLOWED = {"model", "temperature", "max_tokens", "parameters"}
    _EXCLUDED_KEYS = {"metadata", "enabled"}

    @staticmethod
    def check_conflicts(config_data: Dict[str, Any], profile_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Check for conflicts between configuration sources.

        Args:
            config_data: Data from 01.CONFIG
            profile_data: Data from 03.PROFILES

        Returns:
            Tuple of (has_conflicts, list_of_conflicting_keys)
        """
        config_keys = set(config_data.keys())
        profile_keys = set(profile_data.keys())

        overlapping = config_keys & profile_keys - ConflictChecker._EXCLUDED_KEYS

        conflicts = [key for key in overlapping if key not in ConflictChecker._OVERRIDE_ALLOWED]

        return len(conflicts) > 0, conflicts


class FieldValidator:
    """Validates required fields in configuration."""

    REQUIRED_BASE_CONFIG = {
        "model", "max_tokens", "temperature",
        "retry_config", "avg_output_tokens"
    }
    REQUIRED_RETRY_CONFIG = {
        "max_retries", "timeout", "transport_retries",
        "backoff_base_seconds", "backoff_max_seconds"
    }
    SKIPPED_KEYS = {"metadata", "enabled", "min_prompt_tokens"}

    def validate_required_fields(self, config: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate that all required fields are present.

        Args:
            config: Merged configuration dictionary

        Returns:
            Tuple of (is_valid, list_of_missing_fields)
        """
        missing_fields = []
        missing_fields.extend(self._validate_section(config, self.REQUIRED_BASE_CONFIG))
        missing_fields.extend(self._validate_nested(config, "retry_config", self.REQUIRED_RETRY_CONFIG))
        missing_fields.extend(self._validate_cache_config(config))

        return len(missing_fields) == 0, missing_fields

    def find_empty_values(self, config: Dict[str, Any], prefix: str = "") -> List[str]:
        """Recursively find fields with empty or None values.

        Args:
            config: Configuration dictionary
            prefix: Current path prefix for nested fields

        Returns:
            List of field paths with empty values
        """
        empty_fields = []

        for key, value in config.items():
            field_path = f"{prefix}.{key}" if prefix else key

            if key in self.SKIPPED_KEYS:
                continue

            if value is None or value == "":
                empty_fields.append(field_path)
            elif isinstance(value, dict):
                empty_fields.extend(self.find_empty_values(value, field_path))

        return empty_fields

    @staticmethod
    def _validate_section(config: Dict[str, Any], required: set) -> List[str]:
        return [f for f in required if f not in config]

    @staticmethod
    def _validate_nested(config: Dict[str, Any], section: str, required: set) -> List[str]:
        if section not in config:
            return []
        return [f"{section}.{f}" for f in required if f not in config[section]]

    @staticmethod
    def _validate_cache_config(config: Dict[str, Any]) -> List[str]:
        missing = []
        if "cache_config" not in config:
            return missing

        cache_config = config["cache_config"]
        if "enabled" not in cache_config:
            return ["cache_config.enabled"]

        if cache_config["enabled"]:
            ttl = cache_config.get("cache_ttl")
            if ttl is None or ttl == "":
                missing.append("cache_config.cache_ttl (must be set when cache is enabled)")
            elif ttl not in ("5m", "1h"):
                missing.append("cache_config.cache_ttl (must be '5m' or '1h')")

        return missing


class ConfigurationValidator:
    """Orchestrates configuration validation with zero tolerance for defaults or conflicts."""

    def __init__(self):
        self._yaml_validator = YamlValidator()
        self._conflict_checker = ConflictChecker()
        self._field_validator = FieldValidator()

    def validate_yaml_file(self, file_path: Path) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """Validate a YAML file."""
        return self._yaml_validator.validate_yaml_file(file_path)

    def check_conflicts(self, config_data: Dict[str, Any], profile_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Check for conflicts between configuration sources."""
        return self._conflict_checker.check_conflicts(config_data, profile_data)

    def validate_required_fields(self, config: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate that all required fields are present."""
        return self._field_validator.validate_required_fields(config)

    def validate_configuration_paths(self) -> Tuple[bool, List[str]]:
        """Validate that required configuration directories exist."""
        missing_paths = []
        base_path = Path("USER-FILES")
        for dir_path in [base_path / "01.CONFIG", base_path / "03.PROFILES"]:
            if not dir_path.exists():
                missing_paths.append(str(dir_path))

        return len(missing_paths) == 0, missing_paths

    def validate_all(self, config: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Perform comprehensive validation of all configuration."""
        errors = []

        paths_valid, missing_paths = self.validate_configuration_paths()
        if not paths_valid:
            errors.append(f"Missing configuration directories: {', '.join(missing_paths)}")

        fields_valid, missing_fields = self.validate_required_fields(config)
        if not fields_valid:
            errors.append(f"Missing required fields: {', '.join(missing_fields)}")

        empty_fields = self._field_validator.find_empty_values(config)
        if empty_fields:
            errors.append(f"Empty/None values found: {', '.join(empty_fields)}")

        return len(errors) == 0, errors

    def generate_error_report(self, errors: List[str]) -> str:
        """Generate a detailed error report for configuration issues."""
        reporter = ConfigReporter()
        return reporter.generate_error_report(errors)
