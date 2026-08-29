# Phase 1 — Typed assets and per-shot reference routing (`plan/phase_1.md`)

## Bootstrap

- [x] **[git]** Switch to branch `img-to-reframes` if not already on it
  - Requirement: plan_context.md §0.1 — the 3-phase plan lives on `img-to-reframes`
  - Action: verify with `git branch --show-current` — already on `img-to-reframes` (HEAD `c35a72f`); nothing to do
  - Effort: 1 point | Priority: High

- [x] **[USER-FILES/05.OUTPUT]** Capture baseline regression run at `c35a72f` (P1-01)
  - Requirement: phase_1.md §1.5 — "An MD with no assets block produces byte-identical output to `c35a72f` (regression — capture a run before starting)"
  - Action: before any code change, run the rewrite pipeline on the current `04.INPUT/` files; record the output dir and sha256 of every produced MD as the golden baseline for P1-15
  - Effort: 1 point | Priority: High

## src/assets.py (new module)

- [x] **[src/assets.py]** Implement `Asset` dataclass + assets-block parser (P1-02)
  - Requirement: phase_1.md §1.1 — fenced ```` ```yaml assets ```` block: `id` matches `^A\d+$` and is unique within the file, `role` ∈ `character|prop|location`, `note` optional free text, `url` required; §1.5 — duplicate asset id → run aborts
  - Action: new focused module (keeps `md_input_parser.py` under the 250-line soft limit): `Asset` dataclass (`id`, `role`, `note`, `url`); `extract_assets_block(content, filename)` fence parser — absent → `None`; malformed YAML, bad id pattern, bad role, missing url, or duplicate id → `ValueError` (fail loud at parse time, before any directory exists)
  - Effort: 2 points | Priority: High

## src/md_input_parser.py

- [x] **[src/md_input_parser.py]** Parse assets block into `ParsedMdInput`; legacy path unchanged (P1-03)
  - Requirement: §1.1 — "Backward compatibility is mandatory. An MD with no assets block parses exactly as it does now … every shot receives all of them, with an INFO log saying so"
  - Action: call `extract_assets_block` from `parse_md_file`; add `assets: List[Asset]` to `ParsedMdInput`; strip the fenced block from scene-text collection (its non-URL lines like `- id: A1` would otherwise pollute the scene); no block → INFO log naming the file
  - Effort: 1 point | Priority: High
  - Related: P1-02

- [x] **[src/md_input_parser.py]** Extend checkbox grammar with grounding lists `{A1, A2}` (P1-04)
  - Requirement: §1.3 — "Every checkbox entry gains a grounding list … `{}` means master only"
  - Action: extend `_parse_checkbox_line` to split a trailing `{...}` off the label; return per-label ground ids (empty for `{}`); keep parsing braces-less legacy labels (preflight needs the label intact to enforce Q2's hard fail)
  - Effort: 1 point | Priority: High
  - Related: P1-02, P1-10

## src/shot_sheet.py

- [x] **[src/shot_sheet.py]** Add `asset` field to the subject schema (P1-05)
  - Requirement: §1.2 — each subject "may carry the asset that best depicts it" — `asset: A1` or `null`
  - Action: add `asset: Optional[str]` to `ShotSubject`; `shot_sheet_from_dict` reads it (`str` or `None`, nothing else); `_render_shot_sheet_block` in `plan_output_writer.py` emits it so the binding survives into the enriched MD
  - Effort: 1 point | Priority: High
  - Related: P1-09

## src/payload_builder.py

- [x] **[src/payload_builder.py]** Asset-labelled marker text (P1-06)
  - Requirement: §1.2 — assets sent as `image_url` parts "labelled by id in the marker text (extend the existing labelling in `payload_builder`)"
  - Action: accept refs as `(id, role, note, url)` descriptors instead of bare URLs; marker line becomes `Image N is asset A1 (role: character) — "the woman in the passenger seat".`; image-count invariant untouched (it compares against whatever list it was handed, §1.4)
  - Effort: 2 points | Priority: High
  - Related: P1-07, P1-14

## src/shot_planner.py

- [x] **[src/shot_planner.py]** Send declared assets to the planner; bind-only-when-confident (P1-07)
  - Requirement: §1.2 — "`--plan` … now also receives every declared asset as an `image_url` part" and "bind an asset only when it is confident the asset depicts that subject, and to leave `asset: null` otherwise"
  - Action: pass declared assets into `build_user_content` for plan calls; extend the strict json_schema: subject `asset` is `null` or matches `^A\d+$`; extend the planner instruction with the confidence rule
  - Effort: 2 points | Priority: High
  - Related: P1-06, P1-08

- [x] **[src/shot_planner.py]** Abort `--plan` on an undeclared asset binding (P1-08)
  - Requirement: §1.2 + questions.md Q6 — the schema can enforce the id pattern but not existence
  - Action: after the plan call, validate every non-null `asset` against the file's assets block; undeclared id → `_FAILED` dir + exit 1 naming the subject and the id (same class as the free-form subject-id defect)
  - Effort: 1 point | Priority: High
  - Related: P1-07

## src/plan_output_writer.py

- [x] **[src/plan_output_writer.py]** Emit grounding lists on checkbox labels (P1-09)
  - Requirement: §1.3 — "Grounds are derived by the planner from the subject bindings: a shot bound to S1 grounds on S1's asset, when one exists"; master implicit, never listed
  - Action: derive braces per shot entry from its subjects' `asset` fields; render `- [x] Close Up — S1 (woman) {A1}` and `{}` for scene-wide shots; shot-sheet block emits `asset` per subject
  - Effort: 2 points | Priority: High
  - Related: P1-05, P1-07

## src/preflight.py

- [x] **[src/preflight.py]** Grounding-id and declaration checks (P1-10)
  - Requirement: §1.3 — every id in braces must exist in the assets block, else "hard fail naming the file, the label, and the unknown id"; empty assets block with non-empty braces → hard fail; Q1 — refs present but undeclared → hard fail; Q2 — braces-less label in an asset-bearing file → hard fail. All before any API call and before any directory is created
  - Action: run in `run_preflight` (skip in plan_mode, matching existing checkbox-validation policy); raise `PreflightError` with file + label + offending id
  - Effort: 2 points | Priority: High
  - Related: P1-04

- [x] **[src/preflight.py]** Binding-divergence WARNs (P1-11)
  - Requirement: Q3 — WARN when a checked shot's braces omit a bound subject's asset; Q4 — braces are authoritative, WARN when they disagree with shot-sheet bindings
  - Action: cross-check each checked label's braces against its subjects' shot-sheet `asset` fields; `logger.warning` on divergence, never hard-fail (human override allowed)
  - Effort: 1 point | Priority: Med
  - Related: P1-10

- [x] **[src/preflight.py]** Asset URL reachability (P1-12)
  - Requirement: Q5 — HEAD-check every declared asset URL; a dead URL aborts the run even when no checked shot grounds on it
  - Action: extend the existing URL loop to include all declared asset urls, sharing the `url_cache`
  - Effort: 1 point | Priority: Med
  - Related: P1-10

## src/multi_angle_output_saver.py

- [x] **[src/multi_angle_output_saver.py]** Per-shot reference routing in `save_angle_outputs` (P1-13)
  - Requirement: §1.4 — replace the once-built ref block with "per shot, the resolved list of grounding URLs … master plus only those"; "Output format is otherwise byte-identical — `frame-composer` must not notice anything except that some files now carry fewer embeds"
  - Action: change the signature to take per-shot grounding URL lists; emit `prompt\n\n![master]\n\n` + that shot's refs only; no refs → no trailing ref block
  - Effort: 1 point | Priority: High
  - Related: P1-14

## src/multi_angle_orchestrator.py

- [x] **[src/multi_angle_orchestrator.py]** Resolve per-shot grounding; wire payload and saver (P1-14)
  - Requirement: §1.4 — "The same routing must reach the API call: `build_user_content()` should receive only that shot's grounding assets as `ref_images`, not the whole kit"
  - Action: resolve each checked label's braces → asset URLs (master never listed); pass the per-shot refs to `build_user_content` and the per-shot lists to `save_angle_outputs`; legacy path (no assets block) passes all refs exactly as today
  - Effort: 2 points | Priority: High
  - Related: P1-06, P1-13

## Verification (§1.5)

- [x] **[tests/verification]** Regression: no-assets-block file byte-identical to baseline (P1-15)
  - Requirement: §1.5 + acceptance 2 — "An MD with no assets block produces byte-identical output to `c35a72f`"
  - Action: re-run the same `04.INPUT/` file(s) and sha256-compare every output MD against the P1-01 capture
  - Effort: 1 point | Priority: High
  - Related: P1-01

- [x] **[tests/verification]** Routing: CU S1 → master+A1 only; CU S2 → master+A2 only; scene-wide → master only (P1-16)
  - Requirement: §1.5 + acceptance 1
  - Action: input MD with two character assets; read the three output MDs and assert their exact embed lists
  - Effort: 1 point | Priority: High

- [x] **[tests/verification]** Failure battery: undeclared id in braces; duplicate asset id → abort with zero output directories (P1-17)
  - Requirement: §1.5 + acceptance 3
  - Action: two malformed inputs; assert exit non-zero, no final output directory, no deliverable MDs
  - Effort: 1 point | Priority: High

- [x] **[tests/verification]** `--plan` on an asset-bearing file: bindings present; `04.INPUT/` byte-identical (P1-18)
  - Requirement: §1.5 + acceptance 12
  - Action: checksum `04.INPUT/` before/after; inspect the enriched MD for subject `asset` fields and braces on labels
  - Effort: 1 point | Priority: High

- [x] **[tests/verification]** Regression gates: `--selftest` live + four deliberate-failure tests (P1-19)
  - Requirement: §1.5 + acceptance 10
  - Action: rerun the existing suite; all four abort with zero output directories
  - Effort: 1 point | Priority: High

## Wrap-up

- [x] **[docs]** Commit (on owner request only) + `AGENTS.md` session entry (P1-20)
  - Requirement: plan_context.md §0.8 — "Phases land in order and each ends with a commit plus an `AGENTS.md` entry"; manifesto §10 — no commits unless explicitly requested
  - Action: verify all P1-15…P1-19 gates pass; check file sizes against the 250/400-line memo; write the session summary into `AGENTS.md`; commit only when the owner says so
  - Effort: 1 point | Priority: Med


## Verification notes (2026-08-29)

- P1-15: live legacy rerun → 17/17 embed-identical, file set identical; prompt texts differ
  run-to-run because the profile runs at temperature 0.2 (stochastic, not a regression).
  Deterministic proof instead: old (c35a72f) vs new parser output identical on the legacy
  file and all 17 payloads byte-identical (oldpkg harness in /tmp/opencode).
- P1-16: live — CU S1 → master+A1 only; CU S2 → master+A2 only; Wide Shot → master only;
  all prompts 78–90 words, all end with the preservation clause.
- P1-17: undeclared brace id → PreflightError exit 1; duplicate asset id → ValueError exit 1;
  zero output directories both.
- P1-18: live --plan on asset file → asset field emitted for all subjects (model chose null
  bindings — confident-only rule; non-null derivation unit-verified offline), braces on every
  label, 04.INPUT sha256-identical.
- P1-19: --selftest PASS live; 404 URL / text/html / text-only model (vision gate) /
  payload-integrity invariant all abort; zero output directories.
- P1-20: AGENTS.md entry written; commit pending owner request.
