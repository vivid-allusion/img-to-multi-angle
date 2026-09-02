"""Banned-word scan (feature spec §4C).

An image model renders physical objects, physical light, and visible anatomy.
Words naming an atmosphere, a mood, or an editorial judgement render nothing —
they consume prompt budget and dilute the tokens that do carry an image.
"""

import re
from typing import List

# Abstract nouns, invisible qualities, and editorialising adverbs.
BANNED_WORDS = (
    "atmosphere",
    "atmospheric",
    "mood",
    "moody",
    "vibe",
    "vibes",
    "energy",
    "essence",
    "feeling",
    "feelings",
    "aura",
    "palpable",
    "tangible",
    "evident",
    "intense",
    "intensely",
    "intensity",
    "heroically",
    "grimly",
    "defiantly",
    "desperately",
    "ominously",
    "menacingly",
    "commandingly",
    "dramatically",
)

# Preservation boilerplate — "preserve character wardrobe", "maintaining the
# original look". The bare verb stays legal: "maintaining her grip on the rope"
# is a physical action, not an instruction the model cannot draw.
BOILERPLATE = (
    r"(?:preserv\w*|maintain\w*|retain\w*)\s+"
    r"(?:\w+\s+){0,3}"
    r"(?:character\w*|historical|original|period|wardrobe|identit\w*|look|appearance\w*"
    r"|same|palette|lighting|colou?r\w*|setting|environment\w*|scene|composition|details?)"
)

_PATTERN = re.compile(
    r"\b(?:" + "|".join(BANNED_WORDS) + r")\b|" + BOILERPLATE,
    re.IGNORECASE,
)


def find_banned(text: str) -> List[str]:
    """Return every banned surface form in `text`, in order of appearance."""
    return [match.group(0) for match in _PATTERN.finditer(text)]
