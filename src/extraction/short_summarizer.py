"""Generate short summaries from long PAD summaries using OpenAI API."""

import json
from pathlib import Path
from typing import Dict, List, Optional

from openai import OpenAI


class ShortSummarizer:
    """Generate short summaries and geographic scope from long summaries."""

    # Prompt ID for short summary custom GPT
    SHORT_SUMMARY_PROMPT_ID = "pmpt_695d94ebaef0819796b1eb3d107d00aa053dbcd063f14b6c"
    SHORT_SUMMARY_PROMPT_VERSION = "2"

    def __init__(self):
        """Initialize the short summarizer with OpenAI client."""
        self.client = OpenAI()

    def generate_short_summary(
        self,
        long_summary: str,
    ) -> Dict[str, str]:
        """
        Generate a short summary and geographic scope from a long summary.

        Args:
            long_summary: Long summary text

        Returns:
            Dictionary with "summary" and "geographic_scope" keys

        Raises:
            ValueError: If API response is invalid
        """
        # Call custom GPT with the long summary
        response = self.client.responses.create(
            prompt={
                "id": self.SHORT_SUMMARY_PROMPT_ID,
                "version": self.SHORT_SUMMARY_PROMPT_VERSION,
            },
            input=long_summary,
        )

        # Extract and parse JSON response
        result_text = response.output_text
        result_json = json.loads(result_text)

        # Validate response structure
        if "summary" not in result_json or "geographic_scope" not in result_json:
            raise ValueError(
                f"Invalid response structure: missing required keys. Got: {result_json.keys()}"
            )

        return result_json


def generate_all_short_summaries(
    summaries_dir: Path,
    output_dir: Path,
    specific_project: Optional[str] = None,
    overwrite: bool = False,
) -> Dict[str, List]:
    """
    Generate short summaries for multiple PAD documents.

    Args:
        summaries_dir: Directory containing long summary text files
        output_dir: Directory to save short summary JSON files
        specific_project: Specific project ID to process (None = process all)
        overwrite: Whether to overwrite existing output files

    Returns:
        Dictionary with summarization results:
            - generated: List of successfully processed project IDs
            - skipped: List of skipped project IDs (already exists)
            - failed: List of tuples (project_id, error_message)
    """
    # Initialize summarizer
    summarizer = ShortSummarizer()

    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)

    # Get list of summary files to process
    if specific_project:
        summary_file = summaries_dir / f"{specific_project}_summary.txt"
        if not summary_file.exists():
            return {
                "generated": [],
                "skipped": [],
                "failed": [(specific_project, "Summary file not found")],
            }
        summary_files = [summary_file]
    else:
        summary_files = list(summaries_dir.glob("*_summary.txt"))

    # Track results
    results = {"generated": [], "skipped": [], "failed": []}

    # Process each summary file
    for summary_file in summary_files:
        # Extract project ID from filename (e.g., "P075941_summary.txt" -> "P075941")
        project_id = summary_file.stem.replace("_summary", "")

        output_file = output_dir / f"{project_id}.json"

        # Check if output already exists
        if output_file.exists() and not overwrite:
            results["skipped"].append(project_id)
            continue

        try:
            # Read long summary
            long_summary = summary_file.read_text(encoding="utf-8")

            # Generate short summary
            short_summary_data = summarizer.generate_short_summary(long_summary)

            # Save as JSON
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(short_summary_data, f, indent=2)

            results["generated"].append(project_id)

        except Exception as e:
            results["failed"].append((project_id, str(e)))

    return results
