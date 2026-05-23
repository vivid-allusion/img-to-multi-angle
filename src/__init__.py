"""TXT Processor Package

A tool for processing text files with AI.

Main entry point:
    python -m src.main

Configuration:
    - profiles: YAML profiles in USER-FILES/03.PROFILES/
    - config: Configuration files in USER-FILES/01.CONFIG/

Core Modules:
    - txt_reader: TXT file discovery and reading
    - txt_writer: TXT file output with timestamps
    - txt_processing_orchestrator: Main workflow orchestrator
    - api_client: OpenRouter API interaction
    - cost_calculator: Token usage and cost tracking
    - cost_reporter: Cost analysis and reporting
    - reporting: Summary and failure reporting
    - auth: API key management

"""

__version__ = "4.0.0"