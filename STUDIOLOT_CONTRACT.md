# STUDIOLOT_CONTRACT.md

> This repo is part of the studiolot ecosystem.
> Preserve the CLI contract below when modifying this script.

---

## What studiolot is

studiolot is a TUI that orchestrates AI media generation. It drives scripts
like this one by passing `--input_dir`, `--output_dir`, and `--profile` flags.
The same script runs standalone (with its own `USER-FILES/` defaults) or
under studiolot (with paths injected by the TUI).

Full architecture: `studiolot/docs/architecture/PHILOSOPHY.md`

---

## Dual-mode contract

| Mode | How invoked | Input | Output | Profile |
|------|------------|-------|--------|---------|
| **Standalone** | `python run.py` from repo root | `USER-FILES/04.INPUT/` | `USER-FILES/05.OUTPUT/` | `USER-FILES/03.PROFILES/` (fallback `02.STANDBY/`) |
| **Studiolot** | `python <entry> --input_dir X --output_dir Y --profile Z` | `--input_dir` value | `--output_dir` value | `--profile` value |

The script detects its mode by checking whether `--input_dir` and `--profile`
were passed on the command line.

---

## REQUIRED — Vehicle contract (calls an external API)

- [ ] Accepts `--input_dir`, `--output_dir`, `--profile` CLI flags
- [ ] Reads `.md` bullet files from input_dir (scene text = non-embed/URL lines before first image; image lines = `![](url)`)
- [ ] Writes output to a timestamped subfolder under output_dir
- [ ] Does NOT `import replicate` (or any provider SDK) directly — uses `engine_loader.py`
- [ ] `engine_loader.py` vendored copy matches `studiolot/pipeline/engine_loader.py`
- [ ] Profile YAML carries `platform`, `endpoint`, `parameters`, `prompt_prefix`/`suffix`
- [ ] Do NOT hardcode folder paths (no `03_INPUT_SHOTLIST(STILL)`, etc.)
- [ ] Do NOT move or delete user files from input directories
- [ ] CLI flags take priority over standalone defaults

---

## Reference — studiolot repo

| Doc | What it covers |
|-----|---------------|
| `docs/architecture/PHILOSOPHY.md` | Why, folder model, bullet format, sidecar, copy-forward |
| `docs/architecture/DASH_CONTRACT.md` | TUI panel responsibilities, execution paths, keybindings |
| `docs/architecture/ENGINE_CONTRACT.md` | Engine interface, datatypes, repo structure, discovery |
| `docs/architecture/VEHICLE_CONTRACT.md` | Vehicle CLI contract, engine discovery, standalone UX |
| `pipeline/engine_loader.py` | Canonical `load_engine()` — vendored copies must match |
| `pipeline/constants.py` | Canonical folder names, action verbs, conventions |
| `console/studiolot/screens/project_init/tools_data.py` | `UTILITY_REPOS` + `APPLICATION_REGISTRY` — what's wired |

The studiolot repo is at:
`/home/admin/Nextcloud/00-DEVELOPMENT/MISC_DEV_TOOLS/studiolot/`

---

## Session History

<!-- Add entries here when changes are made. Same format as FC's AGENTS.md. -->

- **2026-08-24**: Scene (Dataset A) is now multi-line — all lines before the first image are joined as scene text; Markdown embed/link and URL lines are skipped and logged at INFO.
- **2026-08-29**: Phase 2 — the fixed angle template directory is gone; `--plan` proposes the shot list from the image itself. Checkbox entries lead with shot ids validated against the file's own shot-plan block. Batch mode and its CLI flags (`--batch-id`, `--list-batches`, `--wait`) are removed. Output MD contract unchanged: prompt, blank line, image embeds.
