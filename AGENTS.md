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
- **31 Python files** in `src/`, **3,804 total lines**
- Entry point: `python -m src.main`
- Config: `USER-FILES/01.CONFIG/openrouter_config.yaml` + `USER-FILES/03.PROFILES/*.yaml`
- Input: `USER-FILES/04.INPUT/*.md` (must include checkbox section)
- Output: `USER-FILES/05.OUTPUT/{timestamp}_{model}_{mode}_MULTI-ANGLE-MD/`

## Key Modules
- `main.py` — CLI entry point, argument parsing
- `config.py` — Config loading, `require_batch_config()` utility
- `config_validator.py` — Split into `YamlValidator`, `FieldValidator`, `ConflictChecker` + thin `ConfigurationValidator` orchestrator
- `profile_manager.py` — Profile loading/application
- `cli_handler.py` — Thin router delegating to `ProfileCommand`, `BatchCommand`, `CostCommand`, `ProcessCommand`
- `multi_angle_orchestrator.py` — Main processing workflow, angles/templates cached as instance attributes
- `api_client.py` — OpenRouter API wrapper with extracted helpers (`_build_system_message`, `_build_api_payload`, `_extract_usage_data`)
- `batch_processor.py` / `batch_monitor.py` / `batch_result_parser.py` — Batch operations
- `cost_calculator.py` — Token cost calculation

## Refactoring Completed (2026-05-23)
- **34 tasks completed**, 41 effort points
- Deleted 2 dead modules: `response_validator.py`, `cost_reporter.py`
- Removed 21 unused constants from `constants.py`
- Removed 3 unused dataclasses from `data_models.py`
- Split `ConfigurationValidator` into 4 focused classes
- Split `CLIHandler` into 4 command handlers + thin router
- Reduced `process_text()` complexity from 14 to ~4
- Reduced `_process_single_file()` from 7 to 3 parameters
- Created shared `require_batch_config()` utility
- All stale docstrings updated, version bumped to 5.0.0

## Codebase Health (as of 2026-08-24)
- 0 syntax errors
- 0 unused imports
- 0 functions with cyclomatic complexity >10
- 1 file over 250-line soft limit: `cli_handler.py` (263 lines)
- 0 files over 400-line hard limit
- 0 TODO/FIXME comments
- 0 logger.debug() statements
- 0 print() statements in src/
- 31 files in `src/`, 3,804 total lines

## Future Considerations
- 8 functions have exactly 5 parameters (borderline acceptable, not blocking)

## Testing
```bash
venv/bin/python -m src.main --list-profiles   # Works
venv/bin/python -m src.main --dry-run          # Works (does NOT parse MD files)
venv/bin/python -m src.main --cost-only        # Works (dummy API key for token counting)
```
