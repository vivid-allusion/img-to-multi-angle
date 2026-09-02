"""Per-shot prompt generation: render, call, scan, retry once, accumulate.

Split out of `multi_angle_orchestrator` when the banned-word retry pushed that
module past the 250-line soft limit. The loop is one coherent unit and moves
whole.
"""

from typing import Any, Dict, List, Tuple
from openrouter import OpenRouter
from loguru import logger

from .api_client import process_text, build_system_prompt
from .banned_words import find_banned
from .exceptions import FileProcessingError
from .md_input_parser import ParsedMdInput
from .payload_builder import build_user_content
from .shot_plan import ShotEntry
from .user_message_template import render_user_message

USAGE_KEYS = (
    "input_tokens",
    "output_tokens",
    "cache_creation_input_tokens",
    "cache_read_input_tokens",
    "cost",
)

RETRY_NOTE = (
    "Your previous attempt used the forbidden word(s) {words}. Rewrite it describing "
    "only what a camera can capture — no abstract nouns, no editorialising modifiers, "
    "and no instruction to preserve or maintain anything."
)


def accumulate_usage(total: Dict[str, Any], usage: Dict[str, Any]) -> None:
    """Fold one call's usage into the running total. A retried shot really was
    billed twice, so its first attempt is counted too."""
    if not usage:
        return
    for key in USAGE_KEYS:
        total[key] = total.get(key, 0) + usage.get(key, 0)


def generate_shots(
    parsed: ParsedMdInput,
    shots_to_run: List[Tuple[ShotEntry, List[str]]],
    filename: str,
    client: OpenRouter,
    config: Dict[str, Any],
    um_template: str,
) -> Tuple[Dict[str, str], Dict[str, List[str]], Dict[str, str], Dict[str, Any]]:
    """One call per shot → (prompts, ground urls, labels, usage totals).

    Each generated prompt is scanned for forbidden words. A hit retries that
    shot once with the offending words named; a second hit aborts the run.
    """
    cache_config = config.get("cache_config", {})
    use_cache = cache_config.get("enabled", False) and len(shots_to_run) >= 2
    cache_ttl = cache_config.get("cache_ttl") if use_cache else None
    if use_cache:
        logger.info(f"Prompt caching active (TTL: {cache_ttl})")

    system_prompt = build_system_prompt(config)
    assets_by_id = {a.id: a for a in parsed.assets} if parsed.assets is not None else {}

    angle_results: Dict[str, str] = {}
    grounds_by_angle: Dict[str, List[str]] = {}
    labels_by_shot: Dict[str, str] = {}
    total_usage: Dict[str, Any] = {}

    total_shots = len(shots_to_run)
    for i, (entry, ground_ids) in enumerate(shots_to_run, 1):
        shot_id = entry.id
        logger.info(f"  [{i}/{total_shots}] {shot_id}: {entry.label}")
        user_msg = render_user_message(um_template, entry.label, entry.intent)

        if parsed.assets is None:
            shot_refs = parsed.ref_images
            ground_urls = list(parsed.ref_images)
        else:
            shot_refs = [assets_by_id[gid] for gid in ground_ids if gid in assets_by_id]
            ground_urls = [a.url for a in shot_refs]

        def call(message: str):
            user_content = build_user_content(
                scene=parsed.scene,
                original_image=parsed.original_image,
                ref_images=shot_refs,
                angle_text=message,
                cache_breakpoint=use_cache,
                cache_ttl=cache_ttl,
            )
            return process_text(user_content, client, config, system_prompt=system_prompt)

        try:
            response_text, usage_data = call(user_msg)
            hits = find_banned(response_text)
            if hits:
                logger.warning(f"  {shot_id}: forbidden word(s) {hits} — retrying once")
                accumulate_usage(total_usage, usage_data)
                retry_msg = f"{user_msg}\n\n" + RETRY_NOTE.format(words=", ".join(hits))
                response_text, usage_data = call(retry_msg)
                hits = find_banned(response_text)
                if hits:
                    raise RuntimeError(f"forbidden word(s) {hits} still present after one retry")
        except Exception as e:
            raise FileProcessingError(f"{filename} shot '{shot_id}': {e}") from e

        angle_results[shot_id] = response_text
        grounds_by_angle[shot_id] = ground_urls
        labels_by_shot[shot_id] = entry.label
        accumulate_usage(total_usage, usage_data)

    return angle_results, grounds_by_angle, labels_by_shot, total_usage
