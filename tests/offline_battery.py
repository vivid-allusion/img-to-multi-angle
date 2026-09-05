"""Offline battery (43 checks) — the persistent regression net for the ban scan,
shot_type schema, fence parsing, coverage-gate logic, placeholder substitution,
few-shot quality, and prompt-asset word band.

Run from the repo root:  venv/bin/python tests/offline_battery.py
Pure Python, no API calls, no pytest. Reconstructed from the session notes in
AGENTS.md ("Where the verification lives").
"""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))

from src.banned_words import find_banned
from src.shot_plan import (
    MANDATORY_SHOT_TYPES,
    SHOT_TYPES,
    extract_shot_plan,
    shot_entries_from_list,
)
from src.md_input_parser import parse_md_file
from src.user_message_template import load_user_message_template, render_user_message

CHECKS = []


def check(name):
    def deco(fn):
        CHECKS.append((name, fn))
        return fn
    return deco


def entry(shot_id, label, intent, shot_type, subject_ids, grounds):
    return {
        "id": shot_id,
        "label": label,
        "intent": intent,
        "shot_type": shot_type,
        "subject_ids": subject_ids,
        "grounds": grounds,
    }


# --- Ban scan: known-bad prompts (the 6 documented offenders) -----------------

KNOWN_BAD = [
    "Preserve character appearances",
    "Maintain the cool twilight palette",
    "retain the original composition",
    "preserving the historical setting",
    "The mood is palpable",
    "the atmosphere feels intense",
]

for text in KNOWN_BAD:
    def _bad_factory(t=text):
        def fn():
            hits = find_banned(t)
            assert hits, f"expected a ban hit in: {t!r}"
        return fn
    CHECKS.append((f"ban scan flags: {text}", _bad_factory()))


@check("ban scan flags: capturing the essence of the scene")
def _():
    assert find_banned("capturing the essence of the scene") == ["essence"]


@check("ban scan flags: maintains character identity (conjugated verb)")
def _():
    assert find_banned("maintains character identity") == ["maintains character identity"]


@check("ban scan is case-insensitive: 'The MOOD is dark'")
def _():
    assert find_banned("The MOOD is dark") == ["MOOD"]


ALLOWED = [
    "maintaining her grip on the rope",
    "the man in the dark overcoat and wide-brimmed hat",
    "gloved hands hauling a rope taut",
    "a lantern sits on the crate between them",
    "",
]

for text in ALLOWED:
    def _allowed_factory(t=text):
        def fn():
            assert find_banned(t) == [], f"false positive on: {t!r}"
        return fn
    CHECKS.append((f"ban scan clean: {text!r}", _allowed_factory()))


# --- shot_type schema ----------------------------------------------------------

@check("shot_type: all six SHOT_TYPES accepted")
def _():
    data = [
        entry(f"SH0{i+1}", t, "Camera places for this shot.", t, [], [])
        for i, t in enumerate(SHOT_TYPES)
    ]
    entries = shot_entries_from_list(data, "x.md")
    assert [e.shot_type for e in entries] == list(SHOT_TYPES)


@check("shot_type: unknown value raises ValueError")
def _():
    data = [entry("SH01", "X", "Camera places.", "ultra_wide", [], [])]
    try:
        shot_entries_from_list(data, "x.md")
    except ValueError as e:
        assert "unknown shot_type" in str(e)
    else:
        raise AssertionError("expected ValueError")


@check("shot_type: empty stays legal for legacy fences")
def _():
    data = [{"id": "SH01", "label": "X", "intent": "Camera places."}]
    entries = shot_entries_from_list(data, "x.md")
    assert entries[0].shot_type == ""


@check("shot_type: fence with unknown shot_type raises ValueError")
def _():
    content = (
        "scene text\n\n![master](https://example.com/m.jpg)\n\n"
        "```yaml shot-plan\n- id: SH01\n  label: X\n  intent: Camera places.\n"
        "  shot_type: ultra_wide\n```\n"
    )
    try:
        extract_shot_plan(content, "x.md")
    except ValueError as e:
        assert "unknown shot_type" in str(e)
    else:
        raise AssertionError("expected ValueError")


@check("coverage gate: MANDATORY_SHOT_TYPES is exactly face_cu/hands_insert/wide_master")
def _():
    assert MANDATORY_SHOT_TYPES == frozenset({"face_cu", "hands_insert", "wide_master"})


# --- shot-plan fence round-trip -------------------------------------------------

ENRICHED_MD = """A snow-covered railway platform at dusk, two workers in heavy canvas coats load wooden crates onto a flatcar.

![original](https://example.com/master.jpg)

```yaml shot-sheet
subjects:
  - id: S1
    description: the overseer in a black wool overcoat
```

```yaml shot-plan
- id: SH01
  label: Overseer Face Close-Up
  intent: Camera tight on the overseer's face, eyes legible.
  shot_type: face_cu
  subject_ids: [S1]
  grounds: []
- id: SH02
  label: Hands Insert
  intent: Close framing on gloved hands hauling the rope.
  shot_type: hands_insert
  subject_ids: [S1]
  grounds: []
```

- [x] SH01 — Overseer Face Close-Up {}
- [ ] SH02 — Hands Insert {}

![ref](https://example.com/ref.jpg)
"""


@check("fence: absent shot-plan fence returns None")
def _():
    assert extract_shot_plan("just scene text", "x.md") is None


@check("fence: malformed YAML raises ValueError")
def _():
    content = "```yaml shot-plan\n- id: [unclosed\n```\n"
    try:
        extract_shot_plan(content, "x.md")
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError")


@check("fence: duplicate shot ids raise ValueError")
def _():
    data = [entry("SH01", "A", "i1", "face_cu", [], []), entry("SH01", "B", "i2", "hands_insert", [], [])]
    try:
        shot_entries_from_list(data, "x.md")
    except ValueError as e:
        assert "duplicate shot id" in str(e)
    else:
        raise AssertionError("expected ValueError")


@check("fence: enriched MD parses to the expected entries")
def _():
    parsed = parse_md_file(_write_tmp(ENRICHED_MD))
    assert parsed.checked_shots == ["SH01"]
    assert parsed.checked_shot_bindings == [("SH01", [])]
    assert [e.id for e in parsed.shot_entries] == ["SH01", "SH02"]
    assert [e.shot_type for e in parsed.shot_entries] == ["face_cu", "hands_insert"]
    assert parsed.shot_entries[0].label == "Overseer Face Close-Up"
    assert parsed.ref_images == ["https://example.com/ref.jpg"]


@check("fence: enriched MD re-parses identically (round-trip)")
def _():
    p1 = parse_md_file(_write_tmp(ENRICHED_MD))
    p2 = parse_md_file(_write_tmp(ENRICHED_MD))
    for a, b in zip(p1.shot_entries, p2.shot_entries):
        assert (a.id, a.label, a.intent, a.shot_type, a.subject_ids, a.grounds) == (
            b.id, b.label, b.intent, b.shot_type, b.subject_ids, b.grounds,
        )


@check("fence: legacy shot-plan without shot_type keys still parses")
def _():
    content = (
        "scene\n\n![master](https://example.com/m.jpg)\n\n"
        "```yaml shot-plan\n- id: SH01\n  label: X\n  intent: Camera places.\n```\n"
    )
    entries = extract_shot_plan(content, "x.md")
    assert entries[0].shot_type == ""


# --- coverage-gate set logic ----------------------------------------------------

@check("coverage gate: missing face_cu detected by set difference")
def _():
    proposed = {"hands_insert", "wide_master"}
    missing = MANDATORY_SHOT_TYPES - proposed
    assert missing == {"face_cu"}


@check("coverage gate: complete coverage leaves no missing set")
def _():
    proposed = {"face_cu", "hands_insert", "wide_master"}
    assert MANDATORY_SHOT_TYPES - proposed == set()


# --- placeholder substitution ----------------------------------------------------

UM_PATH = ROOT / "USER-FILES" / "01.CONFIG" / "user_message.md"


@check("placeholders: label substituted verbatim")
def _():
    rendered = render_user_message(_template(), "Face CU", "intent text")
    assert "Face CU" in rendered


@check("placeholders: intent substituted verbatim")
def _():
    rendered = render_user_message(_template(), "label text", "Tight framing on the eyes")
    assert "Tight framing on the eyes" in rendered


@check("placeholders: template contains both [Shot label] and [Shot intent]")
def _():
    t = _template()
    assert "[Shot label]" in t and "[Shot intent]" in t


@check("placeholders: rendered output has no leftover [Shot placeholders")
def _():
    rendered = render_user_message(_template(), "L", "I")
    assert "[Shot label]" not in rendered and "[Shot intent]" not in rendered


@check("placeholders: template contains no image URL (blind-model guard)")
def _():
    assert "http" not in _template()


# --- few-shot word band and cleanliness -------------------------------------------

@check("few-shot: exactly 4 rewritten prompts in system_prompt.md")
def _():
    assert len(_few_shots()) == 4


for idx in range(4):
    def _band_factory(i=idx):
        def fn():
            words = len(_few_shots()[i].split())
            assert 70 <= words <= 110, f"few-shot {i+1} has {words} words"
        return fn
    CHECKS.append((f"few-shot {idx+1}: 70–110 word band", _band_factory()))


@check("few-shot: no banned words in any rewritten prompt")
def _():
    for prompt in _few_shots():
        assert find_banned(prompt) == [], f"banned word in: {prompt[:60]}..."


@check("few-shot: no CU/MCU/OTS abbreviation leaks")
def _():
    import re
    for prompt in _few_shots():
        assert not re.search(r"\b(CU|MCU|OTS)\b", prompt), prompt


# --- prompt-asset word band: no stale 60–90 ---------------------------------------

@check("word band: '60' absent from system_prompt.md")
def _():
    assert "60" not in (ROOT / "USER-FILES/01.CONFIG/system_prompt.md").read_text()


@check("word band: '90' absent from system_prompt.md")
def _():
    assert "90" not in (ROOT / "USER-FILES/01.CONFIG/system_prompt.md").read_text()


@check("word band: '60' absent from user_message.md")
def _():
    assert "60" not in (ROOT / "USER-FILES/01.CONFIG/user_message.md").read_text()


@check("word band: '90' absent from user_message.md")
def _():
    assert "90" not in (ROOT / "USER-FILES/01.CONFIG/user_message.md").read_text()


@check("word band: both assets carry the 110 ceiling")
def _():
    sp = (ROOT / "USER-FILES/01.CONFIG/system_prompt.md").read_text()
    um = (ROOT / "USER-FILES/01.CONFIG/user_message.md").read_text()
    assert "110" in sp and "110" in um


# --- helpers ----------------------------------------------------------------------

_tmp_counter = 0


def _write_tmp(content: str) -> Path:
    global _tmp_counter
    path = Path(f"/tmp/opencode/offline_battery_{_tmp_counter}.md")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    _tmp_counter += 1
    return path


def _template() -> str:
    return load_user_message_template(UM_PATH)


def _few_shots():
    sp = (ROOT / "USER-FILES/01.CONFIG/system_prompt.md").read_text()
    return [line[2:].strip() for line in sp.splitlines() if line.startswith("> Reframe")]


def main() -> int:
    failed = []
    for name, fn in CHECKS:
        try:
            fn()
            print(f"PASS  {name}")
        except Exception as e:
            failed.append((name, e))
            print(f"FAIL  {name}: {e}")
    print(f"\n{len(CHECKS) - len(failed)}/{len(CHECKS)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
