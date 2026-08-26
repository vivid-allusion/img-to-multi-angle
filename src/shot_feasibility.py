"""§3.5 feasibility classifier — which shots to offer and pre-tick.

Classification inputs are the template frontmatter (shot_size, azimuth_delta,
height_delta, min_source_size, transform) compared against the shot sheet.
Risk order: subtractive < lateral < novel_view.

- subtractive → Coverage, pre-ticked
- lateral     → Coverage, pre-ticked only if the bound subject(s) are
                unoccluded (Q13); scene-wide templates always pre-tick
- novel_view  → Stretch heading, never pre-ticked; ~180° reverse shots are
                only offered when the opposing subject's face is visible
"""

from dataclasses import dataclass
from typing import Dict, List, Optional

from .angle_loader import AngleTemplate
from .shot_sheet import ShotSheet

SHOT_SIZE_ORDER = {"EWS": 1, "WS": 2, "MWS": 3, "MS": 4, "MCU": 5, "CU": 6, "ECU": 7}
RISK_ORDER = {"subtractive": 0, "lateral": 1, "novel_view": 2}

HEADING_COVERAGE = "### Coverage (recommended)"
HEADING_STRETCH = "### Stretch (unlikely to match source)"


@dataclass
class ShotEntry:
    """One checkbox entry in the enriched MD."""

    label: str
    subject_ids: List[str]
    ticked: bool
    heading: str


def _worst(a: str, b: str) -> str:
    return a if RISK_ORDER[a] >= RISK_ORDER[b] else b


def classify_shot(template: AngleTemplate, sheet: ShotSheet) -> str:
    """Compute the worst-case transform class for a template vs a shot sheet."""
    risk = "subtractive"
    source_size = SHOT_SIZE_ORDER.get(sheet.shot_size)

    if template.shot_size and source_size:
        target = SHOT_SIZE_ORDER.get(template.shot_size)
        if target is not None and target < source_size:
            risk = _worst(risk, "novel_view")

    if template.azimuth_delta >= 180:
        risk = _worst(risk, "novel_view")
    elif template.azimuth_delta > 0:
        risk = _worst(risk, "lateral")

    if template.height_delta >= 2:
        risk = _worst(risk, "novel_view")
    elif template.height_delta == 1:
        risk = _worst(risk, "lateral")

    if template.min_source_size and source_size:
        min_size = SHOT_SIZE_ORDER.get(template.min_source_size)
        if min_size is not None and source_size > min_size:
            risk = _worst(risk, "lateral")

    return _worst(risk, template.transform)


def _subject_groups(template: AngleTemplate, sheet: ShotSheet) -> List[List[str]]:
    """Fan the template out over the roster: [] for scene-wide, else id lists.

    Arity-2: ordered pairs for reverse shots (the §3.5 face_visible gate is
    directional — "S1 over S2" ≠ "S2 over S1"); unordered pairs otherwise.
    """
    if not template.subject_bound:
        return [[]]

    ids = [s.id for s in sheet.subjects]
    if template.subject_arity == 1:
        return [[sid] for sid in ids]

    if template.azimuth_delta >= 180:
        return [[a, b] for a in ids for b in ids if a != b]

    pairs = []
    for i, a in enumerate(ids):
        for b in ids[i + 1:]:
            pairs.append([a, b])
    return pairs


def _subject_by_id(sheet: ShotSheet, sid: str):
    return next((s for s in sheet.subjects if s.id == sid), None)


def _pair_label(template: AngleTemplate, ids: List[str], sheet: ShotSheet) -> str:
    """Human label for one fan-out entry."""
    if not ids:
        return template.label

    if len(ids) == 1:
        subject = _subject_by_id(sheet, ids[0])
        if subject is None:
            return template.label
        return f"{template.label} — {subject.id} ({subject.description})"

    connector = "over" if template.azimuth_delta >= 180 else "and"
    return f"{template.label} — {ids[0]} {connector} {ids[1]}"


def _entry(template: AngleTemplate, ids: List[str], sheet: ShotSheet, risk: str) -> Optional[ShotEntry]:
    """Build the entry for one subject group, or None if not offered at all."""
    if risk == "novel_view":
        if template.azimuth_delta >= 180:
            if len(ids) != 2:
                return None
            target = _subject_by_id(sheet, ids[1])
            if target is None or not target.face_visible:
                return None
        return ShotEntry(
            label=_pair_label(template, ids, sheet),
            subject_ids=ids,
            ticked=False,
            heading=HEADING_STRETCH,
        )

    ticked = True
    if risk == "lateral" and template.subject_bound:
        for sid in ids:
            subject = _subject_by_id(sheet, sid)
            if subject is None or subject.occluded:
                ticked = False

    return ShotEntry(
        label=_pair_label(template, ids, sheet),
        subject_ids=ids,
        ticked=ticked,
        heading=HEADING_COVERAGE,
    )


def build_shot_entries(
    templates: Dict[str, AngleTemplate], sheet: ShotSheet
) -> List[ShotEntry]:
    """Compute the offered shot list for one shot sheet.

    Editorially relevant (families) ∩ feasible → Coverage/Stretch per §3.5.
    """
    entries: List[ShotEntry] = []
    for template in templates.values():
        if "all" not in template.families and sheet.scene_type not in template.families:
            continue

        risk = classify_shot(template, sheet)
        for ids in _subject_groups(template, sheet):
            entry = _entry(template, ids, sheet, risk)
            if entry is not None:
                entries.append(entry)

    return entries
