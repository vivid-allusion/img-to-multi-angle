#!/usr/bin/env python3
"""Configuration error reporting functionality."""

from typing import List
from .config_examples import FIELD_EXAMPLES


class ConfigReporter:
    """Generates detailed configuration error reports."""

    def __init__(self):
        """Initialize the reporter with example configurations."""
        # Convert FIELD_EXAMPLES to string format for YAML
        self.example_values = {}
        for key, value in FIELD_EXAMPLES.items():
            if isinstance(value, str):
                self.example_values[key] = f'"{value}"'
            elif isinstance(value, bool):
                self.example_values[key] = str(value).lower()
            else:
                self.example_values[key] = str(value)

    def generate_missing_config_report(self, missing_fields: List[str]) -> str:
        """Generate detailed report showing exactly what's missing and where to add it.

        Args:
            missing_fields: List of missing field paths

        Returns:
            Detailed error report with examples
        """
        report = [
            "=" * 70,
            "🚨 MISSING CONFIGURATION DETECTED",
            "=" * 70,
            "",
            "The following required configuration fields are missing:",
            ""
        ]

        # Group missing fields by their parent
        grouped = self._group_missing_fields(missing_fields)

        # Generate specific instructions for each group
        for parent, children in grouped.items():
            if parent == 'root':
                report.append("\nAdd to USER-FILES/01.CONFIG/openrouter_config.yaml:")
            else:
                report.append(f"\nUnder '{parent}' section, add:")

            for child in children:
                # Provide example values based on field name
                example = self._get_example_value(child)
                report.append(f"  {child}: {example}")

        report.extend([
            "",
            "=" * 70,
            "WHERE TO ADD CONFIGURATION:",
            "=" * 70,
            "",
            "Option 1: USER-FILES/01.CONFIG/openrouter_config.yaml",
            "Option 2: USER-FILES/03.PROFILES/<your_profile>.yaml",
            "",
            "IMPORTANT: Each setting must be in ONLY ONE location.",
            "NO DEFAULTS will be used - every setting must be explicit.",
            "",
            "=" * 70
        ])

        return "\n".join(report)

    def generate_error_report(self, errors: List[str]) -> str:
        """
        Generate a detailed error report for configuration issues.

        Args:
            errors: List of error messages

        Returns:
            Formatted error report
        """
        # Check if errors are about missing fields
        missing_fields = []
        other_errors = []

        for error in errors:
            if 'Missing required fields:' in error:
                # Extract field names
                fields_str = error.split(':', 1)[1].strip()
                fields = [f.strip() for f in fields_str.split(',')]
                missing_fields.extend(fields)
            else:
                other_errors.append(error)

        # If we have missing fields, generate specialized report
        if missing_fields:
            return self.generate_missing_config_report(missing_fields)

        # Otherwise, generate standard report
        return self._generate_standard_error_report(other_errors)

    def _group_missing_fields(self, missing_fields: List[str]) -> dict:
        """Group missing fields by their parent configuration section."""
        grouped = {}
        for field in missing_fields:
            if '.' in field:
                parent, child = field.rsplit('.', 1)
                if parent not in grouped:
                    grouped[parent] = []
                grouped[parent].append(child)
            else:
                if 'root' not in grouped:
                    grouped['root'] = []
                grouped['root'].append(field)
        return grouped

    def _get_example_value(self, field_name: str) -> str:
        """Get example value for a field based on its name."""
        return self.example_values.get(field_name, '<value>')

    def _generate_standard_error_report(self, errors: List[str]) -> str:
        """Generate standard error report for non-missing-field errors."""
        report = [
            "=" * 70,
            "CONFIGURATION VALIDATION FAILED",
            "=" * 70,
            "",
            "The following configuration errors must be fixed:",
            ""
        ]

        for i, error in enumerate(errors, 1):
            report.append(f"{i}. {error}")

        report.extend([
            "",
            "=" * 70,
            "RESOLUTION:",
            "=" * 70,
            "",
            "All configuration must be explicitly defined in:",
            "  - USER-FILES/01.CONFIG/openrouter_config.yaml",
            "  - USER-FILES/03.PROFILES/*.yaml",
            "",
            "NO DEFAULTS are allowed. Every setting must be explicit.",
            "",
            self._get_example_configuration(),
            "",
            "=" * 70
        ])

        return "\n".join(report)

    def _get_example_configuration(self) -> str:
        """Return example configuration for reference."""
        return """Example required fields in openrouter_config.yaml:
  model: claude-3-5-sonnet-latest
  max_tokens: 800
  temperature: 0.3
  stream: false
  processing_options:
    trim_prompts: true
    normalize_spaces: true
    max_prompt_length: 5900
    include_filename: true
  retry_config:
    max_retries: 2
    timeout: 600.0
  avg_output_tokens: 800"""