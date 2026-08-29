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
    - shot_planner: --plan mode (shot sheet + shot list generation)
    - md_input_parser: MD file discovery and parsing
    - api_client: OpenRouter API interaction
    - cost_calculator: Token usage and cost tracking
    - reporting: Summary and failure reporting
    - auth: API key management via env vars / pass / .env

"""

__version__ = "5.0.0"
