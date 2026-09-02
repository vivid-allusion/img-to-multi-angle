# img-to-multi-angle

Transform Markdown scene descriptions into multi-angle reframed image prompts using the OpenRouter API.

Given an MD file with a scene description and an image URL, this tool looks at the image, decides
its own cinematic shot list, and writes one reframing prompt per shot — ready to feed into an
image-to-image model.

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set your API key
export OPENROUTER_API_KEY="sk-or-..."

# 3. Place your .md files in USER-FILES/04.INPUT/

# 4. Run
python -m src.main
```

## What It Does

One command, one pass. For each input MD file:

1. **Preflight** — validates config and profile, HEAD-checks every image URL, and confirms the
   chosen model has vision. All of it before the first API call and before any output directory
   exists.
2. **Plan** — one vision call proposes 5–6 shots. Each shot carries an id, a label, a concrete
   intent, and a `shot_type` naming the coverage slot it fills (`face_cu`, `medium_action`,
   `hands_insert`, `wide_master`, `dynamic_vantage`, `object_insert`).
3. **Generate** — one call per shot, each carrying the master image plus only the declared assets
   that ground that shot.
4. **Save** — one `.md` per shot, written to a hidden staging directory and atomically promoted to
   a timestamped output directory on success, or renamed `_FAILED` on any error.

### Coverage Hierarchy

Drama lives in faces and hands, so when a scene contains people the planner is required to cover
them. A plan must include at least a **face close-up**, a **hands-on action insert**, and an
**establishing wide** — a plan missing any of the three is rejected and the run aborts. While
people are present, a close-up on an untouched prop is forbidden.

Scenes with no people at all are exempt: vehicles, structures, and landscapes get the boldest
angles available, and object inserts are legitimate there.

### Prompt Craft

Generated prompts describe only what a camera can capture:

- Shot sizes are written as **physical boundaries**, never abbreviations — "framed so close on the
  face that it fills the image from forehead to chin", not "CU on the face".
- Every prompt carries all three pillars: **who** is in frame, **what** they are physically doing,
  **where** they are — in that order, setting last.
- Abstract language is **banned and enforced in code**. "atmosphere", "mood", "vibe", "intensely",
  "preserve character wardrobe" and their relatives are scanned for in both the planner's shot
  intents and every generated prompt. A hit retries that shot once with the offending words named;
  a second hit aborts the run.
- Identity is held by naming visible specifics ("the ankle-length black wool overcoat"), never by
  instructing the model to preserve or maintain anything.

Prompts target 70–110 words.

## Requirements

- Python 3.10+
- OpenRouter API key
- Dependencies: `openrouter`, `pyyaml`, `loguru`, `pandas`, `natsort`

## Installation

```bash
pip install -r requirements.txt
```

### API Key

Set the `OPENROUTER_API_KEY` environment variable:

```bash
export OPENROUTER_API_KEY="sk-or-..."
```

Alternatively, if you have [1Password CLI](https://developer.1password.com/docs/cli/) installed, the tool will automatically retrieve the key from 1Password.

## Input Format

Place `.md` files in `USER-FILES/04.INPUT/`. A file needs only a scene description and a master
image:

```md
1910's Germany. A liquor smuggling ring works a snowy rail platform. Horses and men ready the
crate-laden wagon.

![master](https://example.com/scene.png)
```

That is enough — the planner supplies the shot list.

### Optional: declared assets

To route specific reference images to specific shots, declare them in a ```yaml assets fence:

```yaml assets
- id: A1
  role: character
  note: the overseer
  url: https://example.com/overseer.png
```

Once an assets block exists, every reference image must be declared, and every asset URL is
HEAD-checked during preflight. Each shot then receives the master plus only the assets it grounds
on; without a block, every shot receives every reference.

### Optional: pre-selecting shots

If a file already carries a ```yaml shot-plan fence with checkbox entries, only the ticked shots
run and no planning call is made. Ticked ids must exist in that file's shot-plan block; unknown
ids hard-fail. If checkboxes exist but none are ticked, the file is skipped and copied to the
output directory as-is.

## CLI Commands

```bash
# Process every file in USER-FILES/04.INPUT/ (profile auto-detected if only one exists)
python -m src.main

# Pick a profile explicitly
python -m src.main --profile gemini-3.7-flash_temp0.2_REAL-TIME.yaml

# Use a custom input directory
python -m src.main --input-dir /path/to/mds

# Dry run — set up config and output dir without API calls
python -m src.main --dry-run

# Cost estimate only
python -m src.main --cost-only

# List available profiles
python -m src.main --list-profiles

# Selftest — verify the model receives images and sees orientation correctly
python -m src.main --selftest
```

## Configuration

### Directory Structure

```
USER-FILES/
├── 01.CONFIG/
│   ├── openrouter_config.yaml    # Base settings (cache, processing)
│   ├── system_prompt.md          # System prompt with few-shot examples
│   └── user_message.md           # User message template with placeholders
├── 03.PROFILES/
│   └── *.yaml                    # Model profiles
├── 04.INPUT/                     # Input .md files go here (READ ONLY)
├── 05.OUTPUT/                    # Timestamped output directories
├── 06.DONE/                      # Processed files moved here
└── 07.TEMP/                      # Temporary files
```

### Base Config (`openrouter_config.yaml`)

```yaml
stream: false

retry_config:
  max_retries: 2
  timeout: 600

processing_options:
  trim_prompts: true
  normalize_spaces: true
  max_prompt_length: 1000
  max_response_length: 40000

cache_config:
  enabled: false
  cache_ttl: 5m

avg_output_tokens: 800
```

### Profile Files (`USER-FILES/03.PROFILES/*.yaml`)

Profiles define the model, pricing, and parameters. Naming convention: `{nickname}_temp{temperature}_REAL-TIME.yaml`

```yaml
metadata:
  profile_name: kimi-k2-thinking_temp0.5_REAL-TIME
  description: Moonshot AI's Kimi K2 thinking model
  created: '2026-03-06'
  version: '1.0'

model:
  endpoint: moonshotai/kimi-k2-thinking
  nickname: kimi-k2-thinking
  capabilities:
    supports_caching: false
    supports_thinking: true

pricing:
  real_time:
    input: 0.6
    output: 2.5

parameters:
  temperature: 0.5
  max_tokens: 8000

enabled: true
```

### Important Configuration Rules

- **No defaults policy** — all config fields must be explicitly defined; missing fields cause hard errors
- **No conflicts** — a setting cannot exist in both `openrouter_config.yaml` AND a profile file
- If only one profile exists, it is auto-detected; otherwise `--profile` is required

## Output Format

Output directories are timestamped and never overwritten:

```
USER-FILES/05.OUTPUT/260902_190632_gemini-3.7-flash_RT_temp0.2_MULTI-ANGLE-MD/
├── input-test/
│   ├── input-test_SH01_overseer_face_close_up.md
│   ├── input-test_SH04_rope_binding_insert.md
│   └── ... (one file per shot)
└── summary_report.md
```

Each output `.md` contains the generated reframing prompt (70–110 words), a blank line, then the
master image embed followed by only that shot's grounding reference embeds. Files with checkboxes
but none ticked are copied verbatim instead.

A run that fails at any point promotes nothing: the staging directory is renamed `_FAILED` with a
`FAILURE_REPORT.md` inside, and the process exits 1.

## Cost Estimation

```bash
# Full dry run (no API calls at all)
python -m src.main --dry-run

# Cost estimate only (uses token counting API)
python -m src.main --cost-only
```

Costs are calculated from: system prompt tokens + shot label/intent tokens + estimated output tokens (from `avg_output_tokens` in config) × pricing rates in the profile.

## Troubleshooting

| Issue | Solution |
|---|---|
| `API key not found` | Set `OPENROUTER_API_KEY` env var or install 1Password CLI |
| `No profiles found` | Add a `.yaml` file to `USER-FILES/03.PROFILES/` |
| `Missing config field` | Ensure all required fields exist in `openrouter_config.yaml` |
| `Config conflict` | Remove duplicate settings — each key must be in config OR profile, not both |
| `system_prompt.md not found` | Ensure `USER-FILES/01.CONFIG/system_prompt.md` exists |
| `ticked shot not found in shot-plan block` | The ticked id is absent from that file's shot-plan fence — fix the id or untick it |
| `plan ... missing mandatory coverage` | The planner returned a human-present plan without a face close-up, hands insert, or wide master — rerun |
| `forbidden word(s) ... after one retry` | The model would not drop an abstract word; rerun, or adjust the ban list in `src/banned_words.py` |
| `ref image not declared in the assets block` | Once an assets block exists, every reference image must be declared in it |
