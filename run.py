#!/usr/bin/env python3
"""Run the text processing tool with automatic dependency installation."""

import sys
import subprocess
from pathlib import Path


def in_virtualenv() -> bool:
    """Check if we're in a virtual environment."""
    return hasattr(sys, 'real_prefix') or (
        hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix
    )


def check_dependencies() -> bool:
    """Check if all required dependencies are installed."""
    requirements = [
        ("openrouter", "openrouter"),
        ("yaml", "pyyaml"),
        ("loguru", "loguru"),
        ("natsort", "natsort"),
    ]
    
    for module, _ in requirements:
        try:
            __import__(module)
        except ImportError:
            return False
    
    return True


def install_requirements() -> bool:
    """Install requirements from requirements.txt."""
    requirements_file = Path(__file__).parent / "requirements.txt"
    
    if not requirements_file.exists():
        print(f"Error: {requirements_file} not found")
        return False
    
    print("Installing dependencies...")
    try:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "-r", str(requirements_file)]
        )
        print("✓ Dependencies installed successfully!\n")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Failed to install dependencies: {e}")
        return False


def create_venv(venv_path: Path) -> bool:
    """Create a virtual environment."""
    print(f"Creating virtual environment at {venv_path}...")
    try:
        subprocess.check_call([sys.executable, "-m", "venv", str(venv_path)])
        print("✓ Virtual environment created!\n")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Failed to create virtual environment: {e}")
        return False


def ensure_venv_and_run():
    """Ensure we're in a virtual environment and run the app.

    If not in a venv, creates one, re-invokes this script within it,
    and exits. If already in a venv, returns immediately so the
    caller can proceed with dependency checks and main execution.
    """
    if not in_virtualenv():
        venv_path = Path(__file__).parent / "venv"
        venv_python = venv_path / "bin" / "python"

        if not venv_python.exists():
            if not create_venv(venv_path):
                sys.exit(1)

        result = subprocess.run([str(venv_python), __file__] + sys.argv[1:])
        sys.exit(result.returncode)
    # Already in venv — return to caller for dependency check


def _run_app():
    """Check dependencies and run the application."""
    if not check_dependencies():
        if not install_requirements():
            sys.exit(1)

    from src.main import main
    sys.exit(main())


if __name__ == "__main__":
    ensure_venv_and_run()
    _run_app()
