"""Per-shot prompt generation: render, call, scan, retry once, accumulate.

Split out of `multi_angle_orchestrator` when the banned-word retry pushed that
module past the 250-line soft limit. The loop is one coherent unit and moves
whole.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union
from openrouter import OpenRouter
from loguru import logger

from .api_client import process_text, build_system_prompt
from .assets import Asset
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


@dataclass
class GenerationContext:
    """Call environment shared by every shot of one file."""

    client: OpenRouter
    config: Dict[str, Any]
    um_template: str
    system_prompt: str = ""
    use_cache: bool = False
    cache_ttl: Optional[str] = None


@dataclass
class ShotOutputs:
    """Per-file generation results: prompts, grounds, labels, usage."""

    prompts: Dict[str, str] = field(default_factory=dict)
    grounds_by_shot: Dict[str, List[str]] = field(default_factory=dict)
    labels_by_shot: Dict[str, str] = field(default_factory=dict)
    usage: Dict[str, Any] = field(default_factory=dict)


def _call_shot(
    message: str,
    refs: List[Union[str, Asset]],
    parsed: ParsedMdInput,
    ctx: GenerationContext,
) -> Tuple[str, Dict[str, Any]]:
    user_content = build_user_content(
        scene=parsed.scene,
        original_image=parsed.original_image,
        ref_images=refs,
        angle_text=message,
        cache_breakpoint=ctx.use_cache,
        cache_ttl=ctx.cache_ttl,
    )
    return process_text(user_content, client=ctx.client, config=ctx.config, system_prompt=ctx.system_prompt)


def _call_with_retry(
    message: str,
    refs: List[Union[str, Asset]],
    parsed: ParsedMdInput,
    ctx: GenerationContext,
    usage: Dict[str, Any],
    shot_id: str,
) -> Tuple[str, Dict[str, Any]]:
    """Call once; on a banned-word hit, retry once naming the words. The
    rejected attempt was billed, so its usage is folded in immediately."""
    response_text, usage_data = _call_shot(message, refs, parsed, ctx)
    hits = find_banned(response_text)
    if hits:
        logger.warning(f"  {shot_id}: forbidden word(s) {hits} — retrying once")
        accumulate_usage(usage, usage_data)
        retry_msg = f"{message}\n\n" + RETRY_NOTE.format(words=", ".join(hits))
        response_text, usage_data = _call_shot(retry_msg, refs, parsed, ctx)
        hits = find_banned(response_text)
        if hits:
            raise RuntimeError(f"forbidden word(s) {hits} still present after one retry")
    return response_text, usage_data


def generate_shots(
    parsed: ParsedMdInput,
    shots_to_run: List[Tuple[ShotEntry, List[str]]],
    filename: str,
    ctx: GenerationContext,
) -> ShotOutputs:
    """One call per shot → ShotOutputs (prompts, ground urls, labels, usage).

    Each generated prompt is scanned for forbidden words. A hit retries that
    shot once with the offending words named; a second hit aborts the run.
    """
    cache_config = ctx.config.get("cache_config", {})
    ctx.use_cache = cache_config.get("enabled", False) and len(shots_to_run) >= 2
    ctx.cache_ttl = cache_config.get("cache_ttl") if ctx.use_cache else None
    if ctx.use_cache:
        logger.info(f"Prompt caching active (TTL: {ctx.cache_ttl})")

    ctx.system_prompt = build_system_prompt(ctx.config)
    assets_by_id = {a.id: a for a in parsed.assets} if parsed.assets is not None else {}

    outputs = ShotOutputs()

    total_shots = len(shots_to_run)
    for i, (entry, ground_ids) in enumerate(shots_to_run, 1):
        shot_id = entry.id
        logger.info(f"  [{i}/{total_shots}] {shot_id}: {entry.label}")
        user_msg = render_user_message(ctx.um_template, entry.label, entry.intent)

        if parsed.assets is None:
            shot_refs = parsed.ref_images
            ground_urls = list(parsed.ref_images)
        else:
            shot_refs = [assets_by_id[gid] for gid in ground_ids if gid in assets_by_id]
            ground_urls = [a.url for a in shot_refs]

        try:
            response_text, usage_data = _call_with_retry(
                user_msg, shot_refs, parsed, ctx, outputs.usage, shot_id
            )
        except Exception as e:
            raise FileProcessingError(f"{filename} shot '{shot_id}': {e}") from e

        outputs.prompts[shot_id] = response_text
        outputs.grounds_by_shot[shot_id] = ground_urls
        outputs.labels_by_shot[shot_id] = entry.label
        accumulate_usage(outputs.usage, usage_data)

    return outputs
