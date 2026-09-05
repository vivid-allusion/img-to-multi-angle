"""Failure battery (11 checks) — exit-1 guarantees, atomic-staging residue, the
generator retry, fence strictness, and the human-less Q5 regression guard.

Run from the repo root:  venv/bin/python tests/failure_battery.py
Pure Python; API calls monkeypatched. Reconstructed per AGENTS.md
("Where the verification lives").
"""

import os
import sys
import json
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))

from src.md_input_parser import ParsedMdInput, parse_md_file
from src.shot_plan import ShotEntry
from src.shot_planner import plan_file
from src.user_message_template import load_user_message_template

CHECKS = []


def check(name):
    def deco(fn):
        CHECKS.append((name, fn))
        return fn
    return deco


USAGE = {"input_tokens": 4000, "output_tokens": 300, "cost": 0.0071}

MISSING_FACE_CU = {
    "subjects": [{"id": "S1", "description": "the overseer", "asset": None}],
    "shots": [
        {"id": "SH01", "label": "Hands Insert", "intent": "Close framing on gloved hands.", "shot_type": "hands_insert", "subject_ids": ["S1"], "grounds": []},
        {"id": "SH02", "label": "Rail Depot Master", "intent": "Wide view of the platform.", "shot_type": "wide_master", "subject_ids": ["S1"], "grounds": []},
    ],
}

DIRTY_INTENT = {
    "subjects": [{"id": "S1", "description": "the overseer", "asset": None}],
    "shots": [
        {"id": "SH01", "label": "Overseer Face", "intent": "Tight on the face, capturing the essence of the moment.", "shot_type": "face_cu", "subject_ids": ["S1"], "grounds": []},
        {"id": "SH02", "label": "Hands Insert", "intent": "Close framing on gloved hands.", "shot_type": "hands_insert", "subject_ids": ["S1"], "grounds": []},
        {"id": "SH03", "label": "Wide Master", "intent": "Wide view of the platform.", "shot_type": "wide_master", "subject_ids": ["S1"], "grounds": []},
    ],
}

HUMANLESS = {
    "subjects": [],
    "shots": [
        {"id": "SH01", "label": "Front Grille Insert", "intent": "Camera tight on the front fascia and badge.", "shot_type": "object_insert", "subject_ids": [], "grounds": []},
        {"id": "SH02", "label": "Rear Three-Quarter", "intent": "Low angle from the rear corner.", "shot_type": "dynamic_vantage", "subject_ids": [], "grounds": []},
    ],
}

SCENE_MD = (
    "A snow-covered railway platform at dusk, two workers in heavy canvas coats "
    "load wooden crates onto a flatcar.\n\n"
    "![original](https://example.com/master.jpg)\n"
)


def responder(script):
    """Fake process_text: replays `script`, repeating the last entry forever.
    An Exception entry is raised instead of returned."""
    calls = []

    def fn(user_content, *args, **kwargs):
        calls.append(user_content)
        entry = script[min(len(calls), len(script)) - 1]
        if isinstance(entry, Exception):
            raise entry
        return entry

    return fn, calls


def make_parsed():
    return ParsedMdInput(
        scene="A snow-covered railway platform at dusk.",
        original_image="https://example.com/master.jpg",
        ref_images=[],
        checked_shots=[],
        all_checkbox_lines=[],
    )


def run_orchestrator(script):
    """Run process_all_md_files with the planner's API faked; return (exit_code, out_dir)."""
    tmp = tempfile.mkdtemp(prefix="failure_battery_")
    files_dir = Path(tmp) / "input"
    files_dir.mkdir()
    (files_dir / "scene.md").write_text(SCENE_MD, encoding="utf-8")
    out_dir = Path(tmp) / "out" / "260903_120000_run"

    import src.preflight as preflight
    import src.shot_planner as planner
    import src.base_orchestrator as base

    preflight.run_preflight = lambda *a, **k: None
    base.get_api_key = lambda: "test-key"
    fake, _ = responder(script)
    planner.process_text = fake

    from src.multi_angle_orchestrator import process_all_md_files

    code = None
    try:
        process_all_md_files(
            [files_dir / "scene.md"],
            {"retry_config": {"max_retries": 2}},
            out_dir,
            files_dir,
        )
    except SystemExit as e:
        code = e.code
    return code, out_dir


def _failed_dir(out_dir: Path) -> Path:
    return out_dir.parent / f"{out_dir.name}_FAILED"


# --- orchestrator: plan rejections abort the run with exit 1 -----------------------

@check("exit 1: plan missing face_cu exhausts retries and aborts")
def _():
    code, _ = run_orchestrator([(json.dumps(MISSING_FACE_CU), USAGE)])
    assert code == 1, f"expected exit 1, got {code}"


@check("exit 1: dirty planner intent exhausts retries and aborts")
def _():
    code, _ = run_orchestrator([(json.dumps(DIRTY_INTENT), USAGE)])
    assert code == 1, f"expected exit 1, got {code}"


@check("exit 1: missing-face_cu case leaves a _FAILED dir")
def _():
    _, out_dir = run_orchestrator([(json.dumps(MISSING_FACE_CU), USAGE)])
    failed = _failed_dir(out_dir)
    assert failed.is_dir(), f"no _FAILED dir at {failed}"
    assert (failed / "FAILURE_REPORT.md").exists()


@check("exit 1: missing-face_cu case promotes zero output")
def _():
    _, out_dir = run_orchestrator([(json.dumps(MISSING_FACE_CU), USAGE)])
    assert not out_dir.exists()
    assert set(out_dir.parent.iterdir()) == {_failed_dir(out_dir)}


@check("exit 1: dirty-intent case leaves a _FAILED dir")
def _():
    _, out_dir = run_orchestrator([(json.dumps(DIRTY_INTENT), USAGE)])
    assert _failed_dir(out_dir).is_dir()


@check("exit 1: dirty-intent case promotes zero output")
def _():
    _, out_dir = run_orchestrator([(json.dumps(DIRTY_INTENT), USAGE)])
    assert not out_dir.exists()
    assert set(out_dir.parent.iterdir()) == {_failed_dir(out_dir)}


# --- generator: banned-word retry ---------------------------------------------------

DIRTY_PROMPT = (
    "Reframe the provided image of the rail platform. Framed tight on the "
    "overseer's face, capturing the essence of the moment, gloved hands hauling "
    "the rope behind him."
)
CLEAN_PROMPT = (
    "Reframe the provided image of the rail platform. Framed tight on the "
    "overseer's face from forehead to chin, eyes narrowed toward the flatcar, "
    "gloved hands hauling the rope behind him."
)


def run_generator(script):
    import src.shot_generator as generator

    fake, calls = responder(script)
    generator.process_text = fake
    entry = ShotEntry(
        id="SH01", label="Overseer Face", intent="Tight on the face",
        shot_type="face_cu", subject_ids=[], grounds=[],
    )
    um = load_user_message_template(ROOT / "USER-FILES/01.CONFIG/user_message.md")
    config = {"cache_config": {"enabled": False, "cache_ttl": "5m"}, "system_prompt": ""}
    return generator.generate_shots(
        make_parsed(), [(entry, [])], "scene.md", object(), config, um
    ), calls


@check("generator: prompt dirty twice raises FileProcessingError")
def _():
    from src.exceptions import FileProcessingError
    try:
        run_generator([(DIRTY_PROMPT, USAGE), (DIRTY_PROMPT, USAGE)])
    except FileProcessingError as e:
        assert "forbidden word" in str(e)
    else:
        raise AssertionError("expected FileProcessingError")


@check("generator: prompt dirty once retries and recovers clean")
def _():
    (results, _, _, total_usage), calls = run_generator([(DIRTY_PROMPT, USAGE), (CLEAN_PROMPT, USAGE)])
    assert "essence" not in results["SH01"]
    assert len(calls) == 2


@check("generator: recovered shot is billed for both attempts")
def _():
    (_, _, _, total_usage), _ = run_generator([(DIRTY_PROMPT, USAGE), (CLEAN_PROMPT, USAGE)])
    assert total_usage["input_tokens"] == 8000
    assert total_usage["cost"] == 0.0142


# --- fence strictness + human-less Q5 guard -----------------------------------------

@check("fence: bad shot_type in shot-plan block raises ValueError")
def _():
    content = (
        "scene\n\n![master](https://example.com/m.jpg)\n\n"
        "```yaml shot-plan\n- id: SH01\n  label: X\n  intent: Camera places.\n"
        "  shot_type: ultra_wide\n```\n"
    )
    path = Path("/tmp/opencode/failure_bad_type.md")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    try:
        parse_md_file(path)
    except ValueError as e:
        assert "unknown shot_type" in str(e)
    else:
        raise AssertionError("expected ValueError")


@check("Q5 guard: human-less scene passes the coverage gate")
def _():
    import src.shot_planner as planner

    fake, calls = responder([(json.dumps(HUMANLESS), USAGE)])
    planner.process_text = fake
    sheet, entries, _ = plan_file(make_parsed(), "scene.md", object(), {"retry_config": {"max_retries": 2}})
    assert len(entries) == 2
    assert len(calls) == 1


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
