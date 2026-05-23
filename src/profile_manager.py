#!/usr/bin/env python3
"""Profile management for TXT processor."""

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
    
    # Default to profile.yaml if no specific profile requested
    if not profile_name:
        profile_name = "profile.yaml"
        logger.info("No profile specified, using default profile.yaml")
    
    # Ensure .yaml extension
    if not profile_name.endswith('.yaml'):
        profile_name = f"{profile_name}.yaml"
    
    profile_path = profiles_dir / profile_name
    
    if profile_path.exists():
        logger.info(f"Loading profile: {profile_path.name}")
        with open(profile_path) as f:
            profile = yaml.safe_load(f)
            if profile and profile.get("enabled", True):
                # Log profile metadata if available
                if "metadata" in profile:
                    meta = profile["metadata"]
                    logger.info(f"Profile: {meta.get('name', 'Unknown')} v{meta.get('version', '1.0')}")
                return profile
            else:
                logger.warning(f"Profile {profile_path.name} is disabled")
                return None
    else:
        logger.error(f"Profile not found: {profile_name}")
        # List available profiles
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
                    profile_name = yaml_file.stem
                    enabled = profile.get("enabled", True)
                    
                    model_display = "unknown"
                    if "model" in profile:
                        if isinstance(profile["model"], dict):
                            model_display = profile["model"].get("nickname", "unknown")
                        else:
                            model_display = str(profile["model"])
                    
                    batch_mode = profile.get("batch_mode", False)
                    mode_str = "BATCH" if batch_mode else "REAL-TIME"
                    
                    if "metadata" in profile:
                        profile_name = profile["metadata"].get("profile_name", yaml_file.stem)
                    
                    status = "✓" if enabled else "✗"
                    profiles.append(f"  {status} {yaml_file.name:<45} [{model_display:<20}] ({mode_str})")
        except Exception as e:
            profiles.append(f"  ✗ {yaml_file.name:<45} - Error loading: {e}")
    
    return profiles


def _apply_model_config(config: Dict[str, Any], profile: Dict[str, Any]) -> None:
    """Apply model configuration from profile.
    
    Args:
        config: Base configuration dictionary to update
        profile: Profile dictionary with model settings
    """
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
        
        logger.info(f"Using model from profile: {nickname} → {endpoint}")
        
        if capabilities:
            logger.debug(f"Model capabilities: {capabilities}")
    else:
        logger.error(f"Invalid model config in profile: {model_config}")
        raise ValueError("Model config must be a dictionary with 'endpoint' field")


def _apply_parameters(config: Dict[str, Any], profile: Dict[str, Any]) -> None:
    """Apply parameter settings from profile.
    
    Args:
        config: Base configuration dictionary to update
        profile: Profile dictionary with parameter settings
    """
    if "parameters" not in profile:
        return
        
    if "temperature" in profile["parameters"]:
        config["temperature"] = profile["parameters"]["temperature"]
    if "max_tokens" in profile["parameters"]:
        config["max_tokens"] = profile["parameters"]["max_tokens"]


def _apply_batch_mode(config: Dict[str, Any], profile: Dict[str, Any]) -> None:
    """Apply batch mode configuration from profile.
    
    Args:
        config: Base configuration dictionary to update
        profile: Profile dictionary with batch mode settings
    """
    if "batch_mode" not in profile:
        return
        
    config["batch_mode"] = profile["batch_mode"]
    logger.info(f"Batch mode: {profile['batch_mode']}")
    
    if profile["batch_mode"] and "batch_config" in config:
        logger.info("Batch mode enabled - using batch settings from API config")


def _apply_pricing(config: Dict[str, Any], profile: Dict[str, Any]) -> None:
    """Apply pricing configuration from profile.
    
    Args:
        config: Base configuration dictionary to update
        profile: Profile dictionary with pricing settings
    """
    if "pricing" not in profile:
        logger.warning("No pricing information in profile - cost tracking disabled")
        return
    
    pricing = profile["pricing"]
    batch_mode = profile.get("batch_mode", False)
    
    if batch_mode and "batch" in pricing:
        config["pricing"] = pricing["batch"]
        logger.info("Using batch pricing from profile (50% discount)")
    elif "real_time" in pricing:
        config["pricing"] = pricing["real_time"]
        logger.info("Using real-time pricing from profile")
    else:
        logger.warning("Pricing config incomplete in profile")
    
    logger.debug(f"Pricing loaded: {config.get('pricing', {})}")


def _apply_cache_config(config: Dict[str, Any], profile: Dict[str, Any]) -> None:
    """Apply cache configuration from profile.
    
    Args:
        config: Base configuration dictionary to update
        profile: Profile dictionary with cache settings
    """
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
    logger.info(f"Prompt caching enabled (TTL: {cache_config['cache_ttl']})")
    logger.info("Expected savings: ~89% on system prompt tokens")


def _apply_prompt_suffix(config: Dict[str, Any], profile: Dict[str, Any]) -> None:
    """Apply prompt suffix configuration from profile.
    
    Args:
        config: Base configuration dictionary to update
        profile: Profile dictionary with prompt suffix settings
    """
    if "prompt_suffix" not in profile:
        return
        
    suffix_config = profile["prompt_suffix"]
    if isinstance(suffix_config, dict):
        if suffix_config.get("enabled", True):
            config["prompt_suffix"] = suffix_config.get("text", "")
            config["prompt_suffix_options"] = {
                "add_line_break": suffix_config.get("add_line_break", False),
                "check_existing_params": suffix_config.get("check_existing_params", True)
            }
            logger.info(f"Loaded prompt suffix: {config['prompt_suffix']}")
    else:
        config["prompt_suffix"] = profile["prompt_suffix"]


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
    _apply_batch_mode(config, profile)
    _apply_pricing(config, profile)
    _apply_cache_config(config, profile)
    _apply_prompt_suffix(config, profile)
    
    if "fields_to_remove" in profile:
        config["fields_to_remove"] = profile["fields_to_remove"]
        logger.info(f"Fields to remove from profile: {config['fields_to_remove']}")
    
    if "options" in profile:
        logger.warning("'options' section in profile is deprecated. Move settings to API config.")
        if "fields_to_remove" in profile["options"]:
            config["fields_to_remove"] = profile["options"]["fields_to_remove"]
            logger.info(f"Fields to remove from profile (legacy): {config['fields_to_remove']}")
    
    if "metadata" in profile:
        config["profile_metadata"] = profile["metadata"]
        logger.info(f"Loaded profile: {profile['metadata'].get('profile_name', 'Unknown')}")