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
