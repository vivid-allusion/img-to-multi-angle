#!/usr/bin/env python3
"""Profile management for multi-angle MD processor."""

from pathlib import Path
from typing import Dict, Any, List, Optional
import yaml
from loguru import logger


def load_profile(profiles_dir: Path, profile_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Load a profile from the profiles directory.

    Args:
        profiles_dir: Path to the profiles directory
        profile_name: Specific profile filename to load (e.g., 'profile.yaml')
                     If None, loads the default profile.yaml file

    Returns:
        Profile configuration dictionary or None if no profile found
    """
    if not profiles_dir.exists():
        logger.warning(f"Profiles directory not found: {profiles_dir}")
        return None

    if not profile_name:
        profile_name = "profile.yaml"
        logger.info("No profile specified, using default profile.yaml")

    if not profile_name.endswith('.yaml'):
        profile_name = f"{profile_name}.yaml"

    profile_path = profiles_dir / profile_name

    if profile_path.exists():
        with open(profile_path) as f:
            profile = yaml.safe_load(f)
            if profile and profile.get("enabled", True):
                return profile
            else:
                logger.warning(f"Profile {profile_path.name} is disabled")
                return None
    else:
        logger.error(f"Profile not found: {profile_name}")
        available = list(profiles_dir.glob("*.yaml"))
        if available:
            logger.info(f"Available profiles: {', '.join(p.name for p in available)}")
        else:
            logger.warning("No profile files found. Create profile.yaml in USER-FILES/03.PROFILES/")
        return None


def list_available_profiles() -> List[str]:
    """List all available profile files.

    Returns:
        List of profile filenames with status and metadata
    """
    base_path = Path("USER-FILES")
    profiles_dir = base_path / "03.PROFILES"

    if not profiles_dir.exists():
        return ["  No profiles directory found. Create USER-FILES/03.PROFILES/"]

    profiles = []
    yaml_files = sorted(profiles_dir.glob("*.yaml"))

    if not yaml_files:
        return ["  No profile files found. Create profiles in USER-FILES/03.PROFILES/"]

    for yaml_file in yaml_files:
        try:
            with open(yaml_file) as f:
                profile = yaml.safe_load(f)
                if profile:
                    enabled = profile.get("enabled", True)

                    model_display = "unknown"
                    if "model" in profile:
                        if isinstance(profile["model"], dict):
                            model_display = profile["model"].get("nickname", "unknown")
                        else:
                            model_display = str(profile["model"])

                    status = "✓" if enabled else "✗"
                    profiles.append(f"  {status} {yaml_file.name:<45} [{model_display:<20}]")
        except Exception as e:
            profiles.append(f"  ✗ {yaml_file.name:<45} - Error loading: {e}")

    return profiles


def _apply_model_config(config: Dict[str, Any], profile: Dict[str, Any]) -> None:
    """Apply model configuration from profile."""
    if "model" not in profile:
        return

    model_config = profile["model"]

    if isinstance(model_config, dict):
        endpoint = model_config.get("endpoint")
        nickname = model_config.get("nickname", "unknown")
        capabilities = model_config.get("capabilities", {})

        if not endpoint:
            logger.error("Model endpoint not specified in profile")
            raise ValueError("Model endpoint required in profile")

        config["model"] = endpoint
        config["model_nickname"] = nickname
        config["model_capabilities"] = capabilities
    else:
        logger.error(f"Invalid model config in profile: {model_config}")
        raise ValueError("Model config must be a dictionary with 'endpoint' field")


def _apply_parameters(config: Dict[str, Any], profile: Dict[str, Any]) -> None:
    """Apply parameter settings from profile."""
    params = profile.get("parameters", {})
    for key in ("temperature", "max_tokens", "min_prompt_tokens"):
        if key in params:
            config[key] = params[key]


def _apply_pricing(config: Dict[str, Any], profile: Dict[str, Any]) -> None:
    """Apply pricing configuration from profile."""
    if "pricing" not in profile:
        logger.warning("No pricing information in profile - cost tracking disabled")
        return

    pricing = profile["pricing"]

    if "real_time" in pricing:
        config["pricing"] = pricing["real_time"]
    else:
        logger.warning("Pricing config incomplete in profile")


def _apply_cache_config(config: Dict[str, Any], profile: Dict[str, Any]) -> None:
    """Apply cache configuration from profile."""
    if "cache_config" not in config:
        return

    cache_config = config["cache_config"]
    if not cache_config.get("enabled"):
        return

    capabilities = config.get("model_capabilities", {})
    if not capabilities.get("supports_caching", False):
        model_nickname = config.get("model_nickname", "unknown")
        logger.error(f"Caching is enabled in config but model '{model_nickname}' does not support it")
        logger.error("Disable caching in openrouter_config.yaml or switch to a compatible model")
        raise ValueError(f"Model '{model_nickname}' does not support prompt caching")

    if "cache_config" in profile:
        cache_config.update(profile["cache_config"])

    if 'cache_ttl' not in cache_config:
        raise ValueError("cache_ttl must be set when cache is enabled")
    logger.info(f"Prompt caching enabled (TTL: {cache_config['cache_ttl']}) — breakpoint on the stable user prefix (scene + images)")


def apply_profile_to_config(config: Dict[str, Any], profile: Dict[str, Any]) -> None:
    """Apply profile settings to configuration dictionary.

    Args:
        config: Base configuration dictionary to update
        profile: Profile dictionary with overrides

    Note:
        This modifies config in-place
    """
    _apply_model_config(config, profile)
    _apply_parameters(config, profile)
    _apply_pricing(config, profile)
    _apply_cache_config(config, profile)

    if "metadata" in profile:
        config["profile_metadata"] = profile["metadata"]
