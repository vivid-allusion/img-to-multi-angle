"""Multi-Angle MD Processor Package

A tool for processing Markdown files with AI to generate multi-angle reframed outputs.

Main entry point:
    python -m src.main

Configuration:
    - profiles: YAML profiles in USER-FILES/03.PROFILES/
    - config: Configuration files in USER-FILES/01.CONFIG/

Core Modules:
    - main: CLI entry point and argument parsing
    - config: Configuration loading and validation
    - profile_manager: Profile loading and application
    - multi_angle_orchestrator: Main processing workflow
    - shot_planner: Dynamic vision-based shot planning
    - shot_generator: Per-shot prompt generation with banned-word retry
    - md_input_parser: MD file discovery and parsing
    - api_client: OpenRouter API interaction
    - cost_calculator: Token cost estimation for --cost-only
    - reporting: Summary and failure reporting
    - auth: API key management via env vars / pass / .env

"""

__version__ = "5.0.0"
