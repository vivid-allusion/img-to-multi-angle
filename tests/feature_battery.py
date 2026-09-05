"""Feature battery (8 checks) — the planner-retry correction acceptance criteria
from new_feature.md §3 items 1–8. Run from the repo root:

    venv/bin/python tests/feature_battery.py

Pure Python; `process_text` monkeypatched, no API calls.
"""

import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))

from src.assets import Asset
from src.md_input_parser import ParsedMdInput
from src.shot_planner import PlanRejected, _clean_json_text, plan_file
from src.shot_generator import accumulate_usage

CHECKS = []


def check(name):
    def deco(fn):
        CHECKS.append((name, fn))
        return fn
    return deco


USAGE = {
    "input_tokens": 4000,
    "output_tokens": 300,
    "cost": 0.0071,
    "cache_creation_input_tokens": 0,
    "cache_read_input_tokens": 0,
}

VALID_PLAN = {
    "subjects": [{"id": "S1", "description": "the platform overseer", "asset": None}],
    "shots": [
        {"id": "SH01", "label": "Overseer Face Close-Up", "intent": "Camera tight on the overseer's face, eyes legible.", "shot_type": "face_cu", "subject_ids": ["S1"], "grounds": []},
        {"id": "SH02", "label": "Hands Insert", "intent": "Close framing on the gloved hands knotting the rope.", "shot_type": "hands_insert", "subject_ids": ["S1"], "grounds": []},
        {"id": "SH03", "label": "Rail Depot Master", "intent": "Wide view with the overseer head to boots beside the flatcar.", "shot_type": "wide_master", "subject_ids": ["S1"], "grounds": []},
        {"id": "SH04", "label": "Platform Medium", "intent": "Waist-up framing of the overseer with the platform behind.", "shot_type": "medium_action", "subject_ids": ["S1"], "grounds": []},
        {"id": "SH05", "label": "Low-Angle Wagon Vantage", "intent": "Ground-level tilt up at the overseer next to the wagon.", "shot_type": "dynamic_vantage", "subject_ids": ["S1"], "grounds": []},
    ],
}

MISSING_FACE_CU = {
    "subjects": VALID_PLAN["subjects"],
    "shots": [s for s in VALID_PLAN["shots"] if s["shot_type"] != "face_cu"],
}

DIRTY_INTENT = {
    "subjects": VALID_PLAN["subjects"],
    "shots": [
        dict(VALID_PLAN["shots"][0], intent="Tight on the face, capturing the essence of the moment."),
        *VALID_PLAN["shots"][1:],
    ],
}

UNDECLARED_ASSET_PLAN = {
    "subjects": [{"id": "S1", "description": "the platform overseer", "asset": "A9"}],
    "shots": VALID_PLAN["shots"],
}

SCENE_MD = (
    "A snow-covered railway platform at dusk, two workers in heavy canvas coats "
    "load wooden crates onto a flatcar.\n\n"
    "![original](https://example.com/master.jpg)\n"
)


def responder(script):
    """Fake process_text replaying `script` (repeat-last). Exception entries raise."""
    calls = []

    def fn(user_content, *args, **kwargs):
        calls.append(user_content)
        entry = script[min(len(calls), len(script)) - 1]
        if isinstance(entry, Exception):
            raise entry
        return entry

    return fn, calls


def payload_text(parts) -> str:
    return " ".join(
        str(p.get("text"))
        for p in parts
        if isinstance(p, dict) and p.get("type") == "text"
    )


def make_parsed(assets=None):
    return ParsedMdInput(
        scene="A snow-covered railway platform at dusk.",
        original_image="https://example.com/master.jpg",
        ref_images=[],
        checked_shots=[],
        all_checkbox_lines=[],
        assets=assets,
    )


def patch_planner(script):
    import src.shot_planner as planner
    fake, calls = responder(script)
    planner.process_text = fake
    return calls


def run_plan(script, assets=None):
    calls = patch_planner(script)
    config = {"retry_config": {"max_retries": 2}}
    return plan_file(make_parsed(assets), "scene.md", object(), config), calls


# --- 1. missing face_cu: 3 attempts, 2nd/3rd carry the rejection reason -------------

@check("missing face_cu: 3 attempts; 2nd and 3rd request differ from 1st")
def _():
    script = [(json.dumps(MISSING_FACE_CU), USAGE)]
    calls = patch_planner(script)
    try:
        plan_file(make_parsed(), "scene.md", object(), {"retry_config": {"max_retries": 2}})
    except RuntimeError:
        pass
    else:
        raise AssertionError("expected RuntimeError after exhaustion")
    texts = [payload_text(c) for c in calls]
    assert len(texts) == 3
    assert "Your previous plan was rejected" not in texts[0]
    for t in texts[1:]:
        assert "Your previous plan was rejected" in t
        assert "face_cu" in t


# --- 2. exhaustion still exits 1 with _FAILED and no promoted output ----------------

@check("exhaustion: orchestrator exits 1, _FAILED dir, zero promoted output")
def _():
    tmp = tempfile.mkdtemp(prefix="feature_battery_")
    files_dir = Path(tmp) / "input"
    files_dir.mkdir()
    (files_dir / "scene.md").write_text(SCENE_MD, encoding="utf-8")
    out_dir = Path(tmp) / "out" / "260903_120000_run"

    import src.preflight as preflight
    import src.base_orchestrator as base

    preflight.run_preflight = lambda *a, **k: None
    base.get_api_key = lambda: "test-key"
    patch_planner([(json.dumps(MISSING_FACE_CU), USAGE)])

    from src.multi_angle_orchestrator import process_all_md_files

    try:
        process_all_md_files(
            [files_dir / "scene.md"],
            {"retry_config": {"max_retries": 2}},
            out_dir,
            files_dir,
        )
    except SystemExit as e:
        assert e.code == 1
    else:
        raise AssertionError("expected SystemExit")

    failed = out_dir.parent / f"{out_dir.name}_FAILED"
    assert failed.is_dir() and (failed / "FAILURE_REPORT.md").exists()
    assert not out_dir.exists()
    assert set(out_dir.parent.iterdir()) == {failed}


# --- 3. rejected on attempt 1, valid on attempt 2 → succeeds ------------------------

@check("retry recovers: rejected attempt 1, valid attempt 2 → run succeeds")
def _():
    script = [(json.dumps(MISSING_FACE_CU), USAGE), (json.dumps(VALID_PLAN), USAGE)]
    (sheet, entries, _), calls = run_plan(script)
    assert len(entries) == 5
    assert len(calls) == 2


# --- 4. undeclared-asset binding aborts after exactly one call ----------------------

@check("undeclared asset: exactly one call, hard abort, not PlanRejected")
def _():
    assets = [Asset(id="A1", role="character", note="the overseer", url="https://example.com/a1.jpg")]
    script = [(json.dumps(UNDECLARED_ASSET_PLAN), USAGE)]
    calls = patch_planner(script)
    try:
        plan_file(make_parsed(assets), "scene.md", object(), {"retry_config": {"max_retries": 2}})
    except PlanRejected:
        raise AssertionError("undeclared asset must NOT be a PlanRejected")
    except RuntimeError as e:
        assert "undeclared asset" in str(e)
    else:
        raise AssertionError("expected RuntimeError")
    assert len(calls) == 1


# --- 5. non-PlanRejected (auth) propagates after exactly one call --------------------

@check("auth error: propagates after exactly one call")
def _():
    script = [RuntimeError("authentication failed")]
    calls = patch_planner(script)
    try:
        plan_file(make_parsed(), "scene.md", object(), {"retry_config": {"max_retries": 2}})
    except RuntimeError as e:
        assert "authentication failed" in str(e)
    else:
        raise AssertionError("expected RuntimeError")
    assert len(calls) == 1


# --- 6. banned intent retries with the word named -----------------------------------

@check("banned intent: retry names the word and succeeds on attempt 2")
def _():
    script = [(json.dumps(DIRTY_INTENT), USAGE), (json.dumps(VALID_PLAN), USAGE)]
    (_, entries, _), calls = run_plan(script)
    assert len(entries) == 5
    assert len(calls) == 2
    retry_text = payload_text(calls[1])
    assert "essence" in retry_text
    assert "Your previous plan was rejected" in retry_text


# --- 7. usage sums all billed attempts ----------------------------------------------

@check("usage: 2 rejected + 1 accepted attempt at 0.0071 → 0.0213")
def _():
    script = [
        (json.dumps(MISSING_FACE_CU), USAGE),
        (json.dumps(MISSING_FACE_CU), USAGE),
        (json.dumps(VALID_PLAN), USAGE),
    ]
    (_, _, total_usage), _ = run_plan(script)
    assert total_usage["cost"] == 0.0213
    assert total_usage["input_tokens"] == 12000


# --- 8. _clean_json_text WARNs on fence strip, silent on bare JSON -------------------

@check("_clean_json_text: WARN on fenced JSON, silent on bare JSON")
def _():
    from loguru import logger

    warnings = []
    sink_id = logger.add(lambda msg: warnings.append(str(msg)), level="WARNING")
    try:
        assert _clean_json_text('{"a": 1}') == '{"a": 1}'
        assert warnings == [], f"unexpected WARN on bare JSON: {warnings}"
        assert _clean_json_text('```json\n{"a": 1}\n```') == '{"a": 1}'
        assert warnings and "fenced" in warnings[0]
    finally:
        logger.remove(sink_id)


# --- bonus: accumulate_usage reuse contract -----------------------------------------

@check("accumulate_usage folds a rejected plan's usage into the running total")
def _():
    total = {}
    accumulate_usage(total, USAGE)
    accumulate_usage(total, USAGE)
    assert total["cost"] == 0.0142
    assert total["input_tokens"] == 8000


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
