"""Shared fenced-block extraction for the ```yaml blocks embedded in input MD."""

from typing import Optional, Tuple

import yaml

CLOSE_FENCE = "```"


def extract_fenced_block(
    content: str, fence_marker: str, filename: str, label: str
) -> Tuple[Optional[object], Optional[Tuple[int, int]]]:
    """Return (parsed_yaml, fence_range) for the first block with the given
    marker. Absent fence → (None, None); malformed YAML → ValueError (fail
    loud at parse time, before any directory exists).

    The returned range indexes into content.splitlines() so callers can
    exclude the block from scene text and image scanning.
    """
    lines = content.splitlines()
    fence_idx = None
    for i, line in enumerate(lines):
        if line.strip() == fence_marker:
            fence_idx = i
            break

    if fence_idx is None:
        return None, None

    block_lines = []
    end_idx = fence_idx
    for line in lines[fence_idx + 1 :]:
        end_idx += 1
        if line.strip() == CLOSE_FENCE:
            break
        block_lines.append(line)

    block_text = "\n".join(block_lines)
    try:
        data = yaml.safe_load(block_text)
    except yaml.YAMLError as e:
        raise ValueError(f"{filename}: malformed {label} block: {e}") from e

    return data, (fence_idx, end_idx)


def strip_outer_fences(text: str) -> str:
    """Drop a leading and trailing markdown code-fence line, if present."""
    lines = text.splitlines()
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].startswith("```"):
        lines = lines[:-1]
    return "\n".join(lines).strip()
