"""
Batch result file I/O handler.
Extracted from batch_result_parser.py to maintain file size limits.
"""

import json
from typing import Dict, Any, Optional
from pathlib import Path
from datetime import datetime
from loguru import logger

from .config import get_model_display_name


class BatchResultSaver:
    """Handles saving batch results to files."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize result saver.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        
    def save_results(self, results: Dict[str, Any], output_dir: Optional[Path] = None) -> Dict[str, Path]:
        """
        Save parsed results to output files.
        
        Args:
            results: Parsed results dictionary
            output_dir: Optional output directory override
            
        Returns:
            Dictionary of saved file paths
        """
        if output_dir is None:
            output_dir = self._create_output_directory()
            
        output_dir.mkdir(parents=True, exist_ok=True)
        
        saved_files = {}
        
        # Save different types of results
        if results["succeeded"]:
            saved_files.update(self._save_successful_results(results["succeeded"], results['success_count'], output_dir))
            
        if results["failed"]:
            saved_files.update(self._save_failed_results(results["failed"], results['failure_count'], output_dir))
            
        # Save summary report
        saved_files.update(self._save_summary_report(results, output_dir))
        
        return saved_files
        
    def _create_output_directory(self) -> Path:
        """Create timestamped output directory with batch mode indicator."""
        timestamp = datetime.now().strftime("%y%m%d_%H%M%S")
        # NO DEFAULTS - model must be in config
        model_name = self.config["model"]
        
        # Use display name from config if available
        display_name = get_model_display_name(model_name, self.config).replace("/", "_")
        
        # Always BATCH for batch results
        mode_str = "BATCH"
        
        # NO DEFAULTS - temperature must be in config
        temp = self.config["temperature"]
        
        output_dir = Path(f"USER-FILES/05.OUTPUT/{timestamp}_{display_name}_{mode_str}_temp{temp}")
        
        return output_dir
        
    def _save_successful_results(self, succeeded: list, count: int, output_dir: Path) -> Dict[str, Path]:
        """Save successful batch results as text files."""
        saved = {}

        # Save main results file (keep as JSON for debugging/analysis)
        success_file = output_dir / "batch_results.json"
        with open(success_file, "w") as f:
            json.dump(succeeded, f, indent=2)
        saved["results"] = success_file
        logger.info(f"Saved {count} successful results to {success_file}")

        # Save individual text files with original filenames
        for result in succeeded:
            # Get the filename from the result
            filename = result.get("filename", "unknown")

            # Remove the "text_" prefix if present
            if filename.startswith("text_"):
                filename = filename[5:]

            # Ensure it has .txt extension
            if not filename.endswith(".txt"):
                filename += ".txt"

            # Get the response text
            response = result.get("response", "")

            # Save as text file
            text_file = output_dir / filename
            with open(text_file, "w", encoding="utf-8") as f:
                f.write(response)

            logger.info(f"Saved response to {text_file}")

        return saved
        
    def _save_failed_results(self, failed: list, count: int, output_dir: Path) -> Dict[str, Path]:
        """Save failed batch results."""
        failure_file = output_dir / "batch_failures.json"
        with open(failure_file, "w") as f:
            json.dump(failed, f, indent=2)
            
        logger.warning(f"⚠️ Saved {count} failed results to {failure_file}")
        
        return {"failures": failure_file}
        
    def _save_summary_report(self, results: Dict[str, Any], output_dir: Path) -> Dict[str, Path]:
        """Save batch summary report."""
        from .batch_report_generator import BatchReportGenerator
        
        generator = BatchReportGenerator(self.config)
        summary = generator.create_summary_report(results)
        
        summary_file = output_dir / "BATCH_SUMMARY.md"
        with open(summary_file, "w") as f:
            f.write(summary)
            
        logger.info(f"Saved batch summary to {summary_file}")
        
        return {"summary": summary_file}