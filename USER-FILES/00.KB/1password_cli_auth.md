# 1Password CLI Authentication with Python: An LLM Instruction Manual

This document provides a guide for setting up and using the 1Password CLI tool within a Python script to handle authentication programmatically.

## 1. Prerequisites

Before using this script, ensure the following conditions are met:

1.  **1Password CLI Installed**: The `op` command-line tool must be installed and available in the system's `PATH`.
2.  **1Password Account**: You must have a 1Password account configured with the CLI.
3.  **Python Environment**: A Python environment (3.7+) is required.
4.  **Loguru Library**: The example uses the `loguru` library for clear logging. Install it via pip:
    ```bash
    pip install loguru
    ```

## 2. The Authentication Module

The following Python code provides a self-contained module for ensuring that the 1Password CLI is authenticated. If the session has expired or does not exist, it will trigger the interactive sign-in process for the user.

```python
import os
import shutil
import subprocess
import sys

# This example uses loguru for logging.
# You would need to install it: pip install loguru
from loguru import logger

OP_CLI = shutil.which("op")


class AuthError(Exception):
    """Custom exception for authentication errors."""
    pass


def ensure_op_auth() -> None:
    """
    Ensures 1Password CLI is authenticated, handling the interactive sign-in
    process by capturing the session token from stdout.

    This function is intended as a self-contained example of how to programmatically
    interact with the 1Password CLI for authentication.
    """
    if not OP_CLI:
        raise FileNotFoundError("1Password CLI not found. Please install it.")

    try:
        # First, a lightweight check to see if we're already signed in.
        subprocess.run(
            [OP_CLI, "account", "get"], check=True, capture_output=True, timeout=10
        )
        logger.debug("1Password session is active.")
        return
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        logger.info("🔐 1Password session expired or not found. Signing in...")
        try:
            # The 'op signin' command prompts on stderr and prints the session
            # key to stdout. We need to let the user see the prompt and type
            # their password.
            signin_process = subprocess.Popen(
                [OP_CLI, "signin"],
                stdout=subprocess.PIPE,
                stderr=sys.stderr,  # Pass through to the user's terminal
                stdin=sys.stdin,  # Allow the user to type their password
                text=True,
            )
            stdout, _ = signin_process.communicate(timeout=60)

            if signin_process.returncode != 0:
                raise AuthError("Failed to authenticate with 1Password during sign-in.")

            # The output of `op signin` is a shell command like:
            # export OP_SESSION_my_account="..."
            # We parse it and set the environment variable in our own process.
            if stdout:
                for line in stdout.strip().split("\n"):
                    if line.startswith("export "):
                        line = line.replace("export ", "")
                        key, value = line.split("=", 1)
                        value = value.strip('"')  # Remove quotes
                        os.environ[key] = value
                        logger.debug(f"Set 1Password session variable: {key}")
            logger.info("✅ 1Password sign-in successful.")
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
            logger.error("❌ Failed to authenticate with 1Password.")
            if isinstance(e, subprocess.CalledProcessError) and e.stderr:
                logger.error(f"1Password CLI error:\n{e.stderr}")
            raise AuthError("Failed to authenticate with 1Password") from e
```

## 3. How the Script Works

1.  **Check for `op` CLI**: It first verifies that the `op` executable is available.
2.  **Check Session Status**: It runs a fast, non-interactive command (`op account get`) to check if an active session already exists.
3.  **Initiate Interactive Sign-in**: If the session check fails, it assumes the user is not logged in. It then starts the `op signin` process.
    -   `stdin`, `stdout`, and `stderr` are carefully managed to allow the user to interact with the password prompt directly in their terminal.
4.  **Capture Session Token**: After a successful sign-in, the `op` CLI outputs a session token to `stdout` (e.g., `export OP_SESSION_my_account="..."`). The script captures this output.
5.  **Set Environment Variable**: The script parses the session token and sets it as an environment variable within the current Python process (`os.environ`). This makes the session available to subsequent `op` commands run from the script.

## 4. How to Use in a Project

To use this functionality, simply import the `ensure_op_auth` function and call it before any code that needs to interact with the 1Password CLI.

### Example Usage:

```python
from 1password_auth import ensure_op_auth, AuthError
import subprocess

def get_secret(item_name: str, field_name: str) -> str:
    """
    A function that retrieves a secret from 1Password after ensuring
    authentication.
    """
    try:
        ensure_op_auth()
        secret = subprocess.check_output(
            ["op", "item", "get", item_name, "--field", field_name],
            text=True
        ).strip()
        return secret
    except AuthError as e:
        print(f"Authentication failed: {e}")
        return ""
    except subprocess.CalledProcessError as e:
        print(f"Could not retrieve secret: {e}")
        return ""

# Example call
api_key = get_secret("My API Service", "api_key")
if api_key:
    print("Successfully retrieved API key.")
``` 