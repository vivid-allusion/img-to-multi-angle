#!/usr/bin/env python3
"""Configuration loader for multi-angle MD processing."""

from pathlib import Path
from typing import Dict, Any, Optional
import sys
from loguru import logger

from .profile_manager import load_profile, apply_profile_to_config
from .config_validator import ConfigurationValidator


def require_batch_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure batch_config is present in configuration.

    Args:
        config: Configuration dictionary

    Returns:
        The batch_config dictionary

    Raises:
        ValueError: If batch_config is missing
    """
    if "batch_config" not in config:
        raise ValueError("Missing 'batch_config' in configuration")
    return config["batch_config"]


def _load_base_config(validator: ConfigurationValidator, base_path: Path) -> Dict[str, Any]:
    """Load and validate the base API configuration."""
    api_config_path = base_path / "01.CONFIG" / "openrouter_config.yaml"

    valid, config_data, error = validator.validate_yaml_file(api_config_path)
    if not valid:
        logger.error(f"Configuration validation failed: {error}")
        sys.exit(1)

    logger.info(f"Loaded and validated API configuration from {api_config_path}")
    return config_data


def _load_and_merge_profile(config: Dict[str, Any], validator: ConfigurationValidator,
                           base_path: Path, profile_name: Optional[str]) -> None:
    """Load profile and merge with config after conflict checking."""
    profiles_dir = base_path / "03.PROFILES"
    profile = load_profile(profiles_dir, profile_name)

    if profile:
        # Check for conflicts BEFORE merging
        has_conflicts, conflicting_keys = validator.check_conflicts(config, profile)
        if has_conflicts:
            error_msg = f"Configuration conflict detected! Keys present in both config and profile: {', '.join(conflicting_keys)}"
            logger.error(error_msg)
            logger.error("NO CONFLICTS ALLOWED - each setting must be in either 01.CONFIG or 03.PROFILES, not both")
            sys.exit(1)

        # Apply all profile settings to config
        apply_profile_to_config(config, profile)


def _load_system_prompt(config: Dict[str, Any], base_path: Path) -> None:
    """Load system prompt from file."""
    system_prompt_file = base_path / "01.CONFIG" / "system_prompt.md"
    if system_prompt_file.exists():
        config["system_prompt"] = system_prompt_file.read_text(encoding='utf-8', errors='replace')
        logger.info(f"Loaded system prompt from system_prompt.md ({len(config['system_prompt'])} chars)")
    else:
        logger.error("No system prompt found - system_prompt.md missing")
        raise FileNotFoundError("No system prompt configuration found in USER-FILES/01.CONFIG/")


def _validate_required_fields(config: Dict[str, Any]) -> None:
    """Validate all required configuration fields are present."""
    # Validate ALL required configuration - NO DEFAULTS
    required_fields = ["model", "max_tokens", "temperature", "stream"]
    missing = [f for f in required_fields if f not in config]
    if missing:
        logger.error(f"Missing required configuration fields: {missing}")
        logger.error("All settings must be explicitly defined in USER-FILES/01.CONFIG/ or USER-FILES/03.PROFILES/")
        raise ValueError(f"Incomplete configuration: missing {missing}")

    # Check for required processing options
    if "processing_options" not in config:
        logger.error("Missing 'processing_options' in configuration")
        raise ValueError("Missing 'processing_options' - must be defined in USER-FILES/01.CONFIG/openrouter_config.yaml")

    # Validate processing_options has all required fields
    required_processing = ["trim_prompts", "normalize_spaces", "max_prompt_length", "include_filename"]
    missing_processing = [f for f in required_processing if f not in config["processing_options"]]
    if missing_processing:
        logger.error(f"Missing required processing_options fields: {missing_processing}")
        raise ValueError(f"Incomplete processing_options configuration: missing {missing_processing}")

    # Check for stream configuration
    if "stream" not in config:
        logger.error("Missing 'stream' configuration")
        raise ValueError("Missing 'stream' setting - must be defined in configuration")


def load_strict_config(profile_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Load and validate all configuration sources with NO DEFAULTS policy.

    Args:
        profile_name: Optional profile filename (without path). If None, auto-detects.

    Returns:
        Dict with all settings

    Raises:
        SystemExit: If any validation fails
    """
    validator = ConfigurationValidator()

    # First validate paths exist
    paths_valid, missing_paths = validator.validate_configuration_paths()
    if not paths_valid:
        error_report = validator.generate_error_report(
            [f"Missing configuration directories: {', '.join(missing_paths)}"]
        )
        logger.error(error_report)
        sys.exit(1)

    base_path = Path("USER-FILES")

    # Load base configuration
    config = _load_base_config(validator, base_path)

    # Load and merge profile
    _load_and_merge_profile(config, validator, base_path, profile_name)

    # Load system prompt
    _load_system_prompt(config, base_path)

    # Validate required fields
    _validate_required_fields(config)

    # Final validation of merged configuration
    api_config_path = base_path / "01.CONFIG" / "openrouter_config.yaml"
    is_valid, errors = validator.validate_all(config, api_config_path)
    if not is_valid:
        error_report = validator.generate_error_report(errors)
        logger.error(error_report)
        sys.exit(1)

    logger.success("✅ Configuration validation passed - NO DEFAULTS policy enforced")
    return config


def get_model_display_name(model_name: str, config: Optional[Dict[str, Any]] = None) -> str:
    """
    Get the display name for a model.
    
    Args:
        model_name: Full model name/ID
        config: Config dict containing model_nickname (required)
        
    Returns:
        Display name (nickname) for the model
        
    Raises:
        ValueError: If model_nickname not in config
    """
    if config and "model_nickname" in config:
        return config["model_nickname"]
    
    logger.error("model_nickname not found in config - profile must define model.nickname")
    raise ValueError("Missing model_nickname in configuration")


def get_output_directory(config: Optional[Dict[str, Any]] = None, suffix: str = "") -> Path:
    """Create and return timestamped output directory with profile information.

    Directory name format: YYMMDD_HHMMSS_model_tempX.X[_suffix]

    Args:
        config: Optional configuration dictionary containing model and temperature
        suffix: Optional suffix appended to directory name (e.g., "MULTI-ANGLE-MD")

    Returns:
        Path to the output directory
    """
    from datetime import datetime

    timestamp = datetime.now().strftime("%y%m%d_%H%M%S")

    dir_parts = [timestamp]

    if config:
        if "model" in config:
            model_name = config["model"]
            display_name = get_model_display_name(model_name, config)
            dir_parts.append(display_name)

        batch_mode = config["batch_mode"]
        mode_str = "BATCH" if batch_mode else "RT"
        dir_parts.append(mode_str)

        temp_value = None
        if "temperature" in config:
            temp_value = config["temperature"]

        if temp_value is not None:
            dir_parts.append(f"temp{temp_value}")

    if suffix:
        dir_parts.append(suffix)

    dir_name = "_".join(dir_parts)

    output_dir = Path("USER-FILES") / "05.OUTPUT" / dir_name
    output_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Created output directory: {output_dir}")
    return output_dir