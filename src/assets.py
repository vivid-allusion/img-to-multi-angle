"""Typed reference assets (phase_1 §1.1).

The assets block declares every reference image with a role, so the planner
can bind assets to subjects and each shot can route only its grounding refs.
"""

import re
from dataclasses import dataclass
from typing import List, Optional, Tuple

from .fences import extract_fenced_block

ASSETS_FENCE = "```yaml assets"
ASSET_ID_PATTERN = re.compile(r"^A\d+$")
ASSET_ROLES = {"character", "prop", "location"}


@dataclass
class Asset:
    """One declared reference asset."""

    id: str
    role: str
    note: str
    url: str


def extract_assets_block(
    content: str, filename: str
) -> Tuple[Optional[List[Asset]], Optional[Tuple[int, int]]]:
    """Extract the ```yaml assets fenced block, if present.

    Absent fence → (None, None). Empty block → ([], fence range). Malformed
    YAML, bad id pattern, bad role, missing url, or duplicate id → ValueError
    (fail loud at parse time, before any directory exists).

    The returned fence range indexes into content.splitlines() so the caller
    can exclude the block from scene text and image scanning.
    """
    data, fence_range = extract_fenced_block(content, ASSETS_FENCE, filename, "assets")
    if fence_range is None:
        return None, None

    if data is None:
        data = []
    if not isinstance(data, list):
        raise ValueError(f"{filename}: assets block must be a YAML list of asset entries")

    assets: List[Asset] = []
    seen_ids = set()
    for entry in data:
        try:
            asset = Asset(
                id=str(entry["id"]),
                role=str(entry["role"]),
                note=str(entry.get("note") or ""),
                url=str(entry["url"]),
            )
        except (KeyError, TypeError) as e:
            raise ValueError(
                f"{filename}: asset entry must have 'id', 'role' and 'url': {entry}"
            ) from e

        if not ASSET_ID_PATTERN.match(asset.id):
            raise ValueError(
                f"{filename}: asset id '{asset.id}' must match ^A\\d+$ (e.g. A1)"
            )
        if asset.id in seen_ids:
            raise ValueError(f"{filename}: duplicate asset id '{asset.id}'")
        if asset.role not in ASSET_ROLES:
            raise ValueError(
                f"{filename}: asset '{asset.id}' role '{asset.role}' must be one of "
                f"{sorted(ASSET_ROLES)}"
            )
        seen_ids.add(asset.id)
        assets.append(asset)

    return assets, fence_range
