"""Code-side {subject} slot expansion (Q21) — the model never sees subject ids."""

import re
from typing import List, Optional

from .exceptions import FileProcessingError
from .shot_sheet import ShotSheet

SLOT_PATTERN = re.compile(r"\{subject[a-z_]*\}")

GENERIC_SUBJECT = "the main subject"
GENERIC_SUBJECT_A = "the foreground subject"
GENERIC_SUBJECT_B = "the subject beyond"


def substitute_subject(
    template_body: str, subject_ids: List[str], shot_sheet: Optional[ShotSheet]
) -> str:
    """Replace {subject}/{subject_a}/{subject_b} slots in a template body.

    Plain labels (no ids) render generic positional anchors (Q15). Bound
    labels expand to the roster description; a missing id fails fast (Q21).

    Every slot must be filled. An arity mismatch between the label and the
    template (e.g. "Two Shot — S1" against a two-subject body) would otherwise
    leave a literal "{subject_a}" in the prompt sent to the image model, so any
    surviving slot raises rather than shipping.
    """
    if not subject_ids:
        result = (
            template_body.replace("{subject}", GENERIC_SUBJECT)
            .replace("{subject_a}", GENERIC_SUBJECT_A)
            .replace("{subject_b}", GENERIC_SUBJECT_B)
        )
        return _assert_filled(result, subject_ids)

    roster = {s.id: s for s in shot_sheet.subjects} if shot_sheet else {}

    def description(sid: str) -> str:
        subject = roster.get(sid)
        if subject is None:
            raise FileProcessingError(f"subject '{sid}' not found in shot-sheet roster")
        return subject.description

    if len(subject_ids) == 1:
        result = template_body.replace("{subject}", description(subject_ids[0]))
    else:
        result = (
            template_body.replace("{subject_a}", description(subject_ids[0]))
            .replace("{subject_b}", description(subject_ids[1]))
        )

    return _assert_filled(result, subject_ids)


def _assert_filled(body: str, subject_ids: List[str]) -> str:
    """Raise if any {subject...} slot survived substitution."""
    if SLOT_PATTERN.search(body):
        leftover = sorted(set(SLOT_PATTERN.findall(body)))
        raise FileProcessingError(
            f"unexpanded subject slot(s) {leftover} after binding "
            f"{subject_ids or '[]'} — angle template and label disagree on subject count"
        )
    return body
