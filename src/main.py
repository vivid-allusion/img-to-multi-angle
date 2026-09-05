"""Main entry point for multi-angle MD processing tool."""

import argparse
from pathlib import Path
from loguru import logger
import sys

from .config import load_strict_config, get_output_directory
from .cli_handler import CLIHandler
from .md_input_parser import discover_md_files
from .exceptions import ConfigurationError, FileProcessingError
from .reporting import setup_cli_logging


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Direct multi-angle cinematic reframing from Markdown scene inputs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--profile",
        type=str,
        help="Profile filename to use (e.g., gemini-3.7-flash_temp0.2_REAL-TIME.yaml)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Run without making API calls")
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="Send a test image to the API and verify vision orientation, then exit",
    )
    parser.add_argument(
        "--cost-only",
        action="store_true",
        help="Estimate costs only using token counting",
    )
    parser.add_argument(
        "--list-profiles", action="store_true", help="List available profiles and exit"
    )
    parser.add_argument(
        "--input-dir",
        "-i",
        type=str,
        help="Override input directory (default: USER-FILES/04.INPUT)",
    )

    return parser.parse_args()


def validate_profile_selection(args):
    """Validate profile selection and determine which profile to use."""
    profiles_dir = Path("USER-FILES/03.PROFILES")

    if not profiles_dir.exists():
        logger.error("Profiles directory not found: USER-FILES/03.PROFILES/")
        sys.exit(1)

    yaml_files = list(profiles_dir.glob("*.yaml"))

    if not yaml_files:
        logger.error("No profile files found in USER-FILES/03.PROFILES/")
        logger.error("Create a profile file first")
        sys.exit(1)

    if args.profile:
        profile_name = args.profile if args.profile.endswith(".yaml") else f"{args.profile}.yaml"
        profile_path = profiles_dir / profile_name
        if not profile_path.exists():
            logger.error(f"Profile not found: {profile_name}")
            logger.info(f"Available profiles: {', '.join(p.name for p in yaml_files)}")
            sys.exit(1)
        return profile_name

    if len(yaml_files) == 1:
        return yaml_files[0].name

    logger.error("Multiple profiles found in USER-FILES/03.PROFILES/")
    logger.error("You must specify which profile to use with --profile")
    logger.error("")
    logger.error("Available profiles:")
    for yaml_file in sorted(yaml_files):
        logger.error(f"  {yaml_file.name}")
    logger.error("")
    logger.error("Usage: python3 -m src.main --profile <profile_name>")
    sys.exit(1)


def load_configuration(args):
    """Load and validate configuration."""
    try:
        profile_name = validate_profile_selection(args)
        config = load_strict_config(profile_name)

        if "profile_metadata" in config:
            metadata = config["profile_metadata"]
            logger.info(f"Using profile: {metadata.get('profile_name', 'Unknown')} ({config.get('model')})")

        return config

    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        raise ConfigurationError(f"Failed to load configuration: {e}") from e


def discover_mds(args):
    """Discover MD files based on arguments."""
    if args.input_dir:
        input_path = Path(args.input_dir)
        if not input_path.exists():
            logger.error(f"Input directory not found: {input_path}")
            raise FileProcessingError(f"Input directory not found: {input_path}")
        return discover_md_files(input_path), input_path
    else:
        input_path = Path("USER-FILES/04.INPUT")
        return discover_md_files(input_path), input_path


def _maybe_run_selftest(config) -> None:
    """Run the vision selftest first during dry-run, if an API key is available."""
    try:
        from .auth import get_api_key

        api_key = get_api_key()
    except SystemExit:
        logger.info("No API key available — skipping selftest in dry-run")
        return

    from openrouter import OpenRouter
    from .selftest import run_selftest

    run_selftest(OpenRouter(api_key=api_key), config)


def main():
    """Main entry point."""
    setup_cli_logging()
    args = parse_arguments()

    if args.list_profiles:
        handler = CLIHandler({})
        handler.handle_profile_listing()
        return

    config = load_configuration(args)

    if args.selftest:
        from .auth import get_api_key
        from openrouter import OpenRouter
        from .selftest import run_selftest

        run_selftest(OpenRouter(api_key=get_api_key()), config)
        return

    if args.dry_run and not args.cost_only:
        _maybe_run_selftest(config)

    md_files, input_dir = discover_mds(args)

    output_dir = get_output_directory(config, suffix="MULTI-ANGLE-MD")
    handler = CLIHandler(config)

    if args.cost_only:
        handler.handle_cost_estimation(md_files, output_dir)
    else:
        handler.handle_realtime_processing(md_files, output_dir, input_dir, args.dry_run)


if __name__ == "__main__":
    main()
