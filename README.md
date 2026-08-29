# img-to-multi-angle

Transform Markdown scene descriptions into multi-angle reframed image prompts using the OpenRouter API.

Given an MD file with a scene description and image URLs, this tool generates 17 camera-angle-specific reframing prompts (close-up, wide shot, Dutch angle, etc.) tailored to that scene — ready to feed into an image-to-image model.

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set your API key
export OPENROUTER_API_KEY="sk-or-..."

# 3. Place your .md files in USER-FILES/04.INPUT/

# 4. Run
python -m src.main --profile kimi-k2-thinking_temp0.5_REAL-TIME.yaml
```

## What It Does

For each input MD file, the tool:

1. Parses the scene description and image URLs
2. Loads 17 camera angle templates (close-up, wide shot, low angle, etc.)
3. For each angle, asks an AI model to rewrite the generic template into a specific reframing prompt for that scene
4. Saves one `.md` file per angle in a timestamped output directory

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

Place `.md` files in `USER-FILES/04.INPUT/`. Each file must have:

- **Scene lines**: Scene description — narrative text describing characters, environment, and which reference images correspond to which characters. May span multiple lines before the first image; lines matching a Markdown embed/link (`![alt](url)`, `[text](url)`) or a URL (`http://`, `https://`, `www.`) are skipped and logged
- **First image line**: Original image — first Markdown image link (the main scene image)
- **Checkbox section**: One checkbox per available angle (see below for format)
- **Remaining lines**: Reference images — character reference sheet Markdown image links

Example (`prompt01.md`):

```md
Interior of a sedan at dusk. A man in a dark coat drives, hands on the steering wheel. A woman in a red scarf sits in the passenger seat. The dashboard radio glows between the two front seats.

![master](https://example.com/car-interior.jpeg)

```yaml shot-sheet
scene_type: vehicle_interior
shot_size: MS
camera_height: eye
subject_count: 2
subjects:
- id: S1
  description: the man in the dark coat driving
  position: driver's seat, frame left
  facing: forward
  face_visible: true
  occluded: false
props: []
lighting: warm dusk light
notes: ''
```

```yaml shot-plan
- id: SH01
  label: CU on the woman
  intent: Punch in on the woman in the red scarf, chest up, eye level.
  subject_ids: [S2]
  grounds: []
  recommended: true
  reason: her face is unoccluded and clearly visible in the master
```

### Recommended
- [x] SH01 — CU on the woman {}

![image](https://example.com/woman-ref.png)
```

### Shot Selection via `--plan`

There is no fixed angle list. `--plan` sends the scene image to the model, which proposes a shot sheet and a shot list — including prop and detail inserts (radio, hands, eyes) that a generic angle vocabulary could never express. The enriched MD lands in a timestamped `SHOT-PLAN` output directory; **`04.INPUT/` is never modified**.

**Review gate:** copy the enriched MD into `04.INPUT/` and edit it:
- tick (`- [x]`) the shots to run; untick the rest
- shots the model cannot ground are listed unticked under `### Possible` with a stated reason — you may still tick them deliberately
- the braces (`{A1}`) select which declared assets ground the shot; `{}` = master only

**Validation rules:**
- Every ticked shot id must exist in that file's `shot-plan` block. Unknown ids hard-fail.
- Files without a shot-plan block hard-fail — run `--plan` on them first.
- If all checkboxes are unchecked, the file is skipped — the raw `.md` is copied to the output directory as-is.
- Only ticked shots generate API calls and output files.

## CLI Commands

```bash
# List available profiles
python -m src.main --list-profiles

# Process files with a specific profile
python -m src.main --profile kimi-k2-thinking_temp0.5_REAL-TIME.yaml

# Use a custom input directory
python -m src.main --profile <name> --input-dir /path/to/mds

# Dry run — set up config and output dir without API calls
python -m src.main --profile <name> --dry-run

# Cost estimate only (uses token counting API, no generation)
python -m src.main --profile <name> --cost-only

# Generate shot sheet + shot list (one vision call per file)
python -m src.main --profile <name> --plan

# Selftest — verify the model receives images and sees left/right correctly
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

## Shot Planning

There is no fixed angle list. `--plan` has the model look at the image and propose the shot list itself: a shot sheet (scene type, frame size, camera height, subject roster, props, lighting) plus a shot list where every shot carries a label, an intent written as concrete prose, and a `recommended` flag with a stated reason. Shots the model cannot ground (occluded subjects, faces not visible) are listed unticked under `### Possible`.

## Output Format

Output directories are timestamped and never overwritten:

```
USER-FILES/05.OUTPUT/260524_052133_kimi-k2-thinking_RT_temp0.5_MULTI-ANGLE-MD/
├── prompt01/
│   ├── prompt01_SH01_CU_on_the_woman.md   ← only ticked shots
│   └── ... (only the shots you ticked)
├── prompt02.md                            ← all-unchecked file, copied as-is
└── summary_report.md
```

Each output `.md` file contains the AI-generated reframing prompt (60–90 words, ending with the preservation clause), a blank line, then the master image embed followed by only the grounding reference embeds for that shot. Files with no ticked shots are copied verbatim into the output directory.

## Cost Estimation

```bash
# Full dry run (no API calls at all)
python -m src.main --profile <name> --dry-run

# Cost estimate only (uses token counting API)
python -m src.main --profile <name> --cost-only
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
| `No checkbox section found` | Run `--plan` to generate the shot list and checkbox section |
| `No shot-plan block` | Run `--plan` on the file — legacy template files must be re-planned |
| `Invalid checkbox entries` | Run `--plan` to regenerate the shot list and checkbox section |
