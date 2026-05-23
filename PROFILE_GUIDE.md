# Profile Guide

## Overview

Profiles are self-contained configuration files that define everything needed to run a specific AI model through OpenRouter. Each profile is like a "cartridge" that you pop into the system - it contains all the model information, pricing, and parameters.

## Profile Naming Convention

Profiles follow this naming pattern:
```
[nickname]_[version]_temp[temperature]_[MODE].yaml
```

Examples:
- `haiku_4.5_temp0.3_REAL-TIME.yaml` - Claude Haiku 4.5, temperature 0.3, real-time processing
- `haiku_4.5_temp0.3_BATCH.yaml` - Same model, but batch processing (50% discount)
- `gemini-flash_3_temp0.5_REAL-TIME.yaml` - Gemini Flash 3, temperature 0.5, real-time
- `grok_4.1_temp0.7_BATCH.yaml` - Grok 4.1, temperature 0.7, batch mode

## Profile Structure

Each profile contains these sections:

### 1. Metadata
```yaml
metadata:
  profile_name: "haiku_4.5_0.3_REAL-TIME"
  description: "Fastest and most cost-effective Claude model"
  created: "2026-03-06"
  version: "1.0"
```

### 2. Model Configuration
```yaml
model:
  endpoint: "anthropic/claude-haiku-4.5"  # Full OpenRouter endpoint
  nickname: "haiku"                        # Short name for display
  capabilities:
    context_window: 200000
    supports_batching: true
    supports_caching: false
    supports_thinking: false
```

### 3. Pricing (per million tokens)
```yaml
pricing:
  real_time:
    input: 0.40   # $0.40 per million input tokens
    output: 2.00  # $2.00 per million output tokens
  batch:          # 50% discount
    input: 0.20
    output: 1.00
```

### 4. Processing Mode
```yaml
batch_mode: false  # true = batch (50% discount), false = real-time
```

### 5. Parameters
```yaml
parameters:
  temperature: 0.3    # 0.0 = deterministic, 2.0 = creative
  max_tokens: 8000    # Maximum output length
```

### 6. System Prompt (Optional)
```yaml
# Uncomment to override default system_prompt.md:
# system_prompt: |
#   You are a helpful assistant specialized in...
#   Add your custom system prompt here.
```

### 7. Profile Status
```yaml
enabled: true  # Set to false to disable this profile
```

## Using Profiles

### List Available Profiles
```bash
python3 -m src.main --list-profiles
```

### Run with a Specific Profile
```bash
# Real-time processing
python3 -m src.main --profile haiku_4.5_0.3_REAL-TIME.yaml

# Batch processing (50% discount)
python3 -m src.main --profile haiku_4.5_0.3_BATCH.yaml
```

### Cost Estimation
```bash
python3 -m src.main --profile haiku_4.5_0.3_REAL-TIME.yaml --cost-only
```

## Creating a New Profile

### Step 1: Copy an Existing Profile
```bash
cd USER-FILES/03.PROFILES/
cp haiku_4.5_0.3_REAL-TIME.yaml mymodel_1.0_0.5_REAL-TIME.yaml
```

### Step 2: Edit the New Profile
```yaml
metadata:
  profile_name: "mymodel_1.0_0.5_REAL-TIME"  # Must match filename!
  description: "My custom model configuration"
  created: "2026-03-06"
  version: "1.0"

model:
  endpoint: "provider/model-name"  # Find at openrouter.ai/models
  nickname: "mymodel"
  capabilities:
    context_window: 128000
    supports_batching: true
    supports_caching: false
    supports_thinking: false

pricing:
  real_time:
    input: 1.00   # Check openrouter.ai for current pricing
    output: 3.00
  batch:
    input: 0.50
    output: 1.50

batch_mode: false
parameters:
  temperature: 0.5
  max_tokens: 8000

enabled: true
```

### Step 3: Test Your Profile
```bash
python3 -m src.main --profile mymodel_1.0_0.5_REAL-TIME.yaml --dry-run
```

## Available Models

### Anthropic Claude
- `haiku` - Fastest and most cost-effective
- `sonnet` - Balanced performance
- `opus` - Highest quality reasoning

### Google Gemini
- `gemini-flash` - Fast and efficient
- `gemini-pro` - Balanced
- `gemini-pro-extended` - Extended capabilities

### xAI
- `grok` - Fast Grok model

## Batch vs Real-Time

### Real-Time Processing
- Immediate results (seconds to minutes)
- Standard pricing
- Best for: Interactive use, testing, urgent needs

### Batch Processing
- 50% DISCOUNT on all API costs
- Results within 24 hours (often < 1 hour)
- Best for: Large datasets, non-urgent processing, cost optimization

To use batch mode, simply use a profile with `batch_mode: true` (or a `*_BATCH.yaml` profile).

## Temperature Guide

- **0.0 - 0.3**: Deterministic, consistent outputs (good for factual tasks)
- **0.4 - 0.7**: Balanced creativity (good for general use)
- **0.8 - 1.0**: Creative, varied outputs (good for brainstorming)
- **1.1 - 2.0**: Highly creative, unpredictable (experimental)

## Troubleshooting

### "Multiple profiles found"
If you have multiple profiles in `USER-FILES/03.PROFILES/`, you must specify which one to use:
```bash
python3 -m src.main --profile haiku_4.5_0.3_REAL-TIME.yaml
```

### "Profile not found"
Check that the profile filename matches exactly (including `.yaml` extension):
```bash
# Wrong
python3 -m src.main --profile haiku_4.5_0.3_REAL-TIME

# Right
python3 -m src.main --profile haiku_4.5_0.3_REAL-TIME.yaml
```

### "Missing required configuration"
All required fields must be present in the profile. Check the profile structure section above.

## Advanced: Custom System Prompts

Each profile can override the default system prompt:

```yaml
system_prompt: |
  You are a specialized assistant for analyzing scientific papers.
  
  Your role is to:
  1. Summarize key findings
  2. Identify methodology
  3. Note any limitations
  
  Be concise and technical.
```

## Advanced: Additional Parameters

You can add any OpenRouter-supported parameters:

```yaml
options:
  top_p: 0.9
  frequency_penalty: 0.5
  presence_penalty: 0.3
  stream: false
```

All parameters are passed directly to OpenRouter without filtering or validation.

## Profile Management

### Viewing Profile Details
```bash
cat USER-FILES/03.PROFILES/haiku_4.5_0.3_REAL-TIME.yaml
```

### Disabling a Profile
Edit the profile and set:
```yaml
enabled: false
```

### Generating New Profiles
Use the profile generator script:
```bash
python3 scripts/generate_profiles.py
```

This will create profiles for all models defined in `USER-FILES/01.CONFIG/models.yaml`.

## Best Practices

1. **Start with real-time profiles** for testing and development
2. **Switch to batch profiles** for production runs to save 50%
3. **Use descriptive metadata** so you remember what each profile is for
4. **Keep profiles version-controlled** alongside your code
5. **Test with --cost-only** before large batch runs
6. **Use lower temperatures** (0.3-0.5) for consistent outputs
7. **Use higher temperatures** (0.7-1.0) for creative tasks

## Model Agnosticism

The system is completely model-agnostic. Any model available on OpenRouter will work by simply creating a profile with the correct endpoint. No code changes needed.

To add a new model:
1. Find the model endpoint at openrouter.ai/models
2. Create a profile with that endpoint
3. Run with the new profile

That's it! The system will handle everything else.
