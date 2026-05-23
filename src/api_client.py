#!/usr/bin/env python3
"""OpenRouter API wrapper for TXT processing."""

from typing import Dict, Any
from openrouter import OpenRouter
from loguru import logger
from .response_utils import extract_response_text


def build_system_prompt(config: Dict[str, Any]) -> str:
    """
    Build system prompt for OpenRouter.

    Args:
        config: Configuration dictionary with system_prompt

    Returns:
        System prompt string
    """
    system_prompt = config.get("system_prompt", "")

    logger.debug(f"System prompt from config: {len(system_prompt)} chars")
    logger.debug(f"First 100 chars of system prompt: {system_prompt[:100] if system_prompt else 'EMPTY'}")

    return system_prompt


def process_text(text_content: str, client: OpenRouter, config: Dict[str, Any], use_cache: bool = False) -> tuple[str, Dict[str, Any]]:
    """
    Send text to OpenRouter API and get response.
    
    Args:
        text_content: Text content to process
        client: OpenRouter client instance
        config: Configuration dictionary
        use_cache: Whether to mark system prompt with cache_control
    
    Returns:
        Tuple of (response text, usage data)
    """
    system = build_system_prompt(config)
    
    if use_cache:
        system_message = {
            "role": "system",
            "content": [
                {
                    "type": "text",
                    "text": system,
                    "cache_control": {"type": "ephemeral"}
                }
            ]
        }
    else:
        system_message = {"role": "system", "content": system}
    
    api_payload = {
        "model": config["model"],
        "messages": [
            system_message,
            {"role": "user", "content": text_content}
        ]
    }
    
    if "temperature" in config:
        api_payload["temperature"] = config["temperature"]
    
    if "max_tokens" in config:
        api_payload["max_tokens"] = config["max_tokens"]
    
    if "options" in config:
        for key, value in config["options"].items():
            if key not in api_payload:
                api_payload[key] = value
    
    try:
        logger.info(f"Calling API with model: {api_payload['model']}")
        if "temperature" in api_payload:
            logger.info(f"Temperature: {api_payload['temperature']}")
        if "max_tokens" in api_payload:
            logger.info(f"Max tokens: {api_payload['max_tokens']}")
        
        logger.info(f"System prompt: {len(system)} chars, User message: {len(text_content)} chars")
        
        response = client.chat.send(**api_payload)
        
        response_text = extract_response_text(response)
        
        usage_data = {}
        if hasattr(response, 'usage') and response.usage:
            usage = response.usage
            cache_read = 0
            cache_creation = 0
            if hasattr(usage, 'prompt_tokens_details') and usage.prompt_tokens_details:
                details = usage.prompt_tokens_details
                cache_read = getattr(details, 'cached_tokens', 0)
            usage_data = {
                'input_tokens': getattr(usage, 'prompt_tokens', 0),
                'output_tokens': getattr(usage, 'completion_tokens', 0),
                'cache_creation_input_tokens': cache_creation,
                'cache_read_input_tokens': cache_read
            }
        
        logger.info(f"✅ Processed text ({len(text_content)} chars) -> ({len(response_text)} chars)")
        
    except Exception as e:
        error_type = type(e).__name__
        logger.error(f"API error ({error_type}): {e}")
        raise
    
    return response_text, usage_data
