"""Code-side {subject} slot expansion (Q21) — the model never sees subject ids."""

from typing import List, Optional

from .exceptions import FileProcessingError
from .shot_sheet import ShotSheet

GENERIC_SUBJECT = "the main subject"
GENERIC_SUBJECT_A = "the foreground subject"
GENERIC_SUBJECT_B = "the subject beyond"


def substitute_subject(
    template_body: str, subject_ids: List[str], shot_sheet: Optional[ShotSheet]
) -> str:
    """Replace {subject}/{subject_a}/{subject_b} slots in a template body.

    Plain labels (no ids) render generic positional anchors (Q15). Bound
    labels expand to the roster description; a missing id fails fast (Q21).
    """
    if not subject_ids:
        return (
            template_body.replace("{subject}", GENERIC_SUBJECT)
            .replace("{subject_a}", GENERIC_SUBJECT_A)
            .replace("{subject_b}", GENERIC_SUBJECT_B)
        )

    roster = {s.id: s for s in shot_sheet.subjects} if shot_sheet else {}

    def description(sid: str) -> str:
        subject = roster.get(sid)
        if subject is None:
            raise FileProcessingError(f"subject '{sid}' not found in shot-sheet roster")
        return subject.description

    if len(subject_ids) == 1:
        return template_body.replace("{subject}", description(subject_ids[0]))

    return (
        template_body.replace("{subject_a}", description(subject_ids[0]))
        .replace("{subject_b}", description(subject_ids[1]))
    )
