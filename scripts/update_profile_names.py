#!/usr/bin/env python3
"""Update profile_name field in all profile YAML files."""

import yaml
from pathlib import Path

profiles_dir = Path("USER-FILES/03.PROFILES")

for yaml_file in profiles_dir.glob("*.yaml"):
    with open(yaml_file, 'r') as f:
        data = yaml.safe_load(f)
        data['metadata']['profile_name'] = yaml_file.stem
        with open(yaml_file, 'w') as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)
        print(f"Updated: {yaml_file.name}")

print(f"✅ Updated {len(list(profiles_dir.glob('*.yaml')))} profiles")
