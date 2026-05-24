#!/usr/bin/env python3
"""1Password CLI authentication for API."""

import os
import shutil
import subprocess
import sys
from loguru import logger

from .exceptions import APIAuthenticationError

OP_CLI = shutil.which("op")


def ensure_op_auth() -> None:
    """
    Ensures 1Password CLI is authenticated.
    
    Checks if session is active, if not triggers interactive sign-in.
    """
    if not OP_CLI:
        raise FileNotFoundError("1Password CLI not found. Please install it.")

    try:
        subprocess.run(
            [OP_CLI, "account", "get"],
            check=True,
            capture_output=True,
            timeout=10
        )
        return
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        logger.info("🔐 1Password session expired or not found. Signing in...")
        
    try:
        signin_process = subprocess.Popen(
            [OP_CLI, "signin"],
            stdout=subprocess.PIPE,
            stderr=sys.stderr,
            stdin=sys.stdin,
            text=True,
        )
        stdout, _ = signin_process.communicate(timeout=60)

        if signin_process.returncode != 0:
            raise APIAuthenticationError("Failed to authenticate with 1Password during sign-in.")

        if stdout:
            for line in stdout.strip().split("\n"):
                if line.startswith("export "):
                    line = line.replace("export ", "")
                    key, value = line.split("=", 1)
                    value = value.strip('"')
                    os.environ[key] = value
        logger.info("1Password sign-in successful.")
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        logger.error("❌ Failed to authenticate with 1Password.")
        if isinstance(e, subprocess.CalledProcessError) and e.stderr:
            logger.error(f"1Password CLI error:\n{e.stderr}")
        raise APIAuthenticationError("Failed to authenticate with 1Password") from e


def get_api_key() -> str:
    """
    Retrieve API key from 1Password CLI or environment variable.
    
    Priority order:
    1. OPENROUTER_API_KEY environment variable
    2. 1Password CLI: op item get "API OpenRouter" --field "Api Key"
    
    Returns:
        str: The API key
        
    Raises:
        APIAuthenticationError: If authentication fails
    """
    env_key = os.environ.get("OPENROUTER_API_KEY")
    if env_key:
        logger.info("✅ Using API key from OPENROUTER_API_KEY environment variable")
        return env_key
    
    try:
        ensure_op_auth()
        
        logger.info("Retrieving API key from 1Password...")
        result = subprocess.run(
            [OP_CLI, "item", "get", "yaffe3j6jujz2uiukiw7sjycpe", "--field", "Api Key"],
            capture_output=True,
            text=True,
            check=True,
            timeout=30
        )
        api_key = result.stdout.strip()
        
        if not api_key:
            raise APIAuthenticationError("Empty API key received from 1Password")
            
        logger.info("✅ Successfully retrieved API key from 1Password")
        return api_key
        
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ 1Password item retrieval failed: {e.stderr}")
        raise APIAuthenticationError(f"1Password item retrieval failed: {e.stderr}") from e
    except subprocess.TimeoutExpired as e:
        logger.error("❌ 1Password CLI timeout")
        raise APIAuthenticationError("1Password CLI timeout") from e
    except FileNotFoundError as e:
        logger.error("❌ 1Password CLI not found. Please install 'op' command.")
        raise APIAuthenticationError("1Password CLI not found") from e