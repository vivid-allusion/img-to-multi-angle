#!/usr/bin/env python3
"""Generate self-contained profile files from models.yaml."""

import yaml
from pathlib import Path
from typing import Dict, Any
from datetime import datetime


def write_profile_with_comments(profile_path: Path, profile_data: Dict[str, Any], temp: float):
    """Write profile with helpful comments."""
    
    with open(profile_path, 'w') as f:
        f.write("# =============================================================================\n")
        f.write("# PROFILE METADATA\n")
        f.write("# =============================================================================\n")
        f.write(yaml.dump({'metadata': profile_data['metadata']}, default_flow_style=False, sort_keys=False))
        
        f.write("\n# =============================================================================\n")
        f.write("# MODEL CONFIGURATION\n")
        f.write("# =============================================================================\n")
        f.write("# Full OpenRouter endpoint - change this to use a different model\n")
        f.write(yaml.dump({'model': profile_data['model']}, default_flow_style=False, sort_keys=False))
        
        f.write("\n# =============================================================================\n")
        f.write("# PRICING (per million tokens)\n")
        f.write("# =============================================================================\n")
        f.write("# Update these values if OpenRouter pricing changes\n")
        f.write(yaml.dump({'pricing': profile_data['pricing']}, default_flow_style=False, sort_keys=False))
        
        f.write("\n# =============================================================================\n")
        f.write("# PROCESSING MODE\n")
        f.write("# =============================================================================\n")
        f.write("# batch_mode: true = 50% discount, results within 24 hours\n")
        f.write("# batch_mode: false = real-time processing, standard pricing\n")
        f.write(yaml.dump({'batch_mode': profile_data['batch_mode']}, default_flow_style=False, sort_keys=False))
        
        f.write("\n# =============================================================================\n")
        f.write("# MODEL PARAMETERS\n")
        f.write("# =============================================================================\n")
        f.write("# Alternative temperatures:\n")
        if temp != 0.3:
            f.write(f"# temperature: 0.3  # More deterministic, less creative\n")
        if temp != 0.5:
            f.write(f"# temperature: 0.5  # Balanced creativity\n")
        if temp != 0.7:
            f.write(f"# temperature: 0.7  # More creative, less deterministic\n")
        if temp != 0.9:
            f.write(f"# temperature: 0.9  # High creativity\n")
        f.write("#\n")
        f.write("# Alternative max_tokens:\n")
        f.write("# max_tokens: 4000   # Shorter responses, lower cost\n")
        f.write("# max_tokens: 8000   # Current setting\n")
        f.write("# max_tokens: 16000  # Longer responses, higher cost\n")
        f.write("#\n")
        f.write(yaml.dump({'parameters': profile_data['parameters']}, default_flow_style=False, sort_keys=False))
        
        f.write("\n# =============================================================================\n")
        f.write("# SYSTEM PROMPT (Optional)\n")
        f.write("# =============================================================================\n")
        f.write("# Uncomment to override the default system_prompt.md:\n")
        f.write("# system_prompt: |\n")
        f.write("#   You are a helpful assistant specialized in...\n")
        f.write("#   Add your custom system prompt here.\n")
        f.write("\n")
        
        f.write("# =============================================================================\n")
        f.write("# PROFILE STATUS\n")
        f.write("# =============================================================================\n")
        f.write("# Set to false to disable this profile\n")
        f.write(yaml.dump({'enabled': profile_data['enabled']}, default_flow_style=False, sort_keys=False))


def generate_profiles():
    """Generate profile files for all models in models.yaml."""
    models_file = Path("USER-FILES/01.CONFIG/models.yaml")
    profiles_dir = Path("USER-FILES/03.PROFILES")
    
    with open(models_file) as f:
        models_config = yaml.safe_load(f)
    
    models = models_config.get('models', {})
    pricing = models_config.get('pricing', {})
    batch_pricing = models_config.get('batch_pricing', {})
    
    for nickname, model_info in models.items():
        endpoint = model_info.get('endpoint', nickname)
        description = model_info.get('description', '')
        context_window = model_info.get('context_window', 200000)
        supports_batching = model_info.get('supports_batching', True)
        
        model_pricing = pricing.get(nickname, {})
        model_batch_pricing = batch_pricing.get(nickname, {})
        
        version = extract_version(endpoint)
        
        for temp in [0.3, 0.5, 0.7]:
            for mode in ['REAL-TIME', 'BATCH']:
                if mode == 'BATCH' and not supports_batching:
                    continue
                
                profile_name = f"{nickname}_{version}_temp{temp}_{mode}.yaml"
                profile_data = create_profile(
                    nickname=nickname,
                    version=version,
                    endpoint=endpoint,
                    description=description,
                    temp=temp,
                    mode=mode,
                    context_window=context_window,
                    supports_batching=supports_batching,
                    pricing=model_pricing,
                    batch_pricing=model_batch_pricing
                )
                
                profile_path = profiles_dir / profile_name
                write_profile_with_comments(profile_path, profile_data, temp)
                
                print(f"✓ Generated {profile_name}")


def extract_version(endpoint: str) -> str:
    """Extract version number from endpoint."""
    parts = endpoint.split('/')
    if len(parts) > 1:
        model_part = parts[1]
        version_parts = [p for p in model_part.split('-') if p.replace('.', '').isdigit()]
        if version_parts:
            return version_parts[0]
    return "1.0"


def create_profile(
    nickname: str,
    version: str,
    endpoint: str,
    description: str,
    temp: float,
    mode: str,
    context_window: int,
    supports_batching: bool,
    pricing: Dict[str, Any],
    batch_pricing: Dict[str, Any]
) -> Dict[str, Any]:
    """Create profile dictionary."""
    
    mode_name = "REAL-TIME" if mode == "REAL-TIME" else "BATCH"
    profile_name = f"{nickname}_{version}_{temp}_{mode_name}"
    
    real_time_pricing = format_pricing(pricing)
    batch_pricing_formatted = format_pricing(batch_pricing) if batch_pricing else None
    
    profile = {
        'metadata': {
            'profile_name': profile_name,
            'description': description,
            'created': datetime.now().strftime('%Y-%m-%d'),
            'version': '1.0'
        },
        'model': {
            'endpoint': endpoint,
            'nickname': nickname,
            'capabilities': {
                'context_window': context_window,
                'supports_batching': supports_batching,
                'supports_caching': False,
                'supports_thinking': False
            }
        },
        'pricing': {
            'real_time': real_time_pricing
        },
        'batch_mode': mode == 'BATCH',
        'parameters': {
            'temperature': temp,
            'max_tokens': 8000
        },
        'enabled': True
    }
    
    if batch_pricing_formatted and supports_batching:
        profile['pricing']['batch'] = batch_pricing_formatted
    
    return profile


def format_pricing(pricing_data: Dict[str, Any]) -> Dict[str, float]:
    """Format pricing data to simple input/output format."""
    if not pricing_data:
        return {'input': 0.0, 'output': 0.0}
    
    if isinstance(pricing_data.get('input'), dict):
        input_cost = pricing_data['input'].get('under_200k', 0.0)
    else:
        input_cost = pricing_data.get('input', 0.0)
    
    output_cost = pricing_data.get('output', 0.0)
    
    return {'input': float(input_cost), 'output': float(output_cost)}


if __name__ == '__main__':
    print("Generating self-contained profile files...")
    generate_profiles()
    print("\n✅ Profile generation complete!")
