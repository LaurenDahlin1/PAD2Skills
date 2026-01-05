"""Extract occupations and skills from PAD document chunks using OpenAI API."""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
from openai import OpenAI


class OccupationsExtractor:
    """Extract occupations and skills from PAD document chunks."""

    # Prompt ID for custom GPT
    OCCUPATIONS_PROMPT_ID = "pmpt_6950c224bab0819486a7f38e0ae0109b08192593c3d4b4af"
    OCCUPATIONS_PROMPT_VERSION = "18"

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
        pad_summary: str = "",
    ) -> str:
        """
        Extract occupations and skills from a single PAD chunk.

        Args:
            project_id: Project ID (e.g., "P075941")
            section_id: Section ID (e.g., "0", "1")
            chunk_text: Text content of the chunk
            abbreviations_text: Abbreviations table text (optional)
            pad_summary: PAD summary text for context (optional)

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

        # Prepare input message with project_summary
        input_message = (
            f"project_id: {project_id}\n"
            f"section_id: {section_id}\n"
            f"project_summary: {pad_summary}\n"
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

    def _load_pad_summary(
        self, project_id: str, summary_dir: Path
    ) -> str:
        """
        Load PAD summary file for a project.

        Args:
            project_id: Project ID
            summary_dir: Directory containing PAD summary files

        Returns:
            PAD summary text (empty string if not found)
        """
        summary_file = summary_dir / f"{project_id}_summary.txt"
        if summary_file.exists():
            return summary_file.read_text(encoding="utf-8").strip()
        return ""


def extract_all_occupations(
    chunks_dir: Path,
    output_dir: Path,
    abbr_dir: Optional[Path] = None,
    summary_dir: Optional[Path] = None,
    specific_project: Optional[str] = None,
    overwrite: bool = False,
) -> Dict[str, List]:
    """
    Extract occupations and skills from multiple PAD chunks.

    Args:
        chunks_dir: Directory containing markdown chunk files
        output_dir: Directory to save occupation JSON files
        abbr_dir: Directory containing abbreviation files (optional)
        summary_dir: Directory containing PAD summary files (optional)
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

    # Load abbreviations and summaries per project (cached)
    abbreviations_cache = {}
    pad_summary_cache = {}

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

            # Load PAD summary (cached per project)
            if project_id not in pad_summary_cache:
                if summary_dir:
                    pad_summary = extractor._load_pad_summary(
                        project_id, summary_dir
                    )
                else:
                    pad_summary = ""
                pad_summary_cache[project_id] = pad_summary
            else:
                pad_summary = pad_summary_cache[project_id]

            # Read chunk content
            chunk_text = chunk_file.read_text(encoding="utf-8")

            # Extract occupations
            result_json = extractor.extract_occupations(
                project_id=project_id,
                section_id=section_id,
                chunk_text=chunk_text,
                abbreviations_text=abbreviations_text,
                pad_summary=pad_summary,
            )

            # Save result
            output_file.write_text(result_json, encoding="utf-8")
            results["generated"].append(chunk_file.name)

        except Exception as e:
            results["failed"].append((chunk_file.name, str(e)))

    return results


def prepare_pad_occupations_csv(
    json_dir: Path,
    output_dir: Path,
    specific_project: Optional[str] = None,
    overwrite: bool = False,
) -> Dict[str, List]:
    """
    Prepare PAD occupations CSV files from JSON extractions.
    
    Reads occupation JSON files, flattens extractions into a DataFrame,
    creates combined_text field, and saves as CSV for inspection/debugging.
    
    Args:
        json_dir: Directory containing occupation JSON files
        output_dir: Directory to save prepared CSV files
        specific_project: Specific project ID to process (None = process all)
        overwrite: Whether to overwrite existing output files
    
    Returns:
        Dictionary with preparation results:
            - generated: List of successfully created CSV filenames
            - skipped: List of skipped CSV filenames (already exists)
            - failed: List of tuples (project_id, error_message)
    """
    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Get list of JSON files to process
    json_files = sorted(json_dir.glob("*_occupations.json"))
    
    if not json_files:
        raise FileNotFoundError(f"No occupation JSON files found in {json_dir}")
    
    # Group JSON files by project_id
    projects = {}
    for json_file in json_files:
        # Parse project_id from filename: {project_id}_{section_id}_occupations.json
        project_id = json_file.stem.split("_", 1)[0]
        if specific_project and project_id != specific_project:
            continue
        if project_id not in projects:
            projects[project_id] = []
        projects[project_id].append(json_file)
    
    if not projects:
        raise FileNotFoundError(
            f"No occupation JSON files found"
            + (f" for project {specific_project}" if specific_project else "")
        )
    
    # Track results
    results = {"generated": [], "skipped": [], "failed": []}
    
    # Process each project
    for project_id, project_files in projects.items():
        output_file = output_dir / f"{project_id}_pad_occupations_prepared.csv"
        
        # Check if output already exists
        if output_file.exists() and not overwrite:
            results["skipped"].append(output_file.name)
            continue
        
        try:
            # Read all JSON files for this project and collect extractions
            all_extractions = []
            
            for json_file in project_files:
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                # Check if extractions exist and are not null
                if data.get("extractions") is not None:
                    for extraction in data["extractions"]:
                        extraction["project_id"] = data["project_id"]
                        extraction["section_id"] = data["section_id"]
                        all_extractions.append(extraction)
            
            if not all_extractions:
                results["failed"].append((project_id, "No extractions found"))
                continue
            
            # Convert to DataFrame
            df = pd.DataFrame(all_extractions)
            
            # Create three-digit ID with leading zeros
            df["pad_id"] = [f"{i:03d}" for i in range(len(df))]
            
            # Create combined text column
            df["combined_text"] = df.apply(_combine_pad_fields, axis=1)
            
            # Save to CSV
            df.to_csv(output_file, index=False)
            results["generated"].append(output_file.name)
            
        except Exception as e:
            results["failed"].append((project_id, str(e)))
    
    return results


def _combine_pad_fields(row: pd.Series) -> str:
    """
    Combine PAD occupation fields into single text column.
    
    Args:
        row: DataFrame row with PAD occupation fields
    
    Returns:
        Combined text string
    """
    parts = []
    
    # Add identified_occupation
    if pd.notna(row["identified_occupation"]):
        parts.append(str(row["identified_occupation"]))
    
    # Add activity_description_in_pad
    if pd.notna(row["activity_description_in_pad"]):
        parts.append(str(row["activity_description_in_pad"]))
    
    # Add skills_needed_for_activity (clean list format)
    skills = row["skills_needed_for_activity"]
    if skills is not None and skills is not pd.NA:
        # If it's a list, join with commas
        if isinstance(skills, list):
            skills_str = ", ".join(str(s) for s in skills)
        else:
            # If it's a string representation of a list, clean it up
            skills_str = str(skills).strip("[]").replace("'", "").replace('"', "")
        parts.append(skills_str)
    
    return " ".join(parts)
