"""Main entry point for multi-angle MD processing tool."""

import argparse
from pathlib import Path
from loguru import logger
import sys

from .config import load_strict_config, get_output_directory
from .cli_handler import CLIHandler
from .md_input_parser import discover_md_files
from .exceptions import ConfigurationError, FileProcessingError


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Process MD files with AI for multi-angle reframing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--profile",
        type=str,
        help="Profile filename to use (e.g., haiku_4.5_0.3_REAL-TIME.yaml)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Run without making API calls")
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="Send a test image to the API and verify left/right vision, then exit",
    )
    parser.add_argument(
        "--cost-only",
        action="store_true",
        help="Estimate costs only using token counting API",
    )
    parser.add_argument(
        "--plan",
        action="store_true",
        help="Generate adaptive shot sheets + checkbox lists (one vision call per file) "
        "into a SHOT-PLAN output directory; never writes into 04.INPUT",
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

    parser.add_argument(
        "--batch-id", type=str, help="Check status or fetch results for an existing batch"
    )
    parser.add_argument("--list-batches", action="store_true", help="List recent batches")
    parser.add_argument(
        "--wait", action="store_true", help="Wait for batch completion (use with batch mode)"
    )

    return parser.parse_args()


def validate_profile_selection(args):
    """Validate profile selection and determine which profile to use.

    Args:
        args: Parsed command line arguments

    Returns:
        Profile filename to use, or None for auto-detection

    Raises:
        SystemExit: If profile selection is invalid
    """
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
        profile_path = profiles_dir / args.profile
        if not profile_path.exists():
            logger.error(f"Profile not found: {args.profile}")
            logger.info(f"Available profiles: {', '.join(p.name for p in yaml_files)}")
            sys.exit(1)
        return args.profile

    if len(yaml_files) == 1:
        logger.info(f"Auto-detected single profile: {yaml_files[0].name}")
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
    """Load and validate configuration.

    Args:
        args: Parsed command line arguments

    Returns:
        Loaded configuration dictionary
    """
    try:
        profile_name = validate_profile_selection(args)
        config = load_strict_config(profile_name)

        if "profile_metadata" in config:
            metadata = config["profile_metadata"]
            logger.info(f"Using profile: {metadata.get('profile_name', 'Unknown')}")
            if metadata.get("description"):
                logger.info(f"Description: {metadata['description']}")

        return config

    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        raise ConfigurationError(f"Failed to load configuration: {e}") from e


def discover_mds(args):
    """Discover MD files based on arguments.

    Args:
        args: Parsed command line arguments

    Returns:
        Tuple of (list of MD file paths, input directory path)
    """
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

    handler = CLIHandler(config)

    if handler.handle_batch_operations(args):
        return

    md_files, input_dir = discover_mds(args)
    if not md_files:
        logger.warning(f"No MD files found in {args.input_dir or 'USER-FILES/04.INPUT/'}")
        return

    if args.plan:
        output_dir = get_output_directory(config, suffix="SHOT-PLAN")
        from .shot_planner import run_plan_mode

        run_plan_mode(config, md_files, output_dir)
        return

    output_dir = get_output_directory(config, suffix="MULTI-ANGLE-MD")

    if args.cost_only:
        handler.handle_cost_estimation(md_files, output_dir)
    elif handler.batch_mode:
        handler.handle_batch_submission(md_files, args)
    else:
        handler.handle_realtime_processing(md_files, output_dir, input_dir, args.dry_run)


if __name__ == "__main__":
    main()
