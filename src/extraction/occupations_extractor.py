"""Extract occupations and skills from PAD document chunks using OpenAI API."""

import os
from pathlib import Path
from typing import Dict, List, Optional

from openai import OpenAI


class OccupationsExtractor:
    """Extract occupations and skills from PAD document chunks."""

    # Prompt ID for custom GPT
    OCCUPATIONS_PROMPT_ID = "pmpt_6950c224bab0819486a7f38e0ae0109b08192593c3d4b4af"
    OCCUPATIONS_PROMPT_VERSION = "15"

    def __init__(self):
        """Initialize the occupations extractor with OpenAI client."""
        # Suppress verbose HTTP logging from OpenAI client
        os.environ["OPENAI_LOG"] = "error"
        self.client = OpenAI()

    def extract_occupations(
        self,
        project_id: str,
        section_id: str,
        chunk_text: str,
        abbreviations_text: str = "",
    ) -> str:
        """
        Extract occupations and skills from a single PAD chunk.

        Args:
            project_id: Project ID (e.g., "P075941")
            section_id: Section ID (e.g., "0", "1")
            chunk_text: Text content of the chunk
            abbreviations_text: Abbreviations table text (optional)

        Returns:
            JSON string containing extracted occupations and skills

        Raises:
            ValueError: If API response is invalid
        """
        # Prepend abbreviations if available
        if abbreviations_text:
            chunk_text_with_context = abbreviations_text + "\n\n" + chunk_text
        else:
            chunk_text_with_context = chunk_text

        # Prepare input message
        input_message = (
            f"project_id: {project_id}\n"
            f"section_id: {section_id}\n"
            f"chunk_text: {chunk_text_with_context}"
        )

        # Call custom GPT
        response = self.client.responses.create(
            prompt={
                "id": self.OCCUPATIONS_PROMPT_ID,
                "version": self.OCCUPATIONS_PROMPT_VERSION,
            },
            input=[{"role": "user", "content": input_message}],
            reasoning={"summary": None},
            store=False,
            include=[
                "reasoning.encrypted_content",
                "web_search_call.action.sources",
            ],
        )

        # Extract response text
        return response.output_text

    def _load_abbreviations(
        self, project_id: str, abbr_dir: Path
    ) -> str:
        """
        Load abbreviations file for a project.

        Args:
            project_id: Project ID
            abbr_dir: Directory containing abbreviation files

        Returns:
            Abbreviations text (empty string if not found)
        """
        abbr_file = abbr_dir / f"{project_id}_abbr.md"
        if abbr_file.exists():
            return abbr_file.read_text(encoding="utf-8")
        return ""


def extract_all_occupations(
    chunks_dir: Path,
    output_dir: Path,
    abbr_dir: Optional[Path] = None,
    specific_project: Optional[str] = None,
    overwrite: bool = False,
) -> Dict[str, List]:
    """
    Extract occupations and skills from multiple PAD chunks.

    Args:
        chunks_dir: Directory containing markdown chunk files
        output_dir: Directory to save occupation JSON files
        abbr_dir: Directory containing abbreviation files (optional)
        specific_project: Specific project ID to process (None = process all)
        overwrite: Whether to overwrite existing output files

    Returns:
        Dictionary with extraction results:
            - generated: List of successfully processed chunk filenames
            - skipped: List of skipped chunk filenames (already exists)
            - failed: List of tuples (chunk_filename, error_message)
    """
    # Initialize extractor
    extractor = OccupationsExtractor()

    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)

    # Get list of chunks to process
    chunk_files = sorted(chunks_dir.glob("*.md"))

    # Filter by specific project if specified
    if specific_project:
        chunk_files = [f for f in chunk_files if f.stem.startswith(specific_project)]

    if not chunk_files:
        raise FileNotFoundError(
            f"No chunk files found in {chunks_dir}"
            + (f" for project {specific_project}" if specific_project else "")
        )

    # Load abbreviations per project (cached)
    abbreviations_cache = {}

    # Track results
    results = {"generated": [], "skipped": [], "failed": []}

    # Track progress
    total_chunks = len(chunk_files)
    
    # Process each chunk
    for idx, chunk_file in enumerate(chunk_files, start=1):
        # Parse filename: {project_id}_{section_id}_{snake_title}.md
        filename_parts = chunk_file.stem.split("_", 2)
        if len(filename_parts) < 2:
            results["failed"].append(
                (chunk_file.name, "Invalid chunk filename format")
            )
            continue

        project_id = filename_parts[0]
        section_id = filename_parts[1]

        # Output file path
        output_file = output_dir / f"{project_id}_{section_id}_occupations.json"

        # Check if output already exists
        if output_file.exists() and not overwrite:
            results["skipped"].append(chunk_file.name)
            continue

        # Print progress
        print(f"Sent request, chunk {idx}/{total_chunks}", flush=True)

        try:
            # Load abbreviations (cached per project)
            if project_id not in abbreviations_cache:
                if abbr_dir:
                    abbreviations_text = extractor._load_abbreviations(
                        project_id, abbr_dir
                    )
                else:
                    abbreviations_text = ""
                abbreviations_cache[project_id] = abbreviations_text
            else:
                abbreviations_text = abbreviations_cache[project_id]

            # Read chunk content
            chunk_text = chunk_file.read_text(encoding="utf-8")

            # Extract occupations
            result_json = extractor.extract_occupations(
                project_id=project_id,
                section_id=section_id,
                chunk_text=chunk_text,
                abbreviations_text=abbreviations_text,
            )

            # Save result
            output_file.write_text(result_json, encoding="utf-8")
            results["generated"].append(chunk_file.name)

        except Exception as e:
            results["failed"].append((chunk_file.name, str(e)))

    return results
