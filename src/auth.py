"""Authentication module — 4-tier env var hierarchy.

Priority:
    1. Already-set env var (injected by OpenReel TUI or cloud wrapper)
    2. pass show openreel/<key> (GPG-encrypted, optional)
    3. .env file in project root (standalone mode)
    4. Hard exit if no key found
"""

import os
import sys
import subprocess
from pathlib import Path
from typing import Optional
from loguru import logger
from dotenv import load_dotenv

REQUIRED_KEY = "OPENROUTER_API_KEY"


def _try_pass(key_name: str) -> Optional[str]:
    try:
        result = subprocess.run(
            ["pass", "show", f"openreel/{key_name}"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            logger.info("Retrieved {} from pass", key_name)
            return result.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        pass
    return None


def get_api_key() -> str:
    api_key = os.getenv(REQUIRED_KEY)
    if api_key:
        logger.info("Using {} from environment", REQUIRED_KEY)
        return api_key

    api_key = _try_pass(REQUIRED_KEY.lower())
    if api_key:
        os.environ[REQUIRED_KEY] = api_key
        return api_key

    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        api_key = os.getenv(REQUIRED_KEY)
        if api_key:
            logger.info("Loaded {} from {}", REQUIRED_KEY, env_path)
            return api_key

    sys.exit(
        "ERROR: OPENROUTER_API_KEY not set.\n"
        "  - Set as env var  (export OPENROUTER_API_KEY=...)\n"
        "  - Store in pass   (pass insert openreel/openrouter_api_key)\n"
        "  - Add to .env     (echo OPENROUTER_API_KEY=... > .env)"
    )


__all__ = ["get_api_key"]
