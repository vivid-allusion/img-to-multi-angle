## Last Session Summary (2026-09-05) — Session Close-out: Cleanup Verified, TODO Wiped

### Work done — ✅ COMPLETE
- Re-verified the cleanup batch end-to-end at close-out: 44/44, 11/11, 9/9; compileall
  clean; 32 files / 3,523 lines; 0 print()/TODO/FIXME; unused-import scan clean;
  `--list-profiles` / `--cost-only` ($0.1057, 9 files) / `--dry-run` all exit 0.
- One cosmetic fix landed: `reporting.generate_summary` no longer emits an empty
  "## Statistics" header on dry-run summaries (section is now inside the
  `processed > 0` guard).
- TODO.md wiped to 0 bytes per repo discipline — all 17 cleanup tasks were executed,
  checked off, and are recorded in the previous summary; this entry is the standing
  reference.

### Remaining known items (NOT bugs — do not schedule as refactor backlog)
- `cli_handler.py:69` uses `stats.get('skipped', 0)` / `.get('total_cost', 0.0)` —
  defensive but redundant; both keys always exist in `_empty_stats`. Optional one-line
  consistency polish.
- Live single-pass run with a real key remains the gate before any commit (unchanged).

### Git state
Uncommitted: cleanup batch (7 modified src/, deleted src/data_models.py, requirements.txt,
run.py, deleted scripts/generate_profiles.py + PROFILE_GUIDE.md) stacked on the
still-uncommitted 2026-09-05 refactor batch (31 modified src/, 2 new modules, 3 config/docs,
2 batteries). Commit awaits the owner's go.

---

## Last Session Summary (2026-09-05) — Cleanup Backlog Executed: All 17 Tasks

### Work done — ✅ COMPLETE (all 3 batteries green: 44/44, 11/11, 9/9)

The TODO.md cleanup backlog (from `USER-FILES/07.TEMP/260905_143717_cleanup_report.md`)
executed end-to-end. All 17 tasks checked off in TODO.md. `compileall` clean; 32 files /
3,523 lines (was 33 / 3,595); largest file `md_input_parser.py` 237 (soft limit 250);
0 print()/TODO/FIXME in src/; unused-import scan clean.

### Changes landed (grouped)
- **Dead config writes gone**: `_apply_prompt_suffix` (12 lines) + the `fields_to_remove`
  copy deleted from `profile_manager.py`; `SKIPPED_KEYS` now
  `{"metadata", "enabled", "min_prompt_tokens"}` (`min_prompt_tokens` stays — read at
  api_client.py:104).
- **Metadata plumbing gone**: `base_orchestrator.setup_processing` returns None (logging
  kept); `generate_processing_reports` lost its `metadata` param at both class levels
  (abstract signature synced); the two dead `metadata` dict writes deleted from
  `process_all_md_files`.
- **Honest stats**: `_process_single_file` now returns `Optional[float]` cost — `None`
  means skipped (checkboxes present, none checked → raw MD copied through);
  `process_batch` increments `stats["skipped"]` for None and `stats["processed"]` +
  `total_cost` otherwise; `stats["results"]` key deleted. `cli_handler.py:69` and
  `reporting.generate_summary` now report a real skipped count (was frozen at 0).
- **`data_models.py` deleted** (26 lines): `ProcessingResult` and `UsageData` had zero
  readers after the cost-return refactor; file removed, import dropped.
- **`calculate_cost`** lost its unused `model` param (`dry_run_estimator.py` caller synced).
- **`reporting.py`** dropped the mislabeled "Total API Calls" line (duplicated
  "Files Processed"); the avg-time line stays.
- **Dependency**: `pandas` removed from requirements.txt + run.py check (zero imports).
- **File deletions**: `scripts/generate_profiles.py` (205 lines — read nonexistent
  models.yaml, wrote deleted batch_mode), `PROFILE_GUIDE.md` (275 lines — batch-era docs).
  Rollback: `git checkout -- <path>`.
- **Housekeeping**: `src/__pycache__` swept (12 pyc files from Phase-2-deleted modules).

### Verification
- `venv/bin/python tests/{offline,failure,feature}_battery.py` → 44/44, 11/11, 9/9
- `compileall` clean; unused-import AST scan clean; 0 print()/TODO/FIXME
- Smoke: `--list-profiles`, `--cost-only` (9 files, $0.1057), `--dry-run`
  ("Processed: 0 | Skipped: 0") all exit 0
- Skipped-counter behavior verified offline (fake ParsedMdInput, all-unchecked →
  `skipped=1, processed=0, total_cost=0`, copy invoked)

### Notes for future sessions
- Live single-pass run with a real key remains the gate before any commit (unchanged).
- `TODO.md` left populated with the checked-off cleanup tasks (this session's instruction;
  wipe to 0 bytes only when the owner says so — repo discipline would normally wipe at
  session end).

### Git state
Uncommitted: this cleanup batch (7 modified src/ files: base_orchestrator,
config_validator, cost_calculator, dry_run_estimator, multi_angle_orchestrator,
profile_manager, reporting; deleted src/data_models.py; requirements.txt, run.py;
deleted scripts/generate_profiles.py + PROFILE_GUIDE.md; AGENTS.md; TODO.md), stacked
on the still-uncommitted 2026-09-05 refactor batch. Commit awaits the owner's go.

---

## Last Session Summary (2026-09-05) — Systematic Cleanup Analysis

### Work done — ✅ COMPLETE (analysis only, no src/ changes)

Systematic cleanup scan of `src/` (33 files), `tests/` (3 batteries), root tooling, and all
config assets. Full report:
`USER-FILES/07.TEMP/260905_143717_cleanup_report.md` (07.TEMP is gitignored — the actionable
items are recorded below; TODO.md wiped to 0 bytes at session end per repo discipline).

### Findings — the natural backlog for the next session (schedule in TODO.md)
1. **Dead config writes** (`profile_manager.py`): `_apply_prompt_suffix` (162-173) and the
   `fields_to_remove` block (192-193) copy profile keys into merged config that nothing reads;
   no profile supplies either key. Drop them plus the `prompt_suffix`/`fields_to_remove`
   entries in `config_validator.py:84` `SKIPPED_KEYS`.
2. **Dead metadata plumbing**: `multi_angle_orchestrator.py` `generate_processing_reports`
   takes `metadata` and never uses it (132) — fed by dead dict writes at 174/187 and
   `base_orchestrator.setup_processing`'s return value (34-38); abstract signature 72-74.
3. **Vestigial stats**: `stats["results"]` written never read; `stats["skipped"]` initialised,
   never incremented (the all-checkboxes-unchecked passthrough logs "Skipping" yet bumps
   `processed`), reported frozen at 0 by `cli_handler.py:69`. Decide increment vs delete.
4. **Unread dataclass fields**: `ProcessingResult` only `.cost` is read (`filename`,
   `output_path`, `usage` never consumed); `UsageData.filename`/`.model` set never read.
5. **Unused param**: `cost_calculator.calculate_cost(..., model)` — body never uses `model`;
   sole caller `dry_run_estimator.py:87`.
6. **Unused dependency**: `pandas` in requirements.txt + `run.py` check — zero imports in
   src/ or tests/.
7. **Stale tooling/docs**: `scripts/generate_profiles.py` (reads nonexistent
   `01.CONFIG/models.yaml`, writes deleted `batch_mode`); `PROFILE_GUIDE.md` (documents the
   deleted batch path end-to-end).
8. **Reporting label**: `reporting.py:95` says "Total API Calls" but prints
   `stats['processed']` (files). Relabel.
9. **Housekeeping**: `src/__pycache__` holds 12 pyc files from modules deleted in Phase 2
   (angle_loader, 7 batch_*, plan_output_writer, shot_feasibility, subject_binding, banned_words
   conflicted copy) — `rm -rf src/__pycache__` once.

### Verified clean — do NOT schedule as backlog
- 0 print()/TODO/FIXME/commented-out code blocks in src/; batteries' print() is allowed.
- Only env var consumed: `OPENROUTER_API_KEY` (auth.py 4-tier hierarchy) — no unused env vars.
- `openrouter_config.yaml`: all keys have read sites (max_retries → planner,
  timeout → client timeout_ms, avg_output_tokens → estimator, cache_config → gate).
- Zero exact-duplicate 5-line windows across src/ (fences.py adoption eliminated the last 3).
- No unreachable branches; no file <5 lines of actual code (smallest four all actively read).
- INFORMATIONAL ONLY (no action): 02.STANDBY's 24 profiles still carry deleted batch keys
  (218 refs); profile `capabilities.supports_thinking` carried but never read.

### Git state
Uncommitted: AGENTS.md (this entry) — working tree otherwise unchanged this session. The
2026-09-05 refactor batch (31 modified src/, 2 new modules, 3 config/docs, 2 batteries) is
still awaiting the owner's go. Live single-pass run with a real key remains the gate before
any commit.

---

## Last Session Summary (2026-09-05) — Refactor Backlog Executed: All 40 Tasks

### Work done — ✅ COMPLETE (all 3 batteries green: 44/44, 11/11, 9/9)

The full TODO.md refactor backlog (generated from
`USER-FILES/07.TEMP/260905_112717_refactor_report.md`) executed in one pass. All 40 tasks
checked off in TODO.md. `compileall` clean; every `src/*.py` ≤ 250 lines (was: shot_planner 248
at the soft limit); 0 print()/TODO/FIXME in src/; unused-import scan clean.

### New modules (2)
- `fences.py` (57) — shared `extract_fenced_block()` (find fence marker → collect block →
  yaml.safe_load → ValueError on malformed, returns parsed data + inclusive line range) and
  `strip_outer_fences()`. Adopted by `assets.py`, `shot_sheet.py`, `shot_plan.py` (3 copies
  deleted) and by `shot_planner._clean_json_text` (WARN-on-fence behavior unchanged).
- `shot_plan_spec.py` (114) — PLAN_SYSTEM_PROMPT / PLAN_INSTRUCTION / PLAN_RETRY_NOTE /
  SHOT_SHEET_SCHEMA / RESPONSE_FORMAT moved out of `shot_planner.py` (248 → 159 lines).

### High-priority fixes landed
- **Single config validator**: `config.py:_validate_required_fields` deleted; `validate_all`
  is the one required-key authority (was: two copies validating every startup).
- **Dead required keys gone**: `stream` and `processing_options.*` removed from the validator
  required sets, `FIELD_EXAMPLES`, the error-report template, and `openrouter_config.yaml`.
  `retry_config.timeout` (seconds) is now READ — it is the client `timeout_ms` source in
  `BaseOrchestrator._initialize_api_client` (previously no client timeout at all).
- **Parse-once**: `run_preflight` returns a `PreflightReport` carrying
  `parsed_files: List[(Path, ParsedMdInput)]`; `process_all_md_files` logs the report and
  threads the parsed files into `process_batch` — `parse_md_file` now runs once per file.
- **Estimator honesty**: `dry_run_estimator` zeroes plan tokens for checked-shot files
  (`AUTO_PLAN_SHOTS`/`SHOT_TOKEN_ESTIMATE` constants hoisted). Verified: checked file
  estimates 1 shot × avg_output with no plan call counted.
- **Dead API branch gone**: `_build_api_payload` no longer merges the never-set
  `config["options"]`.

### Structure refactors landed
- `parse_md_file` 117 lines/CC~27 → 81 lines/CC~13 shell over `_collect_images`,
  `_collect_scene`, `_collect_checkbox_sections`; `shot_entries_from_list` split into
  `_check_shot_id`/`_resolve_subject_ids`/`_resolve_grounds`/`_resolve_shot_type`/`_entry_from_item`
  (CC 17 → ≤3 each, all error strings byte-identical); `_parse_plan` split into
  `_check_subject_assets`/`_check_mandatory_coverage`/`_check_banned_intents`.
- `checkbox_validator` consumes `md_input_parser._parse_checkbox_line` (re-parse deleted) and
  imports `SHOT_ID_PATTERN` from `shot_plan` (duplicate constant deleted).
- `shot_generator`: `GenerationContext` + `ShotOutputs` dataclasses; `_call_shot` and
  `_call_with_retry` module-level (per-iteration closure gone); `generate_shots` 6 params → 4.
  `save_angle_outputs` 6 params → 4 (takes `ShotOutputs`).
- `build_user_content` lost the dead `shot_sheet` param (7 → 6, all keyword-friendly);
  `ParsedMdInput.shot_sheet_text` field deleted; `extract_shot_sheet` returns the sheet only.
- `_empty_stats()` helper replaces the duplicated 9-line stats dict; `stats["failed"]`/
  `stats["errors"]` keys deleted everywhere (failures raise → exit 1; `cli_handler` and
  `generate_summary` updated).
- `MultiAngleOrchestrator._resolve_shots_to_run()` extracted from `_process_single_file`
  (41 lines, CC~3); `process_batch` takes parsed files; `setup_processing` reduced to the
  dry-run helper it actually is and calls `self.setup_logging` (duplicate wrapper gone).
- `reporting.generate_summary` 5 params → `RunSummary` dataclass; COST.md reference line
  deleted; profile name lookup fixed (`profile_name`, no more "Name: Unknown"); Failed/Errors
  lines removed.

### Low-priority sweep landed
Unused imports (`main.py`, `shot_plan.py`, `shot_sheet.py`); dead params
(`get_model_display_name`, `validate_all`); pointless YAML re-raise in `validate_yaml_file`
(now returns the documented error triple); `get_output_directory` temp dance; dead local in
`list_available_profiles`; `prompt_suffix_options` write; `APIAuthenticationError`;
`ProcessingResult.success/error`; `ConfigReporter.__init__` (module-level `_EXAMPLE_VALUES`);
selftest uses `payload_builder._image_part`; stale `--plan` docstring in `__init__.py`;
unreachable `if not md_files` in `main.py`; `--profile` now resolves with or without `.yaml`
(matches `load_profile`).

### Test batteries updated (interfaces changed, behavior pins kept)
- `tests/failure_battery.py`: fake `run_preflight` now returns a real `PreflightReport` with
  parsed files; orchestrator configs carry `"timeout": 600` (client timeout reads it);
  `run_generator` drives `GenerationContext` + `ShotOutputs`.
- `tests/feature_battery.py`: same fake-preflight + timeout updates; all 9 retry-contract
  checks unchanged and green.

### Verification
- `venv/bin/python tests/{offline,failure,feature}_battery.py` → 44/44, 11/11, 9/9
- `venv/bin/python -m src.main --list-profiles` / `--cost-only` (9 files, $0.1057) /
  `--dry-run` → exit 0; dry-run summary now shows the real profile name, no COST.md line
- `parse_md_file` is the only public function still >10 CC (~13 — a deliberate section-guard
  shell; further splitting would scatter one cohesive flow)
- Live API run NOT performed this session (no `OPENROUTER_API_KEY` in env at test time) —
  the batteries are offline; a live single-pass run is the natural next-session gate before
  committing.

### Git state
Uncommitted on `master`: 31 modified `src/` files + 2 new modules, 3 modified config/docs
files (`openrouter_config.yaml`, `TODO.md`, `AGENTS.md`), 2 modified test batteries. Commit
awaits the owner's go per repo discipline. `USER-FILES/05.OUTPUT/` gained cost-estimate +
dry-run report dirs from this session's smoke tests (the 04.INPUT sha256s are untouched).

### Session close-out (2026-09-05, end of refactoring pass)
- TODO.md wiped to 0 bytes per repo discipline — all 40 backlog tasks were executed, verified,
  and are recorded above; this summary is the standing reference.
- Re-verified at wipe time: 44/44, 11/11, 9/9; compileall clean; all `src/*.py` ≤ 250 lines;
  no `processing_options`/`stream`/`prompt_suffix_options`/`shot_sheet_text`/
  `APIAuthenticationError`/`stats["failed"]` leftovers anywhere in src/.
- Remaining known items for future sessions (NOT bugs, do not schedule as refactor backlog):
  `parse_md_file` ~13 CC and `preflight._check_groundings` ~11 CC (deliberate sequential
  guard flows); `--cost-only` still excludes image input tokens (warning printed); batteries
  are offline — a live single-pass run with a real key is the gate before any commit.

---

## Last Session Summary (2026-09-05) — Refactor Analysis + TODO Wipe

### Work done — ✅ COMPLETE
Systematic refactor analysis of `src/` (33 files, 3,596 lines) + `tests/` (3 batteries, 950 lines).
Full report: `USER-FILES/07.TEMP/260905_112717_refactor_report.md` (07.TEMP is gitignored). TODO.md
wiped to 0 bytes per repo discipline — all documentation lives in AGENTS.md. No src/ changes were
made this session (analysis only). Working tree clean apart from this AGENTS.md edit.

### Report highlights — the items the next session should schedule
- **High**: duplicated required-config validation (`config.py:_validate_required_fields` vs
  `config_validator.FieldValidator` — both run every startup); no client `timeout_ms` on the
  OpenRouter client (`retry_config.timeout` is required but unread — natural wire point);
  `parse_md_file` runs twice per file (preflight + orchestrator); `--cost-only` counts a plan
  call for checked-shot files that never make one (`dry_run_estimator.py:53-57`);
  `stream`/`processing_options.*` remain mandatory dead weight in every profile.
- **Medium**: `parse_md_file` 117 lines / CC ~27 — split candidate; fence-extraction duplicated
  3× (`assets.py`, `shot_sheet.py`, `shot_plan.py`) → shared helper; checkbox parsing duplicated
  (`checkbox_validator` re-implements `md_input_parser._parse_checkbox_line`); duplicate
  `SHOT_ID_PATTERN`; duplicate 9-line stats dict in `multi_angle_orchestrator.py` (34-42 / 155-163);
  `build_user_content` 7 params incl. dead `shot_sheet` param; `shot_planner.py` at 248 lines
  (2 under the soft limit — split before the next planner edit).
- **Dead code**: unused imports (`main.py:12 short_name`, `shot_plan.py:12 logger`,
  `shot_sheet.py:8,10 Any+logger`); unused params (`get_model_display_name` model_name,
  `validate_all` config_source/profile_source); unreachable `if not md_files` (`main.py:158`);
  `APIAuthenticationError` never raised; `PreflightReport` return value discarded;
  `ProcessingResult.success/error` vestigial; stale `--plan` mention in `src/__init__.py`
  docstring; `prompt_suffix_options` written but never read.
- **Explicitly NOT flagged** (deliberate design, do not "clean up"): retry-billed usage
  accumulation, `RuntimeError` vs `PlanRejected` split, `_FAILED` residue policy, coverage gate,
  boilerplate-regex negative control "maintaining her grip on the rope".

### Git state
Uncommitted: `AGENTS.md` (this entry) + untracked `USER-FILES/07.TEMP/260905_112717_refactor_report.md`
(07.TEMP gitignored). `src/` untouched. Commit awaits the owner's go per repo discipline.

### Still open — unchanged, all re-verified true this session
- The 2026-09-04 "Still open" list stands: `shot_planner.py` 248-line split candidate;
  `retry_config.timeout`/`stream`/`processing_options.*` required but unread; no client timeout;
  `reporting.py:73` COST.md reference (nothing writes it); `reporting.py:88` "Name: Unknown";
  `stats["failed"]`/`stats["errors"]` vestigial; preflight failures surface as raw tracebacks.
- The refactor report's High/Medium items above are the natural backlog for the next session;
  schedule them in TODO.md (deliberately left blank at session end per the owner's instruction).

---

## Last Session Summary (2026-09-04) — Shot-Planner Retry That Actually Corrects Itself

### Feature Implementation — ✅ COMPLETE (verified live)

Spec `USER-FILES/07.TEMP/new_feature.md` (the commit under repair: `b258073`); design forks
Q7–Q9 resolved in `USER-FILES/07.TEMP/questions.md` — all answered option 1:
- **Q7** — live run from `/tmp` input dir (never write into `04.INPUT/`, which is read-only
  sacred space; brief item 10 named `04.INPUT/input-test.md`, a file that does not exist there)
- **Q8** — permanent verification batteries committed to `tests/` (the `/tmp` scratchpad
  batteries were lost twice already; AGENTS.md had flagged the decision)
- **Q9** — `retry_config.timeout` stays unwired this pass

### What the planner retry was (the defects fixed)
`b258073` wrapped the plan call in a 3-attempt loop that (a) sent byte-identical requests every
attempt — useless against the coverage gate and the banned-intent scan, the two content
rejections it actually hits, (b) caught `Exception`, re-firing undeclared-asset aborts and
auth/402/token-floor errors three times, and (c) discarded usage, so plan spend was invisible
(a failing plan burned ~$0.021 unreported).

### Modules Modified (2)
- `shot_planner.py` (248 lines — 2 under the soft limit, split candidate) — `PlanRejected`
  exception (the only thing the loop catches); `_parse_plan(data, parsed, filename)` helper
  raises it for all six content rejections (invalid JSON, non-object JSON, invalid shot sheet,
  invalid shot list, missing mandatory coverage, banned intent) while the undeclared-asset
  check raises plain `RuntimeError` inside it and aborts without retry ("a wrong binding is
  worse than none" — deliberately NOT a PlanRejected). `PLAN_RETRY_NOTE` appends
  `Your previous plan was rejected: {error}…` to `PLAN_INSTRUCTION` on attempts 2+;
  `build_user_content` rebuilt per attempt; `max_retries` read as
  `config["retry_config"]["max_retries"]` (direct index — the `.get(..., 2)` default was
  unreachable, `config_validator.py` requires the key); unreachable post-loop `raise` deleted;
  `_clean_json_text` now WARNs when it strips a fence (strict json_schema makes a fenced
  response a signal, not something to silently repair). Signature →
  `(ShotSheet, List[ShotEntry], Dict[str, Any])`; usage accumulated via
  `shot_generator.accumulate_usage` for **every** attempt including rejected ones (they were
  billed).
- `multi_angle_orchestrator.py` (192) — `plan_usage = {}` before the branch; auto-plan branch
  unpacks three values; after `generate_shots(...)` returns, `accumulate_usage(total_usage,
  plan_usage)`. Checked-shot path untouched (no plan call, no plan usage).

### New Test Batteries (3 — committed per Q8, run with `venv/bin/python tests/<name>.py`)
- `tests/offline_battery.py` (386 lines) — 44 checks: ban scan (9 known-bad incl. boilerplate
  regex conjugation/case-insensitivity + 5 true negatives incl. "maintaining her grip on the
  rope"), shot_type parse/reject/legacy, shot-plan fence round-trip (enriched MD re-parses
  identically), coverage-gate set logic, placeholder substitution, 4 few-shots 70–110 words
  clean with no CU/MCU/OTS leaks, no stale 60–90 band in either prompt asset
- `tests/failure_battery.py` (271) — 11 checks: exit-1 on missing face_cu / dirty planner
  intent (orchestrator level with faked plan API), `_FAILED` dir + zero promoted output for
  both, generator dirty-twice → FileProcessingError, dirty-once recovers billed for 2 calls,
  bad fence shot_type → ValueError, Q5 human-less scene still passes the gate
- `tests/feature_battery.py` (293) — 9 checks: the new retry contract (reason fed back in
  attempts 2/3, rejection text in outgoing `user_content`; exhaustion exits 1 with `_FAILED`
  and no promoted output; rejected-1st/valid-2nd succeeds; undeclared asset exactly 1 call and
  NOT a PlanRejected; auth error propagates after exactly 1 call; banned intent retries with
  the word named; 2 rejected + 1 accepted at 0.0071 → 0.0213 usage; `_clean_json_text` WARN
  only on fences; `accumulate_usage` fold)
- All three green at wrap-up: 44/44, 11/11, 9/9.

### Live Run — ALL PASSED (brief item 10 + Q7)
Copied `04.INPUT/taken-2-fight-scene.md` (3 human subjects, Backblaze image URL — HEAD-checks
200 `image/png`) to `/tmp/opencode/live_test/` and ran
`venv/bin/python -m src.main --input-dir /tmp/opencode/live_test`. Profile
`gemini-3.7-flash_temp0.2_REAL-TIME`, no retries needed, plan call ~16s.
- 6 shots: Bryan Face Close-Up, Bald Attacker Face Close-Up, Bryan Combat Medium, Baton Grip
  Insert, Courtyard Wide Master, Over-the-Shoulder Vantage — the §2 hierarchy exactly.
- All six prompts 80–98 words, zero banned words.
- **Total Cost $0.0624 — now includes the plan call** (last session's $0.0457 excluded it).
- `04.INPUT/` sha256-unchanged. Output at `05.OUTPUT/260903_221533_gemini-3.7-flash_RT_temp0.2_MULTI-ANGLE-MD/`.

### Gotchas learned this session — do not rediscover these
- **`str(dict)` is not JSON.** Fake `process_text` responses in the batteries must be
  `json.dumps(...)`; Python's `str()` emits single quotes and `json.loads` rejects them.
- **Patch the right namespaces.** `shot_planner` binds `process_text` at import →
  patch `src.shot_planner.process_text`. `generate_shots` is bound in
  `multi_angle_orchestrator` → patch there if needed. The orchestrator imports `plan_file`
  *locally inside the method*, so patching `shot_planner.process_text` lets a real plan call
  run offline. Also patch `preflight.run_preflight` (imported inside
  `process_all_md_files`) and `base_orchestrator.get_api_key` (bound at module top).
- **Batteries must `os.chdir(ROOT)`.** `MultiAngleOrchestrator.__init__` hardcodes the
  relative `Path("USER-FILES/01.CONFIG/user_message.md")` — tests run from anywhere would
  fail on the real template load.
- **Usage must accumulate inside the try, before validation.** A rejected plan was billed
  the moment `process_text` returned; `accumulate_usage` therefore runs immediately after
  the call, before `_parse_plan` can raise.
- **The undeclared-asset check lives in `_parse_plan` and raises `RuntimeError` on purpose.**
  The loop catches only `PlanRejected`, so that RuntimeError propagates after exactly one
  call — do not "clean it up" into a PlanRejected.
- **Test files may print.** The 0-`print()` rule is for `src/` only; the batteries report
  with `print`.
- The Nextcloud conflicted copy of `banned_words.py` is **gone** from `src/` this session
  (only the canonical file remains) — the stale-file-edit hazard from 2026-09-02 no longer
  applies, but keep re-reading files after writes if Nextcloud sync is active.

### Git state
Uncommitted on `master`: `src/shot_planner.py`, `src/multi_angle_orchestrator.py` modified,
`tests/` new (3 batteries), `TODO.md`, `USER-FILES/07.TEMP/questions.md` (07.TEMP is
gitignored). Commit awaits the owner's go per repo discipline. Nothing from the 2026-09-02
session was left uncommitted — it landed as `cf4d18d`, `0830f8b`, `b258073`.

### Still open — re-verified this session, all still true
- `shot_planner.py` is at 248 lines, 2 under the soft limit — the next planner edit likely
  forces a split (`_parse_plan` + prompts are the natural seam).
- `retry_config.timeout` required but unread (Q9 deliberately left); `stream` and
  `processing_options.*` required but never read — mandatory dead weight in every profile.
- No client timeout on the OpenRouter client. The SDK constructor accepts `timeout_ms`;
  `BaseOrchestrator._initialize_api_client()` does not pass it. A hung call still has
  nothing to stop it.
- `reporting.py:73` emits "See COST.md for detailed breakdown" — nothing writes COST.md.
- `reporting.py:88` prints "Name: Unknown" when profile metadata lacks a `name` key.
- `stats["failed"]` / `stats["errors"]` initialised but never incremented (vestigial by
  design — failures raise + exit 1).
- Preflight failures surface as raw tracebacks rather than a clean message + exit.
- Live-run scene for future sessions: `/tmp/opencode/live_test/taken-2-fight-scene.md` with
  its Backblaze image URL still HEAD-checking 200 `image/png` as of this session.

---



### Feature Implementation — ✅ COMPLETE (verified live)

Spec `USER-FILES/07.TEMP/new_feature.md`; design forks Q1–Q6 resolved in
`USER-FILES/07.TEMP/questions.md`. Two failures fixed: the planner covered props instead of
people (a lantern macro while the overseer stood uncovered), and prompts leaned on abstract
film jargon and preservation boilerplate that a diffusion model cannot render.

### Decisions (Q1–Q6)
- **Q1** — banned-word scan on planner intents *and* generated prompts; one retry per shot naming
  the offending words, then abort. First-hit abort would discard five good prompts and a paid
  planning call over one stray adjective.
- **Q2** — the `"Reframe the provided image of …"` opener **stays**; blocking applies after it.
  It is what tells an image-to-image model it is transforming the attached image.
- **Q3** — abstract preservation clauses deleted; identity held by naming visible specifics
  ("the ankle-length black wool overcoat"). Reference-image notes kept — they are factual
  statements about attached files and are what makes Phase-1 per-shot asset routing pay off.
- **Q4** — word band 60–90 → **70–110**. The spec's own framing clause is 24 words; the old
  ceiling would have squeezed out the setting pillar §4A makes mandatory.
- **Q5** — coverage hierarchy and the object-CU ban apply **only when human subjects exist**.
  Preserves the verified car-exterior capability (BMW M3, commit 93f6985).
- **Q6** — `shot_type` enum added to the schema; human-present plans missing mandatory coverage
  abort. A prose-only fix was the one option with direct evidence against it.

### New Modules (2)
- `banned_words.py` (57) — `BANNED_WORDS` tuple (abstract nouns, editorialising modifiers) plus a
  `BOILERPLATE` regex catching preserve/maintain/retain applied to character, wardrobe, period,
  lighting, palette, setting, or appearance across up to three intervening words. `find_banned()`
  returns matched surface forms. Flags 6/6 known-bad prompts, 0 false positives on the spec's
  ALLOWED list — including the true negative "maintaining her grip on the rope" (physical action).
- `shot_generator.py` (114) — the per-shot loop (render → build → call → scan → retry → accumulate)
  extracted from the orchestrator when the retry pushed it to 277 lines. `accumulate_usage()`
  counts a retried shot's first attempt too — it really was billed.

### Modules Modified (6)
- `shot_plan.py` (129) — `SHOT_TYPES` (6 slots) and `MANDATORY_SHOT_TYPES`
  (`face_cu`/`hands_insert`/`wide_master`); `ShotEntry.shot_type`; unknown value → ValueError at
  parse time, empty stays legal so legacy shot-plan fences still parse.
- `shot_planner.py` (188) — `shot_type` in `SHOT_SHEET_SCHEMA` properties *and* `required` (strict
  schema demands both); coverage gate scoped to `if sheet.subjects`; intent scan; PLAN_SYSTEM_PROMPT
  rewritten with the ranked hierarchy, the Q5-scoped Forbidden Focus, and an explicit human-less
  escape clause.
- `multi_angle_orchestrator.py` (277 → 190) — loop delegated to `generate_shots()`.
- `USER-FILES/01.CONFIG/system_prompt.md` — Framing Translation table (boundaries, never "CU"),
  Three Pillars, Blocking, the BANNED list, a "Holding Identity Without Boilerplate" section, and
  four new few-shots (face CU / hands insert / low-angle medium / OTS reverse) at 85–92 words each.
- `USER-FILES/01.CONFIG/user_message.md` — aligned; `[Shot label]`/`[Shot intent]` placeholders
  preserved verbatim (`render_user_message` does literal substitution).
- `dry_run_estimator.py` (105) — auto-plan branch 5 → 6 shots.

### Verification — ALL PASSED
- **Offline battery (43 checks)**: ban scan vs 6 known-bad prompts and the ALLOWED list;
  `shot_type` parse/reject/legacy; fence round-trip; coverage-gate set logic; placeholder
  substitution; few-shot word band and cleanliness; no stale 60–90 band anywhere.
- **Failure battery (11 checks)**: missing `face_cu` → exit 1; dirty planner intent → exit 1;
  prompt dirty twice → exit 1; **dirty once → retry recovers and the run completes**; bad fence
  `shot_type` → ValueError; **human-less scene still passes** (Q5 regression guard). Every
  exit-1 case left a `_FAILED` dir and zero promoted output.
- **Live run** (`google/gemini-3.7-flash`, $0.0457): 6 shots planned as Overseer Face Close-Up,
  Worker Face Close-Up, Platform Overseer Medium, Rope Binding Insert, Rail Depot Master,
  Low-Angle Wagon Vantage — the §2 hierarchy exactly. All six prompts 77–81 words, zero banned
  words, zero CU/MCU/OTS abbreviation leaks, no retries needed. `04.INPUT/` sha256-unchanged.
- **Health**: every `src/*.py` under the 250 soft limit (largest: `md_input_parser.py` 225);
  0 `print()`, 0 TODO/FIXME; compileall clean.

### Correction to an earlier summary
The 2026-08-31 entry lists `src/system_prompt.md` and `src/user_message.md`. Both live in
`USER-FILES/01.CONFIG/` — see `config.py:46` and `multi_angle_orchestrator.py:28`.

### Gotchas learned this session — do not rediscover these
- **Strict JSON schema needs a new field in two places.** `SHOT_SHEET_SCHEMA` runs with
  `strict: true` and `additionalProperties: false`, so `shot_type` had to go into the shot item's
  `properties` *and* its `required` list. Adding only `properties` makes the provider reject the
  call outright.
- **The boilerplate regex needs a word gap, not a determiner list.** The first version allowed only
  `the|all|its|their` between the verb and the noun, which caught "Preserve character appearances"
  but missed "Maintain the cool twilight palette" — adjectives intervene. A bounded
  `(?:\w+\s+){0,3}` gap fixed it and took known-bad detection from 5/6 to 6/6. The negative
  control that must keep passing: `"maintaining her grip on the rope"` is a physical action and
  must stay clean. Any future widening of that regex has to be re-checked against it.
- **Retries are billed.** `accumulate_usage()` in `shot_generator.py` folds the first, rejected
  attempt into the usage total as well. A retried shot really did cost two calls and the cost
  report should say so — do not "optimise" that away.
- **Order of work.** The banned-word scan and the coverage gate are read by everything downstream,
  so they land first; the word band must be set before the few-shot examples are authored, or the
  examples get retrofitted to a band they were not written for.

### Documentation
`README.md` rewritten this session (T18, out of brief — owner approved it mid-session). Gone: the
17-template description, the `--plan` workflow, the manual review gate, a `kimi-k2-thinking`
profile that does not exist, and the 60–90 word band. Now documents the single-pass flow, the
coverage hierarchy, the prompt-craft rules, and corrected troubleshooting rows.

### Where the verification lives — READ THIS BEFORE TOUCHING THE FEATURE
The offline battery (43 checks) and failure battery (11 checks) were written to the session
scratchpad under `/tmp` and are **gone**. They are not in the repo. There is no test directory and
no test runner in this project, which matches the manifesto's "test with real data in real
scenarios" — but it means the next change to the ban list, the coverage gate, or the retry path has
no automatic safety net. Both batteries were pure-Python with monkeypatched API calls and are
cheap to rebuild; what they covered is listed under "Verification" above. Decide whether to
reconstruct them before editing `banned_words.py`, `shot_planner.py`, or `shot_generator.py`.

### Nextcloud conflicted copy — needs a decision
`src/banned_words (conflicted copy 2026-09-02 190128).py` sits untracked in `src/`. Nextcloud
created it mid-session and it silently reverted a live edit to the boilerplate regex once, which
cost a debugging cycle — the file on disk stopped matching what had just been written. Contents
are now byte-identical to `src/banned_words.py`, so deleting it loses nothing. Left in place
because it was not created by this session's work. **If Nextcloud sync is active while editing,
expect edits to be reverted under you; re-read a file after writing it if behaviour looks stale.**

### Git state
Uncommitted on `feature/grounded-human-action-coverage`: 2 new modules (`banned_words.py`,
`shot_generator.py`), 7 modified (`shot_plan.py`, `shot_planner.py`,
`multi_angle_orchestrator.py`, `dry_run_estimator.py`, both `01.CONFIG` prompt assets,
`README.md`), plus `AGENTS.md`. Commit awaits the owner's go per repo discipline.

### Still open — re-verified 2026-09-02, all still true
- `stream`, `processing_options.*`, and `retry_config` are **required** by `config.py:57-79`
  (missing → hard fail) but never read for behaviour. Either wire them up or drop them from the
  required set; right now they are mandatory dead weight in every profile.
- No client timeout is set on the OpenRouter client. The live plan call took 98 seconds this
  session; a hung call has nothing to stop it.
- `reporting.py:73` emits "See COST.md for detailed breakdown" — nothing writes COST.md.
- `reporting.py:88` prints "Name: Unknown" when profile metadata lacks a `name` key.
- `stats["failed"]` / `stats["errors"]` are initialised in `multi_angle_orchestrator.py` (lines 36,
  41, 155, 160) and never incremented. This is now dead **by design**, not a bug: any per-file
  failure raises `FileProcessingError`, which aborts the whole run through `fail_run()` + exit 1.
  There is no partial-success path left. Delete the keys or accept them as vestigial.
- Preflight failures surface as raw tracebacks rather than a clean message + exit.

---

## Last Session Summary (2026-08-31) — Direct Multi-Angle Cinematic Reframing (Single-Pass)

### Feature Implementation — ✅ COMPLETE (verified live)

The tool was refactored into a streamlined single-command workflow (`python -m src.main`) that takes raw Markdown scene files and directly generates dynamic, cinematic multi-angle reframing prompts in one automated pass. Q1–Q4 answered (all Option 1) in `USER-FILES/07.TEMP/questions.md`.

### Core Architecture & Workflow
- **Single-Command Execution**: `python -m src.main` processes input files directly. For raw Markdown files (scene + images), it automatically executes a 2-step pipeline in one run: 1 vision analysis call to determine 5–6 bold cinematic shots + individual prompt generation calls per shot.
- **Backward Compatibility**: If an input file contains pre-existing checked shots in a `shot-plan` block, the orchestrator respects and executes only the selected shots.
- **Removed `--plan`**: Eliminated mandatory planning, manual checkbox editing, and the `--plan` CLI flag in favor of a single unified pipeline.

### Modules Modified (8) & Deleted (1)
- `src/system_prompt.md` — Removed the rigid boilerplate preservation clause; added natural consistency rules encouraging bold 3D perspective shifts and unseen camera vantage points; replaced niche few-shots with 3 prestige TV drama scenarios (kitchen dialogue, night car scene, interrogation room); word count target 60–90 words.
- `src/user_message.md` — Streamlined for clean semantic instructions focusing on shot label, intent, and scene context.
- `src/shot_planner.py` (144 lines) — `SHOT_SHEET_SCHEMA` stripped of spatial metadata clutter (coordinates, facing vectors, occlusion booleans, reasonings) down to a lean schema (`subjects` + `shots`); `PLAN_SYSTEM_PROMPT` overhauled to mandate bold prestige drama coverage.
- `src/shot_sheet.py` (129 lines) & `src/shot_plan.py` (136 lines) — Simplified dataclasses and fence parsers with clean defaults.
- `src/preflight.py` (165 lines) — Relaxed requirement for a pre-existing `shot-plan` fence so raw files pass preflight; URL reachability, asset declaration, and model vision capability checks preserved.
- `src/multi_angle_orchestrator.py` (241 lines) — Integrated automated two-step flow (dynamic shot planning + immediate per-shot prompt generation) with atomic output staging (`.staging` -> promote / `_FAILED`).
- `src/dry_run_estimator.py` (101 lines) — Updated `--cost-only` to estimate 1 planning call + 5–6 shot generation calls for raw input files.
- `src/main.py` (172 lines) — Removed `--plan` argument and simplified CLI routing.
- **Deleted `src/plan_output_writer.py`** (181 lines removed).

### Verification — ALL PASSED live
- **Live `--selftest`**: Vision verification passed against `google/gemini-3.7-flash` (red, green, blue canary orientation verified).
- **Live Single-Pass Run**: Raw markdown scene (winter smuggling operation) processed end-to-end in one command:
  - Dynamically planned 6 bold cinematic shots: Wide Establishing Profile, Low Angle Overseer Hero, Over-The-Shoulder Vantage, Dynamic 3/4 Worker Medium, Reverse Ground-Level Draft Team, Detail Insert Crate & Lantern.
  - Generated 6 high-quality reframing prompts (66–77 words), free of rigid boilerplate, fully formatted with master image embeds.
  - Staged and atomically promoted to `USER-FILES/05.OUTPUT/260831_183137_gemini-3.7-flash_RT_temp0.2_MULTI-ANGLE-MD/`.
- **Offline Battery**: Raw parsing, asset parsing, lean schema conversion, and preflight checks verified.
- **Codebase Health**: All 31 files in `src/` are under the 250-line soft limit (3,369 total lines); 0 `print()`, 0 TODO/FIXME in `src/`.

---

## Last Session Summary (2026-08-29) — Phase 2: Retire the angle templates; the planner proposes the shots

### Feature Implementation — ✅ COMPLETE (verified live)

Phase 2 (`plan/phase_2.md`) landed on `img-to-reframes` (uncommitted — commit awaits owner's go,
see "Git state"). The shot list now comes from looking at the image, not from a fixed folder of
17 templates. Q7–Q12 answered (all recommended options) in `USER-FILES/07.TEMP/questions.md`.

### New Module (1)
- `shot_plan.py` (139) — `ShotEntry` dataclass (full record per Q8: id `^SH\d+$`, label, intent,
  subject_ids, grounds, recommended, reason), `shot_entries_from_list()` (duplicate ids,
  unknown subjects vs roster, undeclared grounds vs declared assets → ValueError), and
  `extract_shot_plan()` fence parser (absent → None; malformed → ValueError). Split out of
  `shot_sheet.py` when it crossed 250 (memo rule)

### Modules Modified (13)
- `md_input_parser.py` — parses the ```yaml shot-plan fence (cross-checks roster + declared
  assets at parse time); checkbox grammar now leads with the shot id (`SH01 — CU on the woman
  {A1}`); `checked_angles`/`checked_angle_bindings` → `checked_shots`/`checked_shot_bindings`
  (shot_id, ground_ids) — subject ids live in the plan block, never in labels
- `checkbox_validator.py` — template matching deleted; self-referential validation: ticked id
  must exist in the file's shot-plan block (hard fail, Q7), duplicate ticks hard-fail, unticked
  unknown ids WARN; error messages now direct to `--plan` (§2.6 — no more add-multi-checkboxes)
- `preflight.py` — requires the shot-plan block in rewrite mode (Q7 legacy files hard-fail);
  passes shot ids to the validator; Q3/Q4 brace-vs-binding WARNs now read subject_ids from the
  plan block; Q1/Q2 grounding checks and URL/vision checks untouched
- `shot_planner.py` — json_schema extended with `shots` (id `^SH\d+$`; response-format name
  `shot_plan`); the §2.2 recommendation rule moved verbatim into PLAN_SYSTEM_PROMPT, plus
  intent-prose rules (Q9: intents are concrete descriptions, ids are metadata only); plan call
  now returns (ShotSheet, shots) and aborts on undeclared grounds / unknown subjects (Q6 pattern)
- `plan_output_writer.py` — emits shot-plan fence (full record) + `### Recommended` / neutral
  `### Possible` (Q12) checkbox sections with `SH01 — label {A1}` labels; re-plan drops prior
  shot-sheet AND shot-plan blocks; new sections insert after the last image embed or fenced
  block (canonical §2.3 order: scene, master, assets, shot-sheet, shot-plan, checkboxes)
- `user_message_template.py` + `user_message.md` — `[Dataset D — Angle template text]` replaced
  by `[Shot label]` / `[Shot intent]`; `render_user_message(template, label, intent)`;
  no-image-placeholders docstring stands
- `system_prompt.md` — rules byte-identical; few-shot inputs reshaped to label + intent
- `multi_angle_output_saver.py` — filenames `{input}_{SH01}_{label-slug}.md` (Q10); KeyError
  guard now also covers missing label entries
- `multi_angle_orchestrator.py` — per-shot rewrite calls: entry label + intent → one call;
  result key = shot id; angle_loader/subject_binding imports gone; per-shot ground routing and
  the legacy no-assets path (all refs to every shot) unchanged
- `cli_handler.py` — BatchCommand + batch submission deleted (Q11); now 113 lines
- `main.py` — `--batch-id`/`--list-batches`/`--wait` args + batch routing deleted
- `dry_run_estimator.py` — estimates one plan call + one call per ticked shot (label+intent
  tokens); files without a shot-plan block error per-file
- `config.py` / `config_validator.py` / `config_examples.py` / `config_reporter.py` /
  `profile_manager.py` / `cost_calculator.py` / `dry_run_report_formatter.py` / `reporting.py` —
  `batch_mode`, `batch_config`, `require_batch_config`, batch pricing branch all deleted
  (acceptance 9: every config key has a read site or is deleted)

### Modules/Assets Deleted (10 + 17 + 1 dir)
- `src/`: `angle_loader.py`, `shot_feasibility.py`, `subject_binding.py` + 7 batch modules
  (`batch_request_builder`, `batch_processor`, `batch_monitor`, `batch_result_parser`,
  `batch_result_saver`, `batch_formatter`, `batch_report_generator`)
- `USER-FILES/01.CONFIG/angle-templates/` — 17 template `.md` deleted; **`NEW.md` moved to
  `USER-FILES/00.KB/`** (the owner's notes, preserved)
- YAML keys: `batch_config` (openrouter_config.yaml); `batch_mode`, `pricing.batch`,
  `capabilities.context_window` + `capabilities.supports_batching` (profile)

### Questions resolved this session
Q7–Q12 (all recommended options): legacy files hard-fail → run `--plan`; shot-plan block in the
MD carries the full record (keeps Phase-1 Q3/Q4 WARNs firing); intents are concrete prose with
subject_ids as metadata; `{input}_SH01_{slug}.md` filenames; batch path deleted entirely;
neutral `### Possible` heading.

### Verification (§2.7) — ALL PASSED live where it matters
- **Live `--plan` (car exterior, BMW M3 on a palm street)**: strict json_schema accepted;
  proposed "Front Grille Insert — close-up on the front fascia, headlights, and badge" — a
  detail insert no template could express (bullet 1); SH03 "Driver Interior Shot" listed
  unticked under `### Possible` with the stated reason "Windshield reflections and dark interior
  completely obscure the driver" (bullet 2); `04.INPUT/` untouched (input was /tmp), sha-verified
- **Live rewrite run** (3 ticked shots incl. a deliberate Possible): 3/3 atomic promotion;
  prompts 85–89 words, verbatim preservation clause, no braces/placeholder/id leaks (bullet 4);
  per-shot routing: SH01/SH02 (`{}`) → master only, SH03 (`{A1}`) → master + A1 (acceptance 1);
  filenames `car_interior_SH01_vehicle_wide_shot.md` etc. (Q10); frame-composer format unchanged
  (acceptance 11)
- **Offline battery (43 checks)**: parser/validator/writer round-trips (enriched MD re-parses
  identically), duplicate ids, undeclared grounds, unknown subjects, legacy no-assets path
  (2 image parts, label+intent rendered, both embeds), `--cost-only` exit 0
- **Deliberate-failure battery (5)**: 404 URL / text/html / text-only model (deepseek-chat) /
  ticked SH99 absent from shot-plan / monkeypatched payload → all exit 1 with **zero output
  directories** (bullet 5); undeclared-ground file aborts exit 1, zero dirs (acceptance 3)
- `--selftest` PASS live; `--list-profiles`, `--dry-run` unchanged; compileall clean; 0 print(),
  0 TODO/FIXME in src/

### Git state
Phase 2 is uncommitted on `img-to-reframes` (57 changed paths staged/unstaged: 10 deleted
modules, 17 deleted template files, NEW.md rename, 14 modified files, 1 new module). Commit
awaits the owner's go per repo discipline.

### Still open (unchanged, previously archived)
- `retry_config`/`stream`/`processing_options.*` validated but never read; no client timeout
- `summary_report.md` references a COST.md nothing writes; "Profile: Unknown" in profile logs
- `stats["failed"]`/`stats["errors"]` dead paths; preflight failures surface as raw tracebacks
- `multi_angle_orchestrator.py` 274 lines (+6 this phase — pre-existing justified overage)
- `frame-composer`/`add-multi-checkboxes` external repos untouched (§2.6 note recorded)

### Next Phase
- Phase 3 — client timeout, base_orchestrator/config rename, reporting cleanup, cli_handler
  shrink (plan/phase_3.md). Entry gate met (Phase 2 verified live).

---

## Last Session Summary (2026-08-29) — Phase 1: Typed assets and per-shot reference routing

### Feature Implementation — ✅ COMPLETE (verified live)

Phase 1 of the 3-phase plan (`plan/phase_1.md`, plan_context: "finishing the reframer before
the fork") landed on `img-to-reframes` (committed at phase wrap-up). Goal met: each
shot now ships with exactly the references that ground it. Q1–Q6 answered (all option 1) in
`USER-FILES/07.TEMP/questions.md`.

### New Module (1)
- `assets.py` (98) — `Asset` dataclass (id `^A\d+$`, role ∈ character|prop|location, note, url);
  `extract_assets_block()` fence parser (absent → None; empty → []; malformed/bad id/bad role/
  missing url/duplicate id → ValueError at parse time). Split out of `md_input_parser` per the
  quantity memo (kept it at 235 ≤ 250)

### Modules Modified (8)
- `md_input_parser.py` (235) — parses the optional ```yaml assets block into `ParsedMdInput`
  (`assets: Optional[List[Asset]]`, None = no block); the fence is excluded from scene-text
  collection and image scanning (its `- id: A1` lines would otherwise pollute the scene);
  INFO log "no assets block — every shot receives all N references"; `_parse_checkbox_line`
  returns a 4th element: ground ids from a trailing `{A1, A2}` suffix (`{}` → [], absent → None);
  `checked_angle_bindings` is now (angle, subject_ids, ground_ids) triples
- `shot_sheet.py` — `ShotSubject.asset: Optional[str]`; `shot_sheet_from_dict` validates the
  `^A\d+$` pattern; `plan_output_writer` renders it back into the shot-sheet block
- `payload_builder.py` — `ref_images` now accepts `str | Asset`; marker lines say
  `Image N is asset A1 (role: character) — "note".` for assets, legacy basename wording for
  bare URLs (legacy payloads stay byte-identical — regression proof below); image-count
  invariant unchanged (compares against the handed list)
- `shot_planner.py` — plan calls send declared assets as labelled image parts; json_schema
  subject `asset` is nullable `^A\d+$`; PLAN_SYSTEM_PROMPT instructs bind-only-when-confident
  ("a wrong binding is worse than none"); after the call, any subject bound to an undeclared
  asset id aborts the plan run (`_FAILED` + exit 1) — Q6
- `plan_output_writer.py` — every checkbox label gains derived braces
  (`- [x] Close Up — S1 (woman) {A1}`, `{}` when no bindings); master never listed
- `preflight.py` (200) — `_check_groundings()`: Q1 undeclared ref → hard fail (both modes);
  Q2 braces-less label / unknown brace id / empty-assets-with-braces → hard fail naming file +
  label + id (rewrite mode); Q3/Q4 cross-check braces vs shot-sheet bindings → WARN only
  (braces authoritative); Q5 every declared asset URL HEAD-checked (unused included), dead URL
  aborts. All before any API call and before any directory exists
- `multi_angle_output_saver.py` — `save_angle_outputs()` takes per-shot `grounds_by_angle`;
  emits master + only that shot's grounds; a result with no grounding entry raises KeyError
  (no silent ref loss); legacy byte format preserved (prompt + blank + embeds)
- `multi_angle_orchestrator.py` (268, +16 — was already 252 over the soft limit, pre-existing
  justification holds) — resolves each checked label's braces → asset URLs; passes per-shot
  refs (Asset objects) to `build_user_content` and per-shot grounds to the saver; legacy path
  (no block) passes all refs exactly as before
- `checkbox_validator.py` — strips the trailing `{...}` before template-name matching (the
  Phase 1 grammar made `- [x] Wide Shot {}` spuriously invalid)

### Questions resolved this session
Q1–Q6 in `USER-FILES/07.TEMP/questions.md` (all recommended options): Q1 hard fail on
undeclared refs once an assets block exists; Q2 grounding list mandatory in asset files;
Q3 WARN-only on omitted bound assets; Q4 braces authoritative + WARN on divergence; Q5
HEAD-check all asset URLs including unused; Q6 abort `--plan` on undeclared bindings.

### Verification (§1.5) — ALL PASSED (live where it matters)
- Baseline captured pre-change (`260829_181036_...`, sha256 in /tmp/opencode/p1_baseline_sha256.txt)
- **Regression (P1-15)**: live legacy rerun → 17/17 embed-identical, same file set. Prompt
  texts differ run-to-run because the profile runs at temperature 0.2 — byte-identity across
  live runs is not achievable at temp ≠ 0. Deterministic proof instead: c35a72f parser vs new
  parser → identical output on the legacy file; **all 17 payloads byte-identical** old vs new
  code (harness in /tmp/opencode/oldpkg/)
- **Routing (P1-16)**: live, two character assets (GitHub avatars u/1 u/2 — Wikimedia 403s
  httpx HEAD, avatars return 200 image/*) — CU S1 → master+A1 only; CU S2 → master+A2 only;
  Wide Shot → master only; prompts 78–90 words, preservation clause present
- **Failure battery (P1-17)**: undeclared brace id → PreflightError exit 1; duplicate asset id
  → ValueError exit 1; zero output directories
- **--plan (P1-18)**: live on asset file → shot-sheet block carries `asset` fields, every
  label carries braces; model returned all-null bindings (random avatars vs dock scene — the
  confident-only rule doing its job; non-null brace derivation unit-verified offline);
  `04.INPUT/` sha256-identical before/after
- **Gates (P1-19)**: `--selftest` PASS live; 404 URL / text/html / text-only model (vision
  gate) / payload-integrity invariant all abort, zero output directories
- `--cost-only` ($0.0282) and `--dry-run` unchanged; compileall clean; 0 print(), no new
  TODO/FIXME; all touched files ≤ 268 lines

### Test assets note
Live tests used `--input-dir /tmp/opencode/...` — `04.INPUT/` untouched. Asset URLs for
testing: `https://avatars.githubusercontent.com/u/1?v=4` / `u/2?v=4` (200 image/* on HEAD,
unlike picsum 206 / Wikimedia 403).

### Still open (unchanged)
- `retry_config`/`stream`/`processing_options.*` validated but never read; no client timeout
- `summary_report.md` references a COST.md nothing writes; "Profile: Unknown"
- `stats["failed"]`/`stats["errors"]` dead paths; preflight failures surface as raw tracebacks
- `multi_angle_orchestrator.py` 268 lines (+16 this phase — justified, pre-existing overage)

### Next Phase
- Phase 2 — retire the fixed angle templates (`plan/phase_2.md`); deletes angle_loader,
  shot_feasibility, subject_binding, checkbox template matching. Entry gate met (Phase 1
  verified live).

---

## Last Session Summary (2026-08-29) — Post-plan review fixes

### Four defects found in review of the completed 4-phase plan — ✅ ALL FIXED

**1. Pre-ticking ignored subject visibility (the one that mattered)**
`shot_feasibility._entry()` only consulted `occluded` when `risk == "lateral"`; subtractive
shots pre-ticked unconditionally. The 260826_130445 `--plan` run therefore pre-ticked Close Up /
Extreme Close Up / Rack Focus on S3/S4/S5 — all `face_visible: false, occluded: true`. A punch-in
on a hidden, faceless figure is the exact additive case the classifier exists to avoid.
Fix: new `_pretick_ok()` applies to **any** subject-bound template — occluded subjects never
pre-tick, and tight shots (`FACE_REQUIRED_SIZES = MCU/CU/ECU`) additionally require
`face_visible`. Also fixes the C(n,2) `Two Shot` fan-out, since a pair needs both subjects usable.
Measured against the real 5-subject sheet: **31 → 8 pre-ticked, 39 still offered** (nothing
hidden, only unticked — the user can still tick anything).
NOTE: the original plan text (§3.5) only specified the visibility gate under `lateral`; the
implementation was faithful to the spec. The spec was wrong.

**2. Subject-slot arity was unvalidated → raw placeholders could reach the image model**
`checkbox_validator` verified subject ids against the roster but never against
`template.subject_arity` (the metadata existed and only the planner used it). `Two Shot — S1`
passed validation, then `substitute_subject` left literal `{subject_a}`/`{subject_b}` in the
prompt. Reverse case too (`Close Up — S1 over S2` leaves `{subject}`). Reachable via the human
edit step between `--plan` and the run.
Fix: `validate_checkboxes()` takes an optional `templates` dict and rejects arity mismatches
with a clear message; wired through `preflight.py` and `cli_handler.py` (batch path).

**3. No backstop on unexpanded slots**
Fix: `subject_binding._assert_filled()` raises `FileProcessingError` if any `{subject...}`
survives substitution, naming the leftover slots. Defence in depth behind fix 2.

**4. Dead Dataset B/C plumbing (loaded gun)**
`user_message_template.py` still held `PLACEHOLDER_DATASET_B`/`_C` and both call sites still
passed image URLs in, though `user_message.md` no longer contains those placeholders (no-op).
Re-adding the placeholder would have injected URLs as **text** alongside the real image parts —
silently resurrecting a variant of the original blind-model defect.
Fix: placeholders and params deleted; `render_user_message(template, dataset_d)` is now
two arguments, with a docstring saying why images must never be rendered here.

### Files changed (8)
`shot_feasibility.py`, `checkbox_validator.py`, `preflight.py`, `cli_handler.py`,
`subject_binding.py`, `user_message_template.py`, `multi_angle_orchestrator.py`,
`batch_request_builder.py`

### Verification (all re-run after the fixes)
- Arity: 2 mismatched labels REJECTED, 2 correct labels ACCEPTED
- Slot backstop: both mismatch directions raise; both correct bindings expand fully
- Pre-ticking: 31 → 8 on the real shot sheet, 39 offered either way
- Live end-to-end (2 angles): promoted atomically; both prompts 83 words, clause present,
  no braces, no URL-as-text
- `--selftest` PASS (live), `--list-profiles`, `--cost-only`, `--dry-run` all PASS
- Deliberate-failure tests (404 URL, text/html, payload integrity) all still abort with **zero
  output directories created**
- `compileall` clean; `cli_handler.py` now 270 lines (was 265 — still over the 250 soft limit,
  pre-existing, tracked)

### Still open (unchanged, previously archived)
- `retry_config.max_retries` / `retry_config.timeout` / `processing_options.max_response_length`
  validated but never read; no client `timeout_ms` (this is what let the cache probe hang ~20 min)
- `summary_report.md` references a `COST.md` that nothing writes; "Profile: Unknown"
- `stats["failed"]` / `stats["errors"]` are dead paths now that failures raise
- Preflight failures surface as raw tracebacks rather than a clean one-line message

---

## Last Session Summary (2026-08-26) — Phase 4: Accounting and Caching (plan complete)

### Feature Implementation — ✅ COMPLETE (verified live)
Phase 4 (`plan/phase_4.md`) landed on `feature/vision-payload-and-shot-planner`. This closes
the whole 4-phase plan. Q23/Q24 answered (both recommended options) and recorded in
`USER-FILES/07.TEMP/questions.md`; Q1–Q24 now locked.

### Modules Modified (8)
- `api_client.py` — `_extract_usage_data()` now also extracts `usage.cost` (provider-reported
  billed cost, Q24) and `prompt_tokens_details.cache_write_tokens` (was hardcoded 0);
  `process_text()` lost its `use_cache` param; `_build_system_message()` always emits a plain
  string system message — no system-message cache_control (Q23)
- `multi_angle_orchestrator.py` (252 — 2 over the soft limit; justified: §4.1/§4.4 mandate the
  per-call accumulation loop and per-file cache gate live here, splitting would scatter one
  cohesive flow) — §4.1: per-call usage now ACCUMULATES (`input/output/cache_creation/
  cache_read/cost` summed, was `total_usage = usage_data` ≈ 1/17th of actual); realtime cost is
  now the summed `usage.cost` (Q24) — `calculate_cost` import removed; §4.4: cache gate moved
  per file onto `len(parsed.checked_angles) >= 2` (was all 17 templates), `cache_breakpoint`
  + `cache_ttl` passed into `build_user_content`
- `payload_builder.py` — `cache_ttl` param; breakpoint marker emits
  `{"type": "ephemeral", "ttl": ...}`; breakpoint without ttl → `ValueError` (fail fast)
- `config_validator.py` — deleted `cache_system_prompt`/`report_cache_metrics` from the
  enabled-cache requirements (Q12); `cache_ttl` literal-validated against `5m`/`1h` (§4.3)
- `config_examples.py` / `openrouter_config.yaml` — the two dead keys deleted; yaml keeps
  `cache_config: {enabled: false, cache_ttl: 5m}`
- `preflight.py` — `_warn_dead_cache_keys()` deleted (the keys are gone, not just unread)
- `profile_manager.py` — stale "~89% on system prompt tokens" log replaced (no system
  breakpoint anymore)
- `cost_calculator.py` — dead `UsageStats` class deleted; survives only for `--cost-only`
  estimates and the batch path (Q24)
- `shot_planner.py` — call site updated for the `process_text` signature change

### Cache measurement (§4.5 — verify, don't assume) — caching does NOT pay
Reference file, 17 ticked angles, identical payloads:
- Cache OFF: **$0.0770, 192.7 s** | Cache ON: **$0.0814, 174.8 s** → caching costs ~5.7% MORE
- Probe evidence: first cached call writes 4559 tokens (image-heavy prefix) at the cache-write
  premium; 16 reads don't offset it for gemini-3.7-flash on OpenRouter
- Two cache-on runs hung ~20 min on the first cached call (provider-side stall with
  `cache_control` present; probes with `timeout_ms` completed fine minutes later)
- Per §4.5: `cache_config.enabled` left **false**; measurement recorded here and in TODO
- The plumbing stays: if a future model shows read discounts beating the write premium, flipping
  `enabled: true` is the whole config change

### Verification
- `--selftest` PASS (live); baseline live run 17/17, atomic promotion, $0.0770 provider-reported
- Accumulation unit-checked offline (17 fake calls → correct sums incl. cost)
- `_extract_usage_data` unit-checked incl. None/UNSET cost and missing details
- `--cost-only` ($0.0282, image-token warning intact), `--list-profiles`, `--dry-run` all OK
- Acceptance 7 met: per-file cost is now the true sum of its angle calls (was ~1/17th)
- Acceptance 8: all five §0.3 dead-key defects resolved (3 cache keys + cache pricing + usage)

### Questions resolved this session
Q23 (drop the system-prompt breakpoint — cache only the stable user prefix) and Q24 (trust
`usage.cost` for real-run reports; local pricing survives only for `--cost-only`; no `cache`
pricing block). Both recommended options, both locked.

### TODO archived at wrap-up (then wiped)
- `retry_config`/`stream`/`processing_options.*` validated but never read; OpenRouter client
  built with no `timeout_ms` (the 20-min cache hang is the observed cost — needs its own task)
- `summary_report.md` references COST.md that nothing writes
- Batch path keeps local `calculate_cost` with the §4.2 double-count + pre-Q23 system
  cache_control — standby per Q5, needs its own task if batch is revived

### Git state
Phase 4 committed to `feature/vision-payload-and-shot-planner` (see git log). The 4-phase plan
is complete — no next phase.

### Codebase Stats (as of 2026-08-26, post-Phase 4)
- 40 Python files in `src/`, 4,879 total lines (net −40 vs Phase 3)
- 0 syntax errors, 0 print(), 0 TODO/FIXME in src/
- Over 250-line soft limit: `cli_handler.py` (265, pre-existing known), `multi_angle_orchestrator.py`
  (252, justified above)

---

## Last Session Summary (2026-08-26) — Phase 3: Adaptive Shot Planning

### Feature Implementation — ✅ COMPLETE (all tasks verified against live API)
Phase 3 (`plan/phase_3.md`) landed on `feature/vision-payload-and-shot-planner` (uncommitted —
commit awaits owner's go, see "Git state"). Q19–Q22 answered and recorded in
`USER-FILES/07.TEMP/questions.md`; Q1–Q18 already locked.

### New Modules (5)
- `shot_sheet.py` (118) — `ShotSheet`/`ShotSubject`/`ShotProp` dataclasses (schema §3.3 + Q13
  `occluded`), `extract_shot_sheet()` fence parser (absent → None; malformed → ValueError per Q22),
  `shot_sheet_from_dict()`. Split out of `md_input_parser.py` when it hit 305 lines (now 201)
- `shot_planner.py` (167) — `--plan` core: strict json_schema `SHOT_SHEET_SCHEMA`
  (subject `id` constrained to `^S[0-9]+$` — unconstrained, the model returned free-form ids
  like `man_in_coat`, which the checkbox grammar cannot bind), `plan_file()` (reuses
  `build_user_content` + `process_text` with `skip_token_floor=True` per Q4), `run_plan_mode()`
  (preflight plan_mode → staging → atomic promotion; failure → `_FAILED` + exit 1 per Q16)
- `shot_feasibility.py` (160) — §3.5 classifier: worst-case risk from size scale
  (EWS(1)..ECU(7), target wider → novel_view), azimuth (0/≤30/90→lateral, 180→novel_view +
  opposing-face `face_visible` gate), height (0/1/≥2 steps), `min_source_size` one-step
  demotion, author `transform` floor. Pre-tick: subtractive → ticked; lateral → ticked iff
  bound subjects unoccluded (Q13); novel_view → Stretch unticked. Families gate: template not
  in the scene type's families → not shown at all
- `plan_output_writer.py` (128) — enriched MD: verbatim copy, checkbox section (+ headings +
  prior shot-sheet block) replaced by shot-sheet fence + `### Coverage (recommended)` +
  `### Stretch (unlikely to match source)`; inserted after the last image embed when no
  checkbox section exists (Q19)
- `subject_binding.py` (42) — code-side `{subject}`/`{subject_a}`/`{subject_b}` expansion
  (Q21): roster descriptions, generic anchors for plain labels ("the main subject" /
  "the foreground subject" / "the subject beyond"), missing id → `FileProcessingError`

### Modules Modified (10)
- `angle_loader.py` — `AngleTemplate` dataclass + `load_angle_template_objects()` (YAML
  frontmatter, permissive defaults for frontmatter-less `.txt`), globs `*.md`+`*.txt`, skips
  `NEW.md`; `load_angle_templates()` kept as body-dict legacy API
- `md_input_parser.py` — `ParsedMdInput` + `shot_sheet`, `shot_sheet_text`,
  `checked_angle_bindings`; checkbox labels split on " — " into angle + `S\d+` ids (Q15)
- `checkbox_validator.py` — dual grammar: plain labels vs angle names; suffixed labels also
  vs roster (no ids / no roster / unknown id → hard-fail, unchanged strictness)
- `multi_angle_orchestrator.py` — iterates `checked_angle_bindings`, substitutes slots before
  the call, passes `shot_sheet_text` into `build_user_content`; result keys `Angle_S1` so
  bound shots get distinct output files
- `api_client.py` — `process_text(skip_token_floor, response_format)`; plan calls exempt the
  2078 floor (Q4), json_schema passed through to the payload
- `preflight.py` — `plan_mode` skips checkbox validation only; rewrite mode passes roster to
  validation; URL/vision/config checks unchanged for both modes
- `main.py` — `--plan` flag → `run_plan_mode` with `SHOT-PLAN` suffix
- `cli_handler.py` — batch submission passes roster (suffixed labels no longer spurious-fail);
  batch binding fan-out stays out of scope per Q5
- `dry_run_estimator.py` — plan call folded into `--cost-only` (§3.8): PLAN_INSTRUCTION input
  + one avg_output per file
- `preflight.py`/`payload_builder.py` — unchanged API; payload part-1 carries scene + shot
  sheet text as wired in Phase 1

### Template assets
- All 17 templates converted `.txt` → `.md` with frontmatter (§3.4): `id`, `label`,
  `families` (transcribed from NEW.md, spelling normalised — Q14; `NEW.md` untouched and
  skipped), `transform`, `min_source_size`, `subject_bound`, `subject_arity` (Q20),
  `azimuth_delta`/`height_delta` (Q8), plus `shot_size` — a required completion: §3.5's
  "target vs source" rule needs a per-template target size, and Q8's schema had no field
  for it. Subject-bound bodies address `{subject}`/`{subject_a}`/`{subject_b}`; prose
  otherwise identical to Phase 2
- Family authoring highlights: OTS/Two_Shot bound with arity 2 (ordered pairs for reverse
  shots — the face_visible gate is directional; unordered otherwise); POV floored to
  novel_view (it asks the image model to invent the character's view — exactly the
  additive-geometry failure the plan exists to kill); Birds_Eye height_delta 2 → never
  pre-ticked from ground sources

### Plan-vs-rules decision (documented)
§3.7's format example pre-ticks "Over The Shoulder — S1 over S2" under Coverage while §3.5
says 180° reverse → novel_view → never pre-ticked (and the example's own shot sheet has the
opposing subject face_visible=false). §3.5 rules win — the example is a format illustration,
acceptance 6 is the binding text.

### Verification (§3.9) — ALL PASSED on live runs
- `--plan` live ×3: strict json_schema accepted; atomic promotion; outputs at
  `USER-FILES/05.OUTPUT/260826_125901/130003/130445_..._SHOT-PLAN/` (125901 deleted after the
  id-pattern fix). Scene classification varied (vehicle_exterior → dialogue_3plus) at temp 0.2
  — expected model variance, both defensible for the 5-person train-yard scene
- Rewrite pipeline on enriched MD live: 7/7 ticked shots, bound descriptions substituted
  ("the man in the dark overcoat and wide-brimmed hat"), zero ID leaks, every prompt ends
  with the preservation clause, no detail absent from scene text + image
- Offline classifier battery: vehicle_interior → vehicle shots only; ground-level solo never
  pre-ticks Birds_Eye/Crane; tight CU never pre-ticks Wide; 3-subject roster → 3 close-ups
- No-shot-sheet MD regression: parse identical to pre-Phase-3 (plain labels, no binding)
- `--plan` failure (404 URL): exit 1, zero deliverables, no directory (Q16)
- `04.INPUT/` sha256 byte-identical before/after every `--plan` run
- `add-multi-checkboxes` (external repo) fixed + verified live: 17 angles, `NEW.md` skipped,
  corrected path; committed there as `be53ca3` ("feat: load .md templates, skip NEW.md,
  env/CLI source override") — `--source` CLI / `ANGLE_TEMPLATES_DIR` env override the yaml
  default (Q10)

### Questions resolved this session
Q19–Q22 in `USER-FILES/07.TEMP/questions.md` (all recommended options): Q19 plan accepts both
input shapes (preflight skips checkbox validation in plan mode); Q20 `subject_arity` frontmatter;
Q21 code-side substitution; Q22 malformed shot sheet hard-fails.

### Git state — committed
- `feature/vision-payload-and-shot-planner` holds the committed Phase 3 work: 5 new modules,
  10 modified, 17 template `.md` added, 17 `.txt` deleted (see git log for the commit hash).
  External repo committed separately as `be53ca3`.
- TODO.md wiped clean at phase wrap-up — Phase 4 session starts from a blank TODO.

### Codebase Stats (as of 2026-08-26, post-Phase 3)
- 40 Python files in `src/`, 4,919 total lines (+777 from Phase 1/2 baseline)
- 0 syntax errors, 0 print(), 0 TODO/FIXME in src/
- Over 250-line soft limit: `cli_handler.py` (265) — pre-existing, known, not blocking
- All new files ≤ 167 lines; `md_input_parser.py` split back under the limit (201)

### Next Phase
- Phase 4 — Accounting and caching. Entry gate met (Phases 1–3 verified live).

## Last Session Summary (2026-08-26) — Phase 2: Prompt Quality

### Feature Implementation — ✅ COMPLETE (all tasks verified against live API)
Phase 2 (`plan/phase_2.md`) landed on `feature/vision-payload-and-shot-planner`. No `src/`
code changes shipped — this phase was pure prompt-asset and profile work.

- `system_prompt.md` — preservation clause added as a hard rule + `Your Task` bullet (§2.2);
  all few-shot examples carry the clause; new Example 5 (TWO_SHOT, no character sheets,
  unnamed subjects, descriptive positional anchors); "on the line of eyesight" → "at eye
  level" (§2.5); explicit 60–90 word target (§2.6 + Q18 answer); scene-text factual-only
  guard against convert/stylise/restyle/improve instructions (§2.8); character-sheet bullet
  now fires only when refs exist (§2.5)
- `angle-templates/` (17 files) — de-motioned Rack_Focus / Handheld_Shaky_Cam /
  Tracking_Dolly_Shot / Crane_Jib_Shot per §2.3 table; stripped style/lighting language
  per §2.4 (Close_Up lighting sentence, Macro_Shot style stack, plus "cinematic"/"dramatic"
  and vibe-lists across the other 15). No `prompt_suffix` key added (Q7 answer)
- Profile — renamed `gemini-3.7-flash_temp0.5_REAL-TIME.yaml` →
  `gemini-3.7-flash_temp0.2_REAL-TIME.yaml`, `temperature: 0.2`, `metadata.profile_name`
  updated (§2.7); output dir naming derives from the value so no code change

### Deviation from plan — max_tokens 4000, not 1000 (measured, not guessed)
gemini-3.7-flash is a thinking model whose reasoning tokens count against `max_tokens`,
and reasoning **cannot be disabled**: OpenRouter rejects `reasoning: {"effort": "none"}`
(400 "Reasoning is mandatory for this endpoint") and the SDK silently strips
`reasoning: {"enabled": false}` (its `ChatRequestReasoning` only knows `effort`/`summary`).
At max_tokens 1000 the model burned the entire budget on reasoning → truncated mid-sentence
prompts and one empty response (which the Phase 1 hard-failure machinery caught exactly as
designed: run aborted, zero deliverables, `_FAILED` dir). Set 4000 instead; the 60–90 word
rule in `system_prompt.md` is the real length constraint.

### Verification (§2.9 acceptance) — ALL PASSED on live run
- `--selftest` PASS; live run 17/17 angles, atomic promotion →
  `USER-FILES/05.OUTPUT/260826_102306_gemini-3.7-flash_RT_temp0.2_MULTI-ANGLE-MD/`
- All 17 prompts: end with the preservation clause; 79–90 words (in range); no template-borne
  style/lighting; no motion/focus-pull/transition requests; concrete positional anchors
  everywhere (never bare "the subject"); no "photorealistic" conversion framing
- Independent vision-call description of the source image confirms every prompt detail exists
  in the pixels (snowy birch forest, wooden platform, crate-laden flatcar with stencilled
  letters, two draft horses, man in dark overcoat + wide-brimmed hat at frame left, worker
  holding rope, lanterns, steaming locomotive, twilight) — no fabrications (acceptance 3)
- `260826_101231_..._FAILED/` and `260826_101646_.../` dirs in 05.OUTPUT are diagnostics from
  the truncation investigation (kept per Q2 policy)

### Questions resolved this session
- Q14–Q18 answered in `USER-FILES/07.TEMP/questions.md`: families live in template frontmatter
  (Phase 3); both checkbox grammars accepted; `--plan` gets prime-directive staging; `--plan`
  copies input MD verbatim; 60–90 word target. Q1–Q13 were already answered and locked.

### Next Phase
- Phase 3 — Adaptive shot planning (`--plan` mode). Entry gate met (Phases 1–2 verified live).

### Codebase Stats (as of 2026-08-26)
- 35 Python files in `src/`, unchanged from Phase 1 (4,142 lines — verify)
- 17 angle templates rewritten (all single-sentence framing-only), 1 profile renamed

---

## Last Session Summary (2026-08-25) — Phase 1: Real Images + Hard Failure Guarantees

### Feature Implementation — ✅ COMPLETE (all tasks verified, NOT blocked)
The stage-5 model now actually receives the images, and any deviation from a flawless run
aborts with **zero MD deliverables** (prime directive, plan_context.md §0.4).

- `--selftest` **PASSED against the live API** — red/green/blue orientation correct (acceptance 1)
- All four deliberate-failure tests exit non-zero with no output directory (acceptance 2)
- Live reference run succeeded: 17/17 angles, atomic promotion, 123.8s
- Prompts verified: every concrete detail (wide-brimmed-hat man at frame left, birch forest,
  crate-laden flatcar, two draft horses, lanterns, twilight) confirmed present in the image by an
  independent vision-call description — no fabricated staging (acceptance 3)
- `min_prompt_tokens` baseline **measured** (not guessed): prompt_tokens 4156–4206 per angle call
  → floor set to 2078 in the profile

### New Modules (4)
- `payload_builder.py` (65) — `build_user_content()`: 5 ordered content parts (scene text, original
  image `detail:"original"`, ref images, image-label marker lines, angle template), mandatory
  `PayloadIntegrityError` invariant (image-part count == 1 + refs), `cache_breakpoint` wired
- `preflight.py` (132) — `run_preflight()`: A) parse+checkbox validation (moved from orchestrator),
  B) image URL reachability (httpx HEAD, image/*, ≤20MB, ranged-GET retry on 405, per-run cache),
  C) model vision capability via `models.list().architecture.input_modalities`, D) loud warnings on
  dead cache_config keys. Runs before any directory exists
- `output_staging.py` (33) — sibling `.staging` dir, `os.replace` promotion, `_FAILED` rename +
  `FAILURE_REPORT.md` on failure
- `selftest.py` (53) — canary: committed 256×256 red/green/blue PNG (stdlib zlib+struct, 1071 bytes)
  sent as data: URL; asserts left/right orientation; wired into `--selftest` and as the first thing
  `--dry-run` does when a key is available

### Modules Modified (10)
- `api_client.py` — `process_text` takes `user_content: list`; per-response verification (non-empty
  text raise; prompt_tokens floor raise; null floor → loud WARNING each call); deleted
  `build_system_prompt_with_scene` (scene relocated into user content part 1 per §1.1 ordering)
- `multi_angle_orchestrator.py` (241) — blanket per-file except removed (failures raise
  `FileProcessingError` with file+angle context); preflight → staging → promote flow; dry-run and
  zero-ticked passthrough unchanged
- `batch_request_builder.py` — uses shared builder; scene no longer stapled to system prompt
- `config.py` — `get_output_directory` is pure (no mkdir); directory lifecycle owned by staging
- `base_orchestrator.py` — added `setup_logging(output_dir)`; real runs log into staging
- `profile_manager.py` / `config_validator.py` — `min_prompt_tokens` profile key applied;
  added to SKIPPED_KEYS (null allowed)
- `dry_run_estimator.py` / `dry_run_report_formatter.py` — explicit warning that image tokens are
  excluded from `--cost-only`; scene tokens counted; estimator creates its own report dir
- `main.py` — `--selftest` flag; `_maybe_run_selftest` in dry-run (skips quietly without key)
- `user_message.md` — removed image-embed placeholder sections and the false "scene description in
  your system prompt" sentence; remains the angle-template instruction wrapper (part 5)
- `gemini-3.7-flash_temp0.5_REAL-TIME.yaml` — `min_prompt_tokens: 2078` (measured 2026-08-25)

### Verified
- `--selftest` exit 0 (live), `--list-profiles` unchanged, `--cost-only` warns about image tokens
- Failure tests: 404 URL / text/html content-type / text-only model (deepseek-chat) / monkeypatched
  builder → all exit 1, no final output dir (test 4 leaves the plan-mandated `_FAILED` dir)
- Floor logic verified offline (stub client): abort below floor, warning when null
- Live run output: `USER-FILES/05.OUTPUT/260825_230900_gemini-3.7-flash_RT_temp0.5_MULTI-ANGLE-MD/`
- Old blind outputs (for comparison): `/home/admin/Nextcloud-QO1/BEKER/260825_140626_..._MULTI-ANGLE-MD/`

### Open Questions (from USER-FILES/07.TEMP/questions.md — pending user answers)
- Q1 signed/private URL policy in preflight | Q2 `_FAILED` residue policy (plan-as-written: partials
  kept) | Q3 dry-run selftest billing (plan-as-written: wired) | Q4 token floor vs Phase 3 `--plan`
  calls | Q5 batch mode scope (plan-as-written: builder fixed) | Q6 dead params (wired now per plan)
  | Q11 cost-only (warning chosen) | Q7/Q8/Q9/Q10/Q12 belong to Phases 2–4

### Known — out of scope for this plan (do not fix in Phases 1–4)
- `STUDIOLOT_CONTRACT.md` flags not implemented (`--input_dir` hyphen mismatch, no `--output_dir`,
  hardcoded `USER-FILES/05.OUTPUT` in `config.py`) — needs its own task
- `src/cli_handler.py` is 263 lines (soft-limit overage, known, not blocking)
- `angle-templates/NEW.md` has spelling errors — normalise in Phase 3.4
- Usage accumulation bug (per-file cost = last call only) — Phase 4 §4.1
- `cache_system_prompt` / `report_cache_metrics` dead keys — Phase 4 §4.3
- Rack_Focus/Tracking_Dolly/Crane_Jib/Handheld templates still describe motion — Phase 2 §2.3
- Batch mode: only realtime profile active; batch path uses shared builder but has no staging

### Codebase Stats (as of 2026-08-25)
- 35 Python files in `src/`, 4,142 total lines
- 0 syntax errors, 0 print(), 0 TODO/FIXME in src/
- New files all ≤ 250 lines; `multi_angle_orchestrator.py` trimmed to 241
- 1 file over the 250-line soft limit: `cli_handler.py` (263) — known, not blocking
- 0 files over 400-line hard limit

### Next Phase
- Phase 2 opens only after this live-run verification — which has now happened ✅
- Phase 2: prompt quality (preservation clause, de-motion, style stripping, temp 0.2, few-shots)

---

## Last Session Summary (2026-08-24) — Skip Image/URL Lines Before Endpoint

### Feature Implementation — ✅ COMPLETE (all 5 tasks verified)
- Scene (Dataset A) is now **multi-line**: all lines before the first image line are joined as scene text
- Lines matching Markdown embeds/links (`![alt](url)`, `[text](url)`) or URLs (`http://`, `https://`, `www.`) are **skipped and logged at INFO** (case-insensitive)
- Fails fast: `ValueError` if scene is empty after filtering
- Checkbox parsing, image extraction (Datasets B/C), and all downstream behavior unchanged

### Implementation Details
- `src/md_input_parser.py` (174 lines): added `MD_LINK_PATTERN`, `URL_PATTERN` (IGNORECASE), `_is_skippable_line()` helper; scene built in `parse_md_file()` from `lines[:first_image_idx]`, joined with `\n`, then `.strip()` (keeps existing single-line scenes byte-identical)
- No downstream changes needed — all consumers treat `scene` as an opaque string
- Docs updated: `README.md` (Input Format), `STUDIOLOT_CONTRACT.md` (vehicle bullet + session history)

### Verified
- Direct parse tests: link line, http/www line, uppercase `HTTPS://` line all skipped and logged; scene joined correctly
- Empty-after-filter scene raises `ValueError` (fail fast)
- Regression: existing real input file parses identically (scene byte-identical, 17 angles)
- `venv/bin/python -m src.main --cost-only` end-to-end OK

### Session Insights (worth remembering)
- **`--dry-run` (realtime mode) does NOT parse MD files** — it only sets up config/output dir and writes an empty report. The parse-based dry-run path is **`--cost-only`** (uses `DryRunEstimator` → `parse_md_file`)
- `--cost-only` no longer fails on auth (1Password stripped; dummy key used for token counting)
- Test MD files in `04.INPUT/` were removed after verification so fake URLs never reach real API runs

### Codebase Stats
- 31 Python files in `src/`, 3,804 total lines
- 0 syntax errors, 0 TODO/FIXME, 0 print() in src/
- 1 file over 250-line soft limit: `cli_handler.py` (263) — known, not blocking
- 0 files over 400-line hard limit

### Remaining Tasks
- None for this feature. Live API test still pending from earlier sessions (requires API credits).

## Older Session Summary (2026-05-23) — Multi-Angle Reframing Feature v3

### Feature Implementation — ✅ COMPLETE
- Transformed codebase from TXT-to-Montage to MD-to-Multi-Angle processor
- 21 of 23 tasks completed; 2 remaining (live API test, AGENTS.md update)

### New Modules Created (6)
- `md_input_parser.py` — Parses MD files into Datasets A, B, C (74 lines)
- `angle_loader.py` — Loads angle templates from directory (40 lines)
- `user_message_template.py` — Renders user message with placeholders (61 lines)
- `multi_angle_output_saver.py` — Saves outputs in subdirectories (45 lines)
- `multi_angle_orchestrator.py` — Orchestrates full pipeline (220 lines)
- Rewrote `batch_request_builder.py` — Multi-angle batch requests (116 lines)

### Modules Modified (8)
- `api_client.py` — Added optional `system_prompt` parameter
- `batch_processor.py` — Multi-angle batch creation, saves `_original_items.json`
- `batch_result_parser.py` — Multi-angle custom ID parsing; fixed `_load_original_texts` to load `_original_items.json`
- `batch_result_saver.py` — Multi-angle subdirectory output format
- `cli_handler.py` — Routes to multi-angle orchestrator
- `main.py` — MD file discovery, `MULTI-ANGLE-MD` suffix
- `dry_run_estimator.py` — Multi-angle cost estimation
- `config.py` — Added `suffix` parameter to `get_output_directory`

### Modules Deleted (3)
- `txt_processing_orchestrator.py`, `txt_reader.py`, `txt_writer.py`

### Bugs Fixed
- `batch_result_parser.py:180` tsv_ bug — now handles both `md_` and `txt_` prefixes
- `batch_result_parser.py` was loading `_original_texts.json` but processor saves `_original_items.json` — fixed
- `_parse_successful_result()` wasn't enriching results with `original_image`/`ref_images` — fixed

### Verified Commands
```bash
python3 -m src.main --list-profiles    # OK
python3 -m src.main --dry-run          # OK
python3 -m src.main --cost-only        # OK ($0.0131 for 1 file x 17 angles)
```

### Codebase Stats
- 33 Python files in `src/`, 4,558 total lines
- 0 syntax errors, 0 broken imports
- 2 files over 250-line soft limit: `config_validator.py` (343), `profile_manager.py` (282)

### Remaining Tasks
1. **Live API test** — requires API credits
2. **AGENTS.md update** — deferred until live API test passes

### Known Issues (Not Blocking)
- None

### Cleanup Completed (2026-05-24)
- ~972 lines removed (~21% reduction from 4,558 → 3,586)
- 2 files deleted: `constants.py`, `scripts/update_profile_names.py`
- 16 unused functions removed across 8 files
- 5 unused exception classes removed
- 2 duplicate code blocks consolidated
- 7 logger.debug() statements removed
- 0 syntax errors, 0 unused imports, 0 TODO/FIXME, 0 print() in src/
- Report: `USER-FILES/07.TEMP/260523_cleanup_report.md`

### Checkbox Selection Feature (2026-05-24) — ✅ COMPLETE
- Added per-file angle selection via markdown checkboxes in input MD files
- New module: `checkbox_validator.py` (68 lines) — strict validation, hard-fail on missing/mismatched labels
- `md_input_parser.py` rewritten with `ParsedMdInput` dataclass (156 lines); normalizes spaces→underscores
- `multi_angle_orchestrator.py` — processes only checked angles, skips unchecked files (copies raw MD to output)
- `multi_angle_output_saver.py` — added `copy_raw_md_file()` for unchecked passthrough
- `batch_request_builder.py` — per-file `checked_angles` filtering
- `cli_handler.py` — batch submission validates checkboxes
- `dry_run_estimator.py` — cost estimation uses checked angles only
- `angle_loader.py` — added `get_available_angle_names()` helper
- README.md updated with checkbox workflow documentation
- Input files without checkbox section fail with error suggesting `add-multi-checkboxes` tool
- All-unchecked files are copied verbatim to output directory (no API calls)

---

---

# img-to-multi-angle — Project Context

## Project Overview
Multi-Angle MD Processor — transforms Markdown files into multi-angle reframed outputs using OpenRouter API.

## Architecture
- **33 Python files** in `src/`, **3,596 total lines** (longest 248 — `shot_planner.py`, split candidate)
- **3 offline test batteries** in `tests/` (950 lines — `offline_battery.py` 44 checks, `failure_battery.py` 11, `feature_battery.py` 9; pure Python, monkeypatched API, run with `venv/bin/python tests/<name>.py`)
- Entry point: `python -m src.main`
- Config: `USER-FILES/01.CONFIG/openrouter_config.yaml` + `USER-FILES/03.PROFILES/*.yaml`
- Input: `USER-FILES/04.INPUT/*.md` (raw Markdown with scene + image embeds, or pre-checked Markdown)
- Output: `USER-FILES/05.OUTPUT/{timestamp}_{model}_{mode}_MULTI-ANGLE-MD/`

## Key Modules
- `main.py` — CLI entry point, argument parsing
- `config.py` — Config loading and validation
- `config_validator.py` — Configuration validator
- `profile_manager.py` — Profile loading/application
- `cli_handler.py` — Thin router delegating to `ProfileCommand`, `CostCommand`, `ProcessCommand`
- `multi_angle_orchestrator.py` — Single-pass orchestration (auto-planning + prompt generation) with atomic staging
- `shot_planner.py` — Vision-based dynamic shot planning with reason-fed retry on content rejections
- `shot_plan.py` / `shot_sheet.py` — Shot and scene data models
- `banned_words.py` — Banned abstract-noun / boilerplate scan for planner intents and generated prompts
- `shot_generator.py` — Per-shot prompt generation loop (render → call → scan → retry → accumulate)
- `assets.py` — Typed reference assets parser and models
- `api_client.py` — OpenRouter API wrapper with token floor and usage extraction
- `payload_builder.py` — Multi-part image/text user payload builder
- `preflight.py` — Preflight image reachability and vision capability checks
- `cost_calculator.py` — Token cost calculation

## Codebase Health (as of 2026-09-04)
- 0 syntax errors (compileall clean on `src/` and `tests/`)
- 0 files over 250-line soft limit (`shot_planner.py` 248 is the longest)
- 0 files over 400-line hard limit
- 0 TODO/FIXME comments, 0 print() statements in `src/` (batteries in `tests/` use `print` for reporting — allowed)
- 33 files in `src/`, 3,596 total lines

## Testing
```bash
venv/bin/python tests/offline_battery.py   # 44 checks: ban scan, shot_type, fences, coverage, few-shots
venv/bin/python tests/failure_battery.py   # 11 checks: exit-1 guarantees, _FAILED residue, generator retry
venv/bin/python tests/feature_battery.py   # 9 checks: planner retry contract (reason feed-back, usage sums)
venv/bin/python -m src.main --list-profiles   # Lists profiles
venv/bin/python -m src.main --cost-only        # Token & cost estimation
venv/bin/python -m src.main --selftest         # Vision canary test
venv/bin/python -m src.main                    # Direct single-pass execution
```
