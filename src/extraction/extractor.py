"""Extract document sections and abbreviations from PAD markdown files using OpenAI API."""

import json
import re
from pathlib import Path
from typing import Optional

from openai import OpenAI


class DocumentExtractor:
    """Extract structured information from PAD documents using OpenAI API."""

    # Prompt IDs for custom GPTs
    SECTIONS_PROMPT_ID = "pmpt_6950b4992fcc8194b89fc2d87be08bf8088afcd3c3f3a4d7"
    SECTIONS_PROMPT_VERSION = "6"
    ABBREVIATIONS_PROMPT_ID = "pmpt_69574fe1ff748195b16eca5fcc20d75202a70098695be261"
    ABBREVIATIONS_PROMPT_VERSION = "2"

    def __init__(self):
        """Initialize the document extractor with OpenAI client."""
        self.client = OpenAI()

    def extract_sections(self, markdown_path: Path, project_id: str) -> dict:
        """
        Extract document sections from a PAD markdown file.

        Args:
            markdown_path: Path to markdown file
            project_id: Project ID (e.g., "P075941")

        Returns:
            Dictionary with sections data

        Raises:
            FileNotFoundError: If markdown doesn't exist
            Exception: If extraction fails
        """
        if not markdown_path.exists():
            raise FileNotFoundError(f"Markdown file not found: {markdown_path}")

        # Read markdown content
        markdown_content = markdown_path.read_text(encoding="utf-8")

        # Prepare input with project ID
        input_message = f"Project ID: {project_id}\n\n{markdown_content}"

        # Call custom GPT
        response = self.client.responses.create(
            prompt={
                "id": self.SECTIONS_PROMPT_ID,
                "version": self.SECTIONS_PROMPT_VERSION,
            },
            input=[{"role": "user", "content": input_message}],
            reasoning={"summary": None},
            store=True,
            include=[
                "reasoning.encrypted_content",
                "web_search_call.action.sources",
            ],
        )

        # Extract text from response
        result = None
        for item in response.output:
            if hasattr(item, "content") and hasattr(item, "role"):
                result = item.content[0].text
                break

        if result is None:
            raise ValueError("No valid response received from API")

        # Parse JSON result
        return json.loads(result)

    def extract_abbreviations(self, markdown_path: Path, project_id: str) -> str:
        """
        Extract abbreviations table from a PAD markdown file.

        Args:
            markdown_path: Path to markdown file
            project_id: Project ID (e.g., "P075941")

        Returns:
            Markdown table with abbreviations

        Raises:
            FileNotFoundError: If markdown doesn't exist
            Exception: If extraction fails
        """
        if not markdown_path.exists():
            raise FileNotFoundError(f"Markdown file not found: {markdown_path}")

        # Read markdown content
        markdown_content = markdown_path.read_text(encoding="utf-8")

        # Extract text up to first table (where abbreviations usually end)
        match = re.search(r"\btable\b", markdown_content, re.IGNORECASE)
        if match:
            abbreviations_text = markdown_content[: match.start()].strip()
        else:
            # If no table found, use full content
            abbreviations_text = markdown_content

        # Call custom GPT
        response = self.client.responses.create(
            prompt={
                "id": self.ABBREVIATIONS_PROMPT_ID,
                "version": self.ABBREVIATIONS_PROMPT_VERSION,
            },
            input=[{"role": "user", "content": abbreviations_text}],
            reasoning={"summary": None},
            store=True,
            include=[
                "reasoning.encrypted_content",
                "web_search_call.action.sources",
            ],
        )

        # Extract markdown table from response
        result = None
        for item in response.output:
            if hasattr(item, "content") and hasattr(item, "role"):
                result = item.content[0].text
                break

        if result is None:
            raise ValueError("No valid response received from API")

        return result


def extract_all_sections(
    markdown_dir: Path,
    output_dir: Path,
    specific_file: Optional[str] = None,
    overwrite: bool = False,
) -> dict[str, list]:
    """
    Extract document sections from markdown file(s).

    Args:
        markdown_dir: Directory containing markdown files
        output_dir: Directory to save JSON section files
        specific_file: Specific markdown filename to process (None = process all)
        overwrite: Whether to overwrite existing output files

    Returns:
        Dictionary with extraction results:
            - extracted: List of successfully processed filenames
            - skipped: List of skipped filenames (already exists)
            - failed: List of tuples (filename, error_message)
    """
    # Initialize extractor
    extractor = DocumentExtractor()

    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)

    # Get list of markdown files to process
    if specific_file:
        target_file = markdown_dir / specific_file
        files_to_process = [target_file] if target_file.exists() else []
    else:
        files_to_process = list(markdown_dir.glob("*.md"))

    # Track results
    results = {"extracted": [], "skipped": [], "failed": []}

    # Process each markdown file
    for md_file in files_to_process:
        # Extract project ID from filename (e.g., "P075941.md" -> "P075941")
        project_id = md_file.stem

        output_file = output_dir / f"{project_id}_sections.json"

        # Check if output already exists
        if output_file.exists() and not overwrite:
            results["skipped"].append(md_file.name)
            continue

        try:
            # Extract sections
            sections_data = extractor.extract_sections(md_file, project_id)

            # Save sections JSON
            output_file.write_text(
                json.dumps(sections_data, indent=2), encoding="utf-8"
            )
            results["extracted"].append(md_file.name)

        except Exception as e:
            results["failed"].append((md_file.name, str(e)))

    return results


def extract_all_abbreviations(
    markdown_dir: Path,
    output_dir: Path,
    specific_file: Optional[str] = None,
    overwrite: bool = False,
) -> dict[str, list]:
    """
    Extract abbreviations from markdown file(s).

    Args:
        markdown_dir: Directory containing markdown files
        output_dir: Directory to save abbreviation markdown files
        specific_file: Specific markdown filename to process (None = process all)
        overwrite: Whether to overwrite existing output files

    Returns:
        Dictionary with extraction results:
            - extracted: List of successfully processed filenames
            - skipped: List of skipped filenames (already exists)
            - failed: List of tuples (filename, error_message)
    """
    # Initialize extractor
    extractor = DocumentExtractor()

    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)

    # Get list of markdown files to process
    if specific_file:
        target_file = markdown_dir / specific_file
        files_to_process = [target_file] if target_file.exists() else []
    else:
        files_to_process = list(markdown_dir.glob("*.md"))

    # Track results
    results = {"extracted": [], "skipped": [], "failed": []}

    # Process each markdown file
    for md_file in files_to_process:
        # Extract project ID from filename (e.g., "P075941.md" -> "P075941")
        project_id = md_file.stem

        output_file = output_dir / f"{project_id}_abbr.md"

        # Check if output already exists
        if output_file.exists() and not overwrite:
            results["skipped"].append(md_file.name)
            continue

        try:
            # Extract abbreviations
            abbr_table = extractor.extract_abbreviations(md_file, project_id)

            # Save abbreviations markdown
            output_file.write_text(abbr_table, encoding="utf-8")
            results["extracted"].append(md_file.name)

        except Exception as e:
            results["failed"].append((md_file.name, str(e)))

    return results
