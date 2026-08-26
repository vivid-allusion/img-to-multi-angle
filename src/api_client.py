"""OpenRouter API wrapper for multi-angle processing."""

from typing import Dict, Any, List, Optional
from openrouter import OpenRouter
from loguru import logger
from .response_utils import extract_response_text


def build_system_prompt(config: Dict[str, Any]) -> str:
    """Build system prompt for OpenRouter."""
    return config.get("system_prompt", "")


def _build_system_message(system: str, use_cache: bool) -> Dict[str, Any]:
    """Build system message dict, optionally with cache control."""
    if use_cache:
        return {
            "role": "system",
            "content": [
                {
                    "type": "text",
                    "text": system,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
        }
    return {"role": "system", "content": system}


def _build_api_payload(
    user_content: List[Dict[str, Any]],
    config: Dict[str, Any],
    system_message: Dict[str, Any],
    response_format: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build the API request payload."""
    api_payload = {
        "model": config["model"],
        "messages": [
            system_message,
            {"role": "user", "content": user_content},
        ],
    }

    if "temperature" in config:
        api_payload["temperature"] = config["temperature"]

    if "max_tokens" in config:
        api_payload["max_tokens"] = config["max_tokens"]

    if response_format:
        api_payload["response_format"] = response_format

    if "options" in config:
        for key, value in config["options"].items():
            if key not in api_payload:
                api_payload[key] = value

    return api_payload


def _extract_usage_data(response) -> Dict[str, Any]:
    """Extract token usage data from API response."""
    if not (hasattr(response, "usage") and response.usage):
        return {}

    usage = response.usage
    cache_read = 0

    if hasattr(usage, "prompt_tokens_details") and usage.prompt_tokens_details:
        details = usage.prompt_tokens_details
        cache_read = getattr(details, "cached_tokens", 0)

    return {
        "input_tokens": getattr(usage, "prompt_tokens", 0),
        "output_tokens": getattr(usage, "completion_tokens", 0),
        "cache_creation_input_tokens": 0,
        "cache_read_input_tokens": cache_read,
    }


def process_text(
    user_content: List[Dict[str, Any]],
    client: OpenRouter,
    config: Dict[str, Any],
    use_cache: bool = False,
    system_prompt: Optional[str] = None,
    skip_token_floor: bool = False,
    response_format: Optional[Dict[str, Any]] = None,
) -> tuple[str, Dict[str, Any]]:
    """Send a user message to OpenRouter and verify the response.

    Raises:
        RuntimeError: If the response text is empty or prompt_tokens falls
            below the configured min_prompt_tokens floor. skip_token_floor
            exempts non-rewrite calls (--plan, Q4).
    """
    system = system_prompt if system_prompt else build_system_prompt(config)

    system_message = _build_system_message(system, use_cache)
    api_payload = _build_api_payload(user_content, config, system_message, response_format)

    try:
        logger.info(f"Calling API with model: {api_payload['model']}")
        if "temperature" in api_payload:
            logger.info(f"Temperature: {api_payload['temperature']}")
        if "max_tokens" in api_payload:
            logger.info(f"Max tokens: {api_payload['max_tokens']}")

        logger.info(f"System prompt: {len(system)} chars, User message parts: {len(user_content)}")

        response = client.chat.send(**api_payload)

        response_text = extract_response_text(response)
        usage_data = _extract_usage_data(response)

        logger.info(f"Processed ({len(user_content)} parts) -> ({len(response_text)} chars)")

        if not response_text.strip():
            raise RuntimeError("API returned empty response text — aborting run")

        prompt_tokens = usage_data.get("input_tokens", 0)
        if skip_token_floor:
            logger.info(f"prompt_tokens ({prompt_tokens}) — floor check exempt (plan/selftest call)")
        else:
            floor = config.get("min_prompt_tokens")
            if floor is None:
                logger.warning(
                    "min_prompt_tokens is not set — token floor check skipped. "
                    "Set it to ~50% of the observed prompt_tokens after the first live run."
                )
            elif prompt_tokens < floor:
                raise RuntimeError(
                    f"prompt_tokens ({prompt_tokens}) below min_prompt_tokens floor ({floor}) — "
                    "payload regression suspected, aborting run"
                )

    except Exception as e:
        error_type = type(e).__name__
        logger.error(f"API error ({error_type}): {e}")
        raise

    return response_text, usage_data
