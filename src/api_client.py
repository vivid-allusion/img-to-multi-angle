"""OpenRouter API wrapper for multi-angle processing."""

import time
from typing import Dict, Any, List, Optional
from openrouter import OpenRouter, errors
from openrouter.utils import BackoffStrategy, RetryConfig
from loguru import logger
from .response_utils import extract_response_text

TRANSIENT_ERRORS = (
    errors.TooManyRequestsResponseError,        # 429
    errors.InternalServerResponseError,         # 500
    errors.BadGatewayResponseError,             # 502
    errors.ServiceUnavailableResponseError,     # 503
    errors.RequestTimeoutResponseError,         # 408
    errors.EdgeNetworkTimeoutResponseError,     # 524
    errors.ProviderOverloadedResponseError,     # 529
    errors.NoResponseError,
)

NO_SDK_RETRY = RetryConfig(
    "none", BackoffStrategy(500, 60000, 1.5, 3600000), False
)


def build_system_prompt(config: Dict[str, Any]) -> str:
    """Build system prompt for OpenRouter."""
    return config.get("system_prompt", "")


def _build_system_message(system: str) -> Dict[str, Any]:
    """Build system message dict. No cache_control — the system block carries no
    breakpoint (Q23); caching covers only the stable user prefix (part 4)."""
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

    return api_payload


def _extract_usage_data(response) -> Dict[str, Any]:
    """Extract token usage and the provider-reported billed cost (Q24)."""
    if not (hasattr(response, "usage") and response.usage):
        return {}

    usage = response.usage
    cache_write = 0
    cache_read = 0

    if hasattr(usage, "prompt_tokens_details") and usage.prompt_tokens_details:
        details = usage.prompt_tokens_details
        cache_write = getattr(details, "cache_write_tokens", None) or 0
        cache_read = getattr(details, "cached_tokens", None) or 0

    raw_cost = getattr(usage, "cost", None)
    cost = raw_cost if isinstance(raw_cost, (int, float)) else 0.0

    return {
        "input_tokens": getattr(usage, "prompt_tokens", 0),
        "output_tokens": getattr(usage, "completion_tokens", 0),
        "cache_creation_input_tokens": cache_write,
        "cache_read_input_tokens": cache_read,
        "cost": cost,
    }


def process_text(
    user_content: List[Dict[str, Any]],
    *,
    client: OpenRouter,
    config: Dict[str, Any],
    system_prompt: Optional[str] = None,
    skip_token_floor: bool = False,
    response_format: Optional[Dict[str, Any]] = None,
) -> tuple[str, Dict[str, Any]]:
    """Send a user message to OpenRouter and verify the response.

    Transient API errors (TRANSIENT_ERRORS) are retried with exponential
    backoff; everything else — and the response guards below — abort on the
    first failure.

    Raises:
        RuntimeError: If the response text is empty or prompt_tokens falls
            below the configured min_prompt_tokens floor. skip_token_floor
            exempts non-rewrite calls (--plan, Q4).
    """
    system = system_prompt if system_prompt else build_system_prompt(config)

    system_message = _build_system_message(system)
    api_payload = _build_api_payload(user_content, config, system_message, response_format)

    retry_config = config["retry_config"]
    transport_retries = retry_config["transport_retries"]
    delay = retry_config["backoff_base_seconds"]
    max_delay = retry_config["backoff_max_seconds"]
    # Worst case per plan step: 3 content attempts × 3 transport attempts =
    # 9 billed calls, all accumulated by accumulate_usage.
    for attempt in range(1, transport_retries + 2):
        try:
            response = client.chat.send(**api_payload, retries=NO_SDK_RETRY)
            break
        except TRANSIENT_ERRORS as e:
            if attempt > transport_retries:
                raise
            logger.warning(
                f"Transient API error ({type(e).__name__}) on attempt "
                f"{attempt}/{transport_retries + 1} — retrying in {delay}s"
            )
            time.sleep(delay)
            delay = min(delay * 2, max_delay)

    response_text = extract_response_text(response)
    usage_data = _extract_usage_data(response)

    if not response_text.strip():
        raise RuntimeError("API returned empty response text — aborting run")

    prompt_tokens = usage_data.get("input_tokens", 0)
    if not skip_token_floor:
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

    return response_text, usage_data
