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

- **Line 1**: Scene description — narrative text describing characters, environment, and which reference images correspond to which characters
- **Line 2**: Original image — first Markdown image link (the main scene image)
- **Checkbox section**: One checkbox per available angle (see below for format)
- **Remaining lines**: Reference images — character reference sheet Markdown image links

Example (`prompt01.md`):

```md
Anchorage bar. Close on a Tlingit bartender and a Hasidic Jew sitting across one another inside a dimly lit, early 20th-century tavern. On the left, the large-framed bartender with long dark hair and a thick beard leans over the wooden counter. To the right, the Hasidic man, featuring a graying beard, payot, a black wide-brimmed hat, and a weathered dark coat, reaches toward a shot glass on the bar. The provided image called allen.png shows you what the Hasidic Jew looks like. The provided image edensaw.jpeg shows what the Tlingit bartender looks like.

![image](https://example.com/bar-scene.jpeg)
- [ ] Birds Eye View
- [x] Close Up
- [ ] Crane Jib Shot
- [ ] Dutch Angle
- [ ] Establishing Shot
- [ ] Extreme Close Up
- [ ] Handheld Shaky Cam
- [ ] High Angle
- [ ] Low Angle
- [ ] Macro Shot
- [ ] Over The Shoulder
- [ ] Point Of View Pov
- [ ] Rack Focus
- [ ] Static Shot
- [ ] Tracking Dolly Shot
- [ ] Two Shot
- [ ] Wide Shot
![image](https://example.com/allen.png)
![image](https://example.com/edensaw.jpeg)
```

### Angle Selection via Checkboxes

The script reads available angles dynamically from `USER-FILES/01.CONFIG/angle-templates/`. Each `.txt` file in that directory becomes one checkbox line in the input file.

**Checkbox format:**
- `- [ ] Angle Name` — unchecked (this angle will NOT be processed)
- `- [x] Angle Name` or `- [X] Angle Name` — checked (this angle WILL be processed)
- The angle name must exactly match a `.txt` filename (underscores replaced with spaces)

**Validation rules:**
- Every input file MUST have a checkbox section. Missing checkboxes cause a hard fail.
- All checkbox labels must match existing `.txt` files in `angle-templates/`. Invalid labels cause a hard fail.
- If all checkboxes are unchecked, the file is skipped — the raw `.md` is copied to the output directory as-is.
- Only checked angles generate API calls and output files.

**To add or refresh checkboxes:** Run your MD files through the `add-multi-checkboxes` tool, which reads the current `angle-templates/` directory and inserts the correct checkbox block into each file.

## CLI Commands

```bash
# List available profiles
python -m src.main --list-profiles

# Process files with a specific profile
python -m src.main --profile kimi-k2-thinking_temp0.5_REAL-TIME.yaml

# Use a custom input directory
python -m src.main --profile <name> --input-dir /path/to/mds

# Dry run — estimate costs without making API calls
python -m src.main --profile <name> --dry-run

# Cost estimate only (uses token counting API, no generation)
python -m src.main --profile <name> --cost-only

# Submit as a batch request (requires batch_mode: true in profile)
python -m src.main --profile <name>

# Check batch status
python -m src.main --batch-id <batch_id>

# Wait for batch completion and fetch results
python -m src.main --batch-id <batch_id> --wait

# List recent batches
python -m src.main --list-batches
```

## Configuration

### Directory Structure

```
USER-FILES/
├── 01.CONFIG/
│   ├── openrouter_config.yaml    # Base settings (batch, cache, processing)
│   ├── system_prompt.md          # System prompt with few-shot examples
│   ├── user_message.md           # User message template with placeholders
│   └── angle-templates/          # 17 .txt files, one per camera angle
├── 03.PROFILES/
│   └── *.yaml                    # Model profiles
├── 04.INPUT/                     # Input .md files go here
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

batch_config:
  max_requests_per_batch: 10000
  check_interval_minutes: 5
  max_wait_hours: 24
  auto_download_results: true
  estimate_cost_before_submit: true
  cost_threshold_usd: 100

processing_options:
  trim_prompts: true
  normalize_spaces: true
  max_prompt_length: 1000
  max_response_length: 40000

cache_config:
  enabled: false
  cache_system_prompt: true
  cache_ttl: 5m
  report_cache_metrics: true

avg_output_tokens: 800
```

### Profile Files (`USER-FILES/03.PROFILES/*.yaml`)

Profiles define the model, pricing, and parameters. Naming convention: `{nickname}_temp{temperature}_{REAL-TIME|BATCH}.yaml`

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
    context_window: 128000
    supports_batching: true
    supports_caching: false
    supports_thinking: true

pricing:
  real_time:
    input: 0.6
    output: 2.5
  batch:
    input: 0.3
    output: 1.25

batch_mode: false

parameters:
  temperature: 0.5
  max_tokens: 8000

enabled: true
```

### Important Configuration Rules

- **No defaults policy** — all config fields must be explicitly defined; missing fields cause hard errors
- **No conflicts** — a setting cannot exist in both `openrouter_config.yaml` AND a profile file
- If only one profile exists, it is auto-detected; otherwise `--profile` is required

## Camera Angles

17 angle templates ship by default in `USER-FILES/01.CONFIG/angle-templates/`. The list is dynamic — add or remove `.txt` files to change available angles. The checkbox section in each input file is built from these filenames (underscores → spaces).

## Output Format

Output directories are timestamped and never overwritten:

```
USER-FILES/05.OUTPUT/260524_052133_kimi-k2-thinking_RT_temp0.5_MULTI-ANGLE-MD/
├── prompt01/
│   ├── prompt01_Close_Up.md          ← only checked angles
│   └── ... (only the angles you checked)
├── prompt02.md                        ← all-unchecked file, copied as-is
└── processing_log.txt
```

Each output `.md` file contains the AI-generated reframing prompt plus the original image URL and character reference URLs. Files with no checked angles are copied verbatim into the output directory.

## Batch Processing

Set `batch_mode: true` in a profile to use OpenRouter's Batch API:

- **50% cost discount** vs real-time processing
- Results arrive within 24 hours
- Submit with the normal `--profile` command
- Monitor with `--batch-id <id>` or `--wait`

```bash
# Submit batch
python -m src.main --profile kimi-k2-thinking_temp0.5_BATCH.yaml

# Check status
python -m src.main --batch-id batch_abc123

# Wait for completion and auto-download results
python -m src.main --batch-id batch_abc123 --wait
```

## Cost Estimation

```bash
# Full dry run (no API calls at all)
python -m src.main --profile <name> --dry-run

# Cost estimate only (uses token counting API)
python -m src.main --profile <name> --cost-only
```

Costs are calculated from: system prompt tokens + angle template tokens + estimated output tokens (from `avg_output_tokens` in config) × pricing rates in the profile.

## Troubleshooting

| Issue | Solution |
|---|---|
| `API key not found` | Set `OPENROUTER_API_KEY` env var or install 1Password CLI |
| `No profiles found` | Add a `.yaml` file to `USER-FILES/03.PROFILES/` |
| `Missing config field` | Ensure all required fields exist in `openrouter_config.yaml` |
| `Config conflict` | Remove duplicate settings — each key must be in config OR profile, not both |
| `system_prompt.md not found` | Ensure `USER-FILES/01.CONFIG/system_prompt.md` exists |
| `No angle templates found` | Ensure `USER-FILES/01.CONFIG/angle-templates/` contains `.txt` files |
| `No checkbox section found` | Run your MD files through the `add-multi-checkboxes` tool |
| `Invalid checkbox labels` | Refresh checkboxes with `add-multi-checkboxes` — angle templates may have changed |
